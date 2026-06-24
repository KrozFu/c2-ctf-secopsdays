import json
import pytest


class TestIndexEndpoint:
    def test_index_no_auth(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["name"] == "C2 CTF SecOpsDays"
        assert body["nonce"] == "sentrysec-2026"
        assert body["status"] == "running"
        assert "endpoints" in body

    def test_index_ignores_auth(self, client, auth_headers):
        resp = client.get("/", headers=auth_headers)
        assert resp.status_code == 200


class TestHealthEndpoint:
    def test_health_no_auth(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"

    def test_health_ignores_auth(self, client, auth_headers):
        resp = client.get("/health", headers=auth_headers)
        assert resp.status_code == 200


class TestRegisterEndpoint:
    def test_register_success(self, client, auth_headers, fresh_store):
        data = {
            "agent_id": "test-agent-1",
            "hostname": "host1",
            "os": "Linux 5.15",
            "username": "user1",
            "ip": "10.0.0.1",
        }
        resp = client.post("/register", headers=auth_headers, data=json.dumps(data))
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["agent_id"] == "test-agent-1"
        assert "heartbeat_interval" in body

    def test_register_no_token(self, client):
        resp = client.post(
            "/register",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"hostname": "h"}),
        )
        assert resp.status_code == 401

    def test_register_wrong_token(self, client):
        resp = client.post(
            "/register",
            headers={"X-Auth-Token": "wrong-token", "Content-Type": "application/json"},
            data=json.dumps({"hostname": "h"}),
        )
        assert resp.status_code == 401

    def test_register_generates_id(self, client, auth_headers, fresh_store):
        resp = client.post(
            "/register",
            headers=auth_headers,
            data=json.dumps({"hostname": "h", "os": "Linux", "username": "u", "ip": "10.0.0.1"}),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["agent_id"] is not None


class TestHeartbeatEndpoint:
    def test_heartbeat_known_agent(self, client, auth_headers, fresh_store):
        fresh_store.register({"hostname": "h", "os": "Linux", "username": "u", "ip": "10.0.0.1"}, agent_id="hb-agent")
        resp = client.post(
            "/heartbeat",
            headers=auth_headers,
            data=json.dumps({"agent_id": "hb-agent"}),
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"

    def test_heartbeat_unknown_agent(self, client, auth_headers):
        resp = client.post(
            "/heartbeat",
            headers=auth_headers,
            data=json.dumps({"agent_id": "nonexistent"}),
        )
        assert resp.status_code == 404

    def test_heartbeat_no_auth(self, client):
        resp = client.post(
            "/heartbeat",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"agent_id": "x"}),
        )
        assert resp.status_code == 401


class TestTaskEndpoints:
    def test_enqueue_and_get_task(self, client, auth_headers, fresh_store):
        fresh_store.register({"hostname": "h", "os": "L", "username": "u", "ip": "1.1.1.1"}, agent_id="t-agent")

        resp = client.post(
            "/task/t-agent",
            headers=auth_headers,
            data=json.dumps({"command": "whoami"}),
        )
        assert resp.status_code == 201
        task = resp.get_json()["task"]
        assert task["command"] == "whoami"

        resp = client.get("/task/t-agent", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["task"] is not None
        assert body["task"]["command"] == "whoami"

    def test_get_task_none_pending(self, client, auth_headers, fresh_store):
        fresh_store.register({"hostname": "h", "os": "L", "username": "u", "ip": "1.1.1.1"}, agent_id="no-task")
        resp = client.get("/task/no-task", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["task"] is None

    def test_enqueue_rejects_forbidden_command(self, client, auth_headers, fresh_store):
        fresh_store.register({"hostname": "h", "os": "L", "username": "u", "ip": "1.1.1.1"}, agent_id="sec-agent")
        resp = client.post(
            "/task/sec-agent",
            headers=auth_headers,
            data=json.dumps({"command": "rm -rf /"}),
        )
        assert resp.status_code == 400
        assert "no permitido" in resp.get_json()["error"]

    def test_enqueue_rejects_injection(self, client, auth_headers, fresh_store):
        fresh_store.register({"hostname": "h", "os": "L", "username": "u", "ip": "1.1.1.1"}, agent_id="inj-agent")
        resp = client.post(
            "/task/inj-agent",
            headers=auth_headers,
            data=json.dumps({"command": "whoami; rm -rf /"}),
        )
        assert resp.status_code == 400

    def test_enqueue_unknown_agent(self, client, auth_headers):
        resp = client.post(
            "/task/ghost",
            headers=auth_headers,
            data=json.dumps({"command": "whoami"}),
        )
        assert resp.status_code == 404


class TestResultEndpoint:
    def test_post_and_get_result(self, client, auth_headers, fresh_store):
        fresh_store.register({"hostname": "h", "os": "L", "username": "u", "ip": "1.1.1.1"}, agent_id="r-agent")
        task = fresh_store.add_task("r-agent", "whoami")

        resp = client.post(
            "/result/r-agent",
            headers=auth_headers,
            data=json.dumps({"task_id": task["task_id"], "output": "root"}),
        )
        assert resp.status_code == 200

        resp = client.get("/results/r-agent", headers=auth_headers)
        assert resp.status_code == 200
        results = resp.get_json()["results"]
        assert len(results) == 1
        assert results[0]["output"] == "root"

    def test_get_results_empty(self, client, auth_headers, fresh_store):
        fresh_store.register({"hostname": "h", "os": "L", "username": "u", "ip": "1.1.1.1"}, agent_id="empty-r")
        resp = client.get("/results/empty-r", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["results"] == []


class TestListAgentsEndpoint:
    def test_list_agents(self, client, auth_headers, fresh_store):
        fresh_store.register({"hostname": "h1", "os": "L", "username": "u1", "ip": "1.1.1.1"}, agent_id="a1")
        fresh_store.register({"hostname": "h2", "os": "L", "username": "u2", "ip": "1.1.1.2"}, agent_id="a2")
        resp = client.get("/agents", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["count"] == 2
        assert body["nonce"] == "sentrysec-2026"

    def test_list_agents_no_auth(self, client):
        resp = client.get("/agents")
        assert resp.status_code == 401


class TestAuthSecurity:
    def test_empty_token_rejected(self, client):
        resp = client.get(
            "/agents",
            headers={"X-Auth-Token": "", "Content-Type": "application/json"},
        )
        assert resp.status_code == 401

    def test_missing_header_rejected(self, client):
        resp = client.get("/agents")
        assert resp.status_code == 401

    def test_token_with_semicolon_rejected(self, client):
        resp = client.get(
            "/agents",
            headers={"X-Auth-Token": "token;injection", "Content-Type": "application/json"},
        )
        assert resp.status_code == 401
