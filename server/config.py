"""Configuración del C2 server.

Carga configuración desde profiles YAML con overrides por variables de entorno.
Los profiles definen la configuración base, las env vars permiten personalización.
"""
import os
import yaml
from pathlib import Path


def load_profile(path=None):
    """Carga un profile YAML desde disco."""
    if path is None:
        path = os.environ.get("C2_PROFILE", "profiles/default.yaml")
    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        # Fallback a config por defecto si no existe el profile
        return {
            "listener": {"host": "0.0.0.0", "port": 8080, "protocol": "http"},
            "agent": {"sleep": 30, "jitter": 50, "timeout": 15, "retry_delay": 5},
            "operators": [{"name": "admin", "token": "supersecret-ctf-token"}],
        }


# Cargar profile
_profile = load_profile()
_listener = _profile.get("listener", {})
_agent = _profile.get("agent", {})
_operators = _profile.get("operators", [{}])

# NONCE del equipo (debe ser visible en el video walkthrough del reto).
NONCE = os.environ.get("C2_NONCE", "sentrysec-2026")

# Token compartido entre operador/implant y servidor.
AUTH_TOKEN = os.environ.get("C2_AUTH_TOKEN", _operators[0].get("token", "supersecret-ctf-token"))

# Bind del servidor (desde profile, override por env vars).
HOST = os.environ.get("C2_HOST", _listener.get("host", "0.0.0.0"))
PORT = int(os.environ.get("C2_PORT", _listener.get("port", 8080)))

# Protocolo del listener (http o https).
PROTOCOL = _listener.get("protocol", "http")

# URIs del listener (para referencia).
URIS = _listener.get("uris", [])

# Headers del listener (para referencia).
LISTENER_HEADERS = _listener.get("headers", {})

# Intervalo de heartbeat esperado (segundos). Se envía al implant en el registro.
HEARTBEAT_INTERVAL = int(os.environ.get("C2_HEARTBEAT_INTERVAL", _agent.get("sleep", 30)))

# Jitter del agent (porcentaje ±).
JITTER = _agent.get("jitter", 50)

# Un agente se marca "offline" si no envía heartbeat en este múltiplo del intervalo.
STALE_MULTIPLIER = 2

# Whitelist de comandos permitidos. Solo el binario base (primer token) se valida.
ALLOWED_COMMANDS = {
    "whoami",
    "hostname",
    "id",
    "uname",
    "pwd",
    "ls",
    "cat",
    "ps",
    "env",
    "date",
    "uptime",
    "df",
}

# Archivo de log del servidor.
LOG_FILE = os.environ.get("C2_LOG_FILE", "c2.log")


def get_profile():
    """Devuelve el profile cargado (para uso en otros módulos)."""
    return _profile
