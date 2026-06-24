"""Modelo de datos en memoria y helpers de seguridad del C2 server.

El estado vive en RAM (sin base de datos): al reiniciar el servidor se limpia.
Es suficiente para una demo de CTF y evita dependencias externas.
"""
import shlex
import threading
import time
import uuid
from functools import wraps
from threading import Lock

from flask import jsonify, request

import config

# Caracteres que indican encadenamiento de comandos / inyección de shell.
_FORBIDDEN_TOKENS = (";", "|", "&", "`", "$(", ">", "<", "\n")


def is_command_allowed(command):
    """Valida un comando contra la whitelist.

    Devuelve (True, "") si está permitido, o (False, motivo) si no.
    Rechaza encadenamiento de comandos y binarios fuera de la whitelist.
    """
    if not command or not command.strip():
        return False, "comando vacío"

    for token in _FORBIDDEN_TOKENS:
        if token in command:
            return False, f"token prohibido: {token!r}"

    try:
        parts = shlex.split(command)
    except ValueError as exc:
        return False, f"comando mal formado: {exc}"

    if not parts:
        return False, "comando vacío"

    binary = parts[0]
    if binary not in config.ALLOWED_COMMANDS:
        return False, f"comando no permitido: {binary!r}"

    return True, ""


class AgentStore:
    """Almacén en memoria de agentes, tareas y resultados (thread-safe)."""

    def __init__(self):
        self._lock = Lock()
        self.agents = {}         # agent_id -> info
        self.tasks = {}          # agent_id -> [task, ...]
        self.results = []        # lista de resultados
        self._result_events = {} # task_id -> threading.Event

    def register(self, info, agent_id=None):
        with self._lock:
            agent_id = agent_id or str(uuid.uuid4())
            now = time.time()
            existing = self.agents.get(agent_id, {})
            self.agents[agent_id] = {
                "agent_id": agent_id,
                "hostname": info.get("hostname", "unknown"),
                "os": info.get("os", "unknown"),
                "username": info.get("username", "unknown"),
                "ip": info.get("ip", "unknown"),
                "first_seen": existing.get("first_seen", now),
                "last_seen": now,
                "status": "online",
            }
            self.tasks.setdefault(agent_id, [])
            return agent_id

    def heartbeat(self, agent_id):
        with self._lock:
            agent = self.agents.get(agent_id)
            if not agent:
                return False
            agent["last_seen"] = time.time()
            agent["status"] = "online"
            return True

    def add_task(self, agent_id, command):
        with self._lock:
            if agent_id not in self.agents:
                return None
            task_id = str(uuid.uuid4())
            self._result_events[task_id] = threading.Event()
            task = {
                "task_id": task_id,
                "command": command,
                "status": "pending",
            }
            self.tasks.setdefault(agent_id, []).append(task)
            return task

    def next_task(self, agent_id):
        with self._lock:
            for task in self.tasks.get(agent_id, []):
                if task["status"] == "pending":
                    task["status"] = "dispatched"
                    return task
            return None

    def save_result(self, agent_id, task_id, output):
        with self._lock:
            self.results.append({
                "agent_id": agent_id,
                "task_id": task_id,
                "output": output,
                "timestamp": time.time(),
            })
            for task in self.tasks.get(agent_id, []):
                if task["task_id"] == task_id:
                    task["status"] = "done"
                    break
            event = self._result_events.pop(task_id, None)
        # Señalar fuera del lock para evitar deadlock
        if event:
            event.set()

    def wait_for_result(self, agent_id, task_id, timeout=25):
        """Bloquea hasta que llegue el resultado para task_id (long poll).

        Retorna el dict del resultado o None si expira el timeout.
        """
        event = self._result_events.get(task_id)
        if event:
            event.wait(timeout=timeout)
        with self._lock:
            for r in self.results:
                if r["task_id"] == task_id and r["agent_id"] == agent_id:
                    return r
        return None

    def _refresh_status(self):
        threshold = config.HEARTBEAT_INTERVAL * config.STALE_MULTIPLIER
        now = time.time()
        for agent in self.agents.values():
            if now - agent["last_seen"] > threshold:
                agent["status"] = "offline"

    def list_agents(self):
        with self._lock:
            self._refresh_status()
            return list(self.agents.values())

    def results_for(self, agent_id):
        with self._lock:
            return [r for r in self.results if r["agent_id"] == agent_id]


# Instancia global compartida.
store = AgentStore()


def require_token(func):
    """Decorador que exige el header X-Auth-Token válido."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-Auth-Token", "")
        if token != config.AUTH_TOKEN:
            return jsonify({"error": "unauthorized"}), 401
        return func(*args, **kwargs)
    return wrapper
