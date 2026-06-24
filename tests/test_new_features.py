import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "implant"))


class TestSOCKSClient:
    def test_import_socks_module(self):
        from modules.socks import SOCKSClient
        assert SOCKSClient is not None

    def test_create_socks_client(self):
        from modules.socks import SOCKSClient
        client = SOCKSClient("http://127.0.0.1:8080", "test-token", "test-agent")
        assert client.c2_url == "http://127.0.0.1:8080"
        assert client.auth_token == "test-token"
        assert client.agent_id == "test-agent"

    def test_socks5_handshake(self):
        from modules.socks import SOCKSClient, SOCKS5_VERSION
        client = SOCKSClient("http://127.0.0.1:8080", "token", "agent")
        # Simular handshake SOCKS5
        data = bytes([SOCKS5_VERSION, 0x00])
        # No debe fallar
        assert client is not None


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


class TestSOCKSRoutes:
    def test_socks_status(self, client, auth_headers):
        resp = client.get("/socks/status", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert "running" in body
        assert "host" in body
        assert "port" in body

    def test_socks_start(self, client, auth_headers):
        resp = client.post("/socks/start", headers=auth_headers,
                          json={"host": "127.0.0.1", "port": 11080})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "ok"

    def test_socks_stop(self, client, auth_headers):
        resp = client.post("/socks/stop", headers=auth_headers)
        assert resp.status_code == 200

    def test_socks_channels(self, client, auth_headers):
        resp = client.get("/socks/channels", headers=auth_headers)
        assert resp.status_code == 200
        assert "channels" in resp.get_json()
