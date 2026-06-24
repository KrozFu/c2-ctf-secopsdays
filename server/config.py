"""Configuración del C2 server.

Carga configuración desde profiles YAML con overrides por variables de entorno.
Los profiles definen la configuración base, las env vars permiten personalización.

Este es el ÚNICO módulo que carga el YAML. El resto del código importa
valores desde aquí o recibe dicts ya parseados.
"""
import os
from pathlib import Path

import yaml

from listener import Listener


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


# ---------------------------------------------------------------------------
# Cargar profile (único punto de carga)
# ---------------------------------------------------------------------------
_profile = load_profile()
_listener_cfg = _profile.get("listener", {})
_agent_cfg = _profile.get("agent", {})
_operators = _profile.get("operators", [{}])

# ---------------------------------------------------------------------------
# NONCE del equipo (debe ser visible en el video walkthrough del reto).
# ---------------------------------------------------------------------------
NONCE = os.environ.get("C2_NONCE", "sentrysec-2026")

# ---------------------------------------------------------------------------
# Token compartido entre operador/implant y servidor.
# ---------------------------------------------------------------------------
AUTH_TOKEN = os.environ.get(
    "C2_AUTH_TOKEN",
    _operators[0].get("token", "supersecret-ctf-token"),
)

# ---------------------------------------------------------------------------
# Bind del servidor (desde profile, override por env vars).
# ---------------------------------------------------------------------------
HOST = os.environ.get("C2_HOST", _listener_cfg.get("host", "0.0.0.0"))
PORT = int(os.environ.get("C2_PORT", _listener_cfg.get("port", 8080)))

# ---------------------------------------------------------------------------
# Listener (instancia única reutilizable).
# ---------------------------------------------------------------------------
LISTENER = Listener(_listener_cfg)

# URIs del listener (para referencia y logging).
CALLBACK_URIS = _listener_cfg.get("uris", [])

# Headers del listener (para referencia).
LISTENER_HEADERS = _listener_cfg.get("headers", {})

# ---------------------------------------------------------------------------
# Configuración del agent (implant).
# ---------------------------------------------------------------------------
HEARTBEAT_INTERVAL = int(
    os.environ.get("C2_HEARTBEAT_INTERVAL", _agent_cfg.get("sleep", 30))
)
JITTER = _agent_cfg.get("jitter", 50)

# Un agente se marca "offline" si no envía heartbeat en este múltiplo del intervalo.
STALE_MULTIPLIER = 2

# ---------------------------------------------------------------------------
# Whitelist de comandos permitidos. Solo el binario base (primer token) se valida.
# ---------------------------------------------------------------------------
ALLOWED_COMMANDS = {
    # Comunes (Linux + Windows)
    "whoami",
    "hostname",
    "cat",
    "ps",
    "ping",
    "echo",
    # Linux
    "id",
    "uname",
    "pwd",
    "ls",
    "env",
    "date",
    "uptime",
    "df",
    # Windows
    "ipconfig",
    "dir",
    "tasklist",
    "net",
    "systeminfo",
    "type",
}

# ---------------------------------------------------------------------------
# Archivo de log (resuelve CWD para que funcione desde cualquier directorio).
# ---------------------------------------------------------------------------
LOG_FILE = os.environ.get(
    "C2_LOG_FILE",
    str(Path(__file__).resolve().parent.parent / "c2.log"),
)


def get_profile():
    """Devuelve el profile cargado (para uso en otros módulos)."""
    return _profile
