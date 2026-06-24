"""Clase Listener para configuración del servidor C2.

Un Listener define cómo el servidor C2 escucha conexiones de los agents.
Incluye URIs, headers falsos y configuración de respuesta para evasión.
"""
import yaml
from pathlib import Path


class Listener:
    """Representa un listener del C2 server."""

    def __init__(self, config):
        """Inicializa el listener desde un diccionario de configuración."""
        self.host = config.get("host", "0.0.0.0")
        self.port = config.get("port", 8080)
        self.protocol = config.get("protocol", "http")
        self.uris = config.get("uris", [])
        self.headers = config.get("headers", {})
        self.response = config.get("response", {})

    def get_callback_uris(self):
        """Devuelve las URIs configuradas para callbacks del agent."""
        return self.uris

    def get_fake_headers(self):
        """Devuelve los headers falsos para evasión de IDS/IPS."""
        return self.headers

    def get_response_headers(self):
        """Devuelve los headers de respuesta del servidor."""
        return self.response.get("headers", {})

    def get_server_header(self):
        """Devuelve el header Server falso."""
        return self.response.get("server", "")

    def get_bind_address(self):
        """Devuelve la dirección de bind (host:port)."""
        return f"{self.host}:{self.port}"

    def get_base_url(self):
        """Devuelve la URL base del listener."""
        return f"{self.protocol}://{self.host}:{self.port}"

    def __repr__(self):
        return f"Listener(host={self.host!r}, port={self.port}, protocol={self.protocol!r})"


def load_listener(profile_path="profiles/default.yaml"):
    """Carga un listener desde un archivo profile YAML."""
    try:
        with open(profile_path) as f:
            config = yaml.safe_load(f)
        return Listener(config.get("listener", {}))
    except FileNotFoundError:
        # Fallback a configuración por defecto
        return Listener({})


def create_listener_from_config(config):
    """Crea un Listener desde un diccionario de configuración directo."""
    return Listener(config)
