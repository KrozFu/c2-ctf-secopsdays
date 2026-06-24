"""Arranque del C2 server.

Crea la app Flask, configura el logging, imprime un banner con el NONCE del
equipo (visible para el video walkthrough) y levanta el servidor.
"""
import logging

from flask import Flask

import config
from routes import api
from routes_socks import socks_api


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(config.LOG_FILE),
        ],
    )


def print_banner():
    banner = r"""
   ____ ____   
  / ___|___ \  
 | |     __) | 
 | |___ / __/  
  \____|_____|
"""
    print(banner)
    print("  C2 CTF SecOpsDays — Command & Control")
    print("  " + "-" * 48)
    print(f"  TEAM NONCE  : {config.NONCE}")
    print(f"  Listening   : http://{config.HOST}:{config.PORT}")
    print(f"  Auth token  : {config.AUTH_TOKEN}")
    print(f"  Heartbeat   : {config.HEARTBEAT_INTERVAL}s")
    print(f"  Dashboard   : http://{config.HOST}:{config.PORT}/dashboard")
    if config.CALLBACK_URIS:
        print(f"  Callback URIs: {', '.join(config.CALLBACK_URIS)}")
    print(f"  Protocol    : {config.LISTENER.protocol}")
    print(f"  Fake Server : {config.LISTENER.get_server_header() or '(none)'}")
    print("  " + "-" * 48)
    print("  Solo para uso en CTF / entornos autorizados.\n")


def create_app():
    app = Flask(__name__,
                static_folder="static",
                template_folder="templates")
    # No CORS needed: dashboard y API se sirven desde el mismo origin.
    app.register_blueprint(api)
    app.register_blueprint(socks_api)
    return app


def main():
    setup_logging()
    print_banner()
    app = create_app()
    # use_reloader=False para no duplicar el banner ni el estado en memoria.
    app.run(host=config.HOST, port=config.PORT, use_reloader=False)


if __name__ == "__main__":
    main()
