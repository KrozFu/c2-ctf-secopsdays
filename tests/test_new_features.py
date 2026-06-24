import socket
import struct
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "implant"))


class TestSOCKSClient:
    def test_import_socks_module(self):
        from modules.socks import SOCKSClient

        assert SOCKSClient is not None

    def test_create_socks_client(self):
        from modules.socks import SOCKSClient

        client = SOCKSClient(
            "http://127.0.0.1:8080", "test-token", "test-agent"
        )
        assert client.c2_url == "http://127.0.0.1:8080"
        assert client.auth_token == "test-token"
        assert client.agent_id == "test-agent"

    def test_parse_connect_ipv4(self):
        from modules.socks import SOCKSClient, SOCKS5_VERSION, SOCKS5_CMD_CONNECT, SOCKS5_ATYP_IPV4

        client = SOCKSClient("http://x", "t", "a")
        # Build a valid SOCKS5 CONNECT request for 10.0.0.1:22
        data = struct.pack("!BBBB", SOCKS5_VERSION, SOCKS5_CMD_CONNECT, 0x00, SOCKS5_ATYP_IPV4)
        data += socket_inet_aton("10.0.0.1") + struct.pack("!H", 22)
        result = client.parse_connect_request(data)
        assert result is not None
        assert result["host"] == "10.0.0.1"
        assert result["port"] == 22

    def test_parse_connect_invalid_version(self):
        from modules.socks import SOCKSClient

        client = SOCKSClient("http://x", "t", "a")
        result = client.parse_connect_request(bytes([0x04, 0x01, 0x00, 0x01]))
        assert result is None

    def test_parse_connect_too_short(self):
        from modules.socks import SOCKSClient

        client = SOCKSClient("http://x", "t", "a")
        result = client.parse_connect_request(bytes([0x05]))
        assert result is None

    def test_success_reply(self):
        from modules.socks import SOCKSClient

        reply = SOCKSClient.success_reply()
        assert len(reply) == 10
        assert reply[0] == 0x05
        assert reply[1] == 0x00

    def test_error_reply(self):
        from modules.socks import SOCKSClient, SOCKS5_REP_CONN_REFUSED

        reply = SOCKSClient.error_reply(SOCKS5_REP_CONN_REFUSED)
        assert len(reply) == 10
        assert reply[1] == SOCKS5_REP_CONN_REFUSED


def socket_inet_aton(addr):
    return socket.inet_aton(addr)


class TestDashboard:
    def test_index_returns_json(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "nonce" in resp.get_json()

    def test_dashboard_returns_html(self, client):
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert b"C2 CTF SecOpsDays" in resp.data

    def test_dashboard_includes_nonce(self, client):
        resp = client.get("/dashboard")
        assert b"sentrysec-2026" in resp.data

    def test_dashboard_includes_auth_token(self, client):
        resp = client.get("/dashboard")
        assert b"window.C2_AUTH_TOKEN" in resp.data
        assert b"supersecret-ctf-token" in resp.data


class TestSOCKSRoutes:
    def test_socks_status(self, client, auth_headers):
        resp = client.get("/socks/status", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert "running" in body
        assert "host" in body
        assert "port" in body

    def test_socks_start(self, client, auth_headers):
        resp = client.post(
            "/socks/start",
            headers=auth_headers,
            json={"host": "127.0.0.1", "port": 11080},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "ok"
        # Cleanup
        client.post("/socks/stop", headers=auth_headers)

    def test_socks_stop(self, client, auth_headers):
        client.post(
            "/socks/start",
            headers=auth_headers,
            json={"host": "127.0.0.1", "port": 11081},
        )
        resp = client.post("/socks/stop", headers=auth_headers)
        assert resp.status_code == 200

    def test_socks_channels(self, client, auth_headers):
        resp = client.get("/socks/channels", headers=auth_headers)
        assert resp.status_code == 200
        assert "channels" in resp.get_json()

    def test_socks_connect_missing_params(self, client, auth_headers):
        resp = client.post(
            "/socks/connect", headers=auth_headers, json={}
        )
        assert resp.status_code == 400

    def test_socks_connect_unknown_agent(self, client, auth_headers, fresh_store):
        resp = client.post(
            "/socks/connect",
            headers=auth_headers,
            json={
                "agent_id": "nonexistent",
                "target_host": "10.0.0.1",
                "target_port": 22,
            },
        )
        assert resp.status_code == 404

    def test_socks_connect_creates_channel(self, client, auth_headers, fresh_store):
        fresh_store.register(
            {"hostname": "h", "os": "L", "username": "u", "ip": "1.1.1.1"},
            agent_id="socks-agent",
        )
        resp = client.post(
            "/socks/connect",
            headers=auth_headers,
            json={
                "agent_id": "socks-agent",
                "target_host": "10.0.0.1",
                "target_port": 22,
            },
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert "channel_id" in body
        assert body["target"] == "10.0.0.1:22"

    def test_socks_data_get_empty(self, client, auth_headers):
        resp = client.get(
            "/socks/data/nonexistent_channel", headers=auth_headers
        )
        assert resp.status_code == 204

    def test_socks_data_post_missing_data(self, client, auth_headers):
        resp = client.post(
            "/socks/data/test_channel", headers=auth_headers, json={}
        )
        assert resp.status_code == 400

    def test_socks_data_post_invalid_base64(self, client, auth_headers):
        resp = client.post(
            "/socks/data/test_channel",
            headers=auth_headers,
            json={"data": "!!!not-base64!!!"},
        )
        assert resp.status_code == 400

    def test_socks_data_post_valid(self, client, auth_headers):
        import base64

        encoded = base64.b64encode(b"hello world").decode()
        resp = client.post(
            "/socks/data/test_channel",
            headers=auth_headers,
            json={"data": encoded},
        )
        assert resp.status_code == 200
        assert resp.get_json()["bytes"] == 11

    def test_socks_connected(self, client, auth_headers):
        resp = client.post(
            "/socks/connected/test_channel", headers=auth_headers
        )
        assert resp.status_code == 200

    def test_socks_status_after_start(self, client, auth_headers):
        client.post(
            "/socks/start",
            headers=auth_headers,
            json={"host": "127.0.0.1", "port": 11082},
        )
        resp = client.get("/socks/status", headers=auth_headers)
        body = resp.get_json()
        assert body["running"] is True
        # Cleanup
        client.post("/socks/stop", headers=auth_headers)
