import pytest
from models import is_command_allowed, require_token, AgentStore


class TestIsCommandAllowed:
    def test_allowed_commands(self):
        for cmd in ("whoami", "hostname", "id", "uname", "pwd", "ls", "cat", "ps", "env", "date", "uptime", "df"):
            allowed, reason = is_command_allowed(cmd)
            assert allowed, f"{cmd!r} should be allowed, got rejected: {reason}"

    def test_allowed_with_args(self):
        allowed, _ = is_command_allowed("ls -la")
        assert allowed
        allowed, _ = is_command_allowed("cat /etc/hostname")
        assert allowed
        allowed, _ = is_command_allowed("uname -a")
        assert allowed

    def test_empty_command(self):
        allowed, reason = is_command_allowed("")
        assert not allowed
        assert "vacío" in reason

    def test_whitespace_only(self):
        allowed, reason = is_command_allowed("   ")
        assert not allowed

    def test_unknown_binary(self):
        allowed, reason = is_command_allowed("rm -rf /")
        assert not allowed
        assert "no permitido" in reason

    def test_semicolon_rejected(self):
        allowed, reason = is_command_allowed("ls; whoami")
        assert not allowed
        assert "prohibido" in reason

    def test_pipe_rejected(self):
        allowed, reason = is_command_allowed("cat /etc/passwd | grep root")
        assert not allowed

    def test_ampersand_rejected(self):
        allowed, reason = is_command_allowed("ls & whoami")
        assert not allowed

    def test_backtick_rejected(self):
        allowed, reason = is_command_allowed("`whoami`")
        assert not allowed

    def test_dollar_paren_rejected(self):
        allowed, reason = is_command_allowed("$(whoami)")
        assert not allowed

    def test_redirect_rejected(self):
        allowed, reason = is_command_allowed("ls > /tmp/out")
        assert not allowed

    def test_less_than_rejected(self):
        allowed, reason = is_command_allowed("cat < /etc/passwd")
        assert not allowed

    def test_newline_rejected(self):
        allowed, reason = is_command_allowed("ls\nwhoami")
        assert not allowed

    def test_malformed_command(self):
        allowed, reason = is_command_allowed("cat 'unclosed")
        assert not allowed


class TestAgentStore:
    def test_register(self, fresh_store):
        info = {"hostname": "test-host", "os": "Linux", "username": "user", "ip": "10.0.0.1"}
        agent_id = fresh_store.register(info)
        assert agent_id is not None
        assert agent_id in fresh_store.agents
        assert fresh_store.agents[agent_id]["hostname"] == "test-host"

    def test_register_with_custom_id(self, fresh_store):
        info = {"hostname": "h", "os": "Linux", "username": "u", "ip": "10.0.0.1"}
        agent_id = fresh_store.register(info, agent_id="my-agent")
        assert agent_id == "my-agent"

    def test_heartbeat_known_agent(self, fresh_store):
        info = {"hostname": "h", "os": "Linux", "username": "u", "ip": "10.0.0.1"}
        agent_id = fresh_store.register(info)
        assert fresh_store.heartbeat(agent_id) is True

    def test_heartbeat_unknown_agent(self, fresh_store):
        assert fresh_store.heartbeat("nonexistent") is False

    def test_add_task(self, fresh_store):
        info = {"hostname": "h", "os": "Linux", "username": "u", "ip": "10.0.0.1"}
        agent_id = fresh_store.register(info)
        task = fresh_store.add_task(agent_id, "whoami")
        assert task is not None
        assert task["command"] == "whoami"
        assert task["status"] == "pending"

    def test_add_task_unknown_agent(self, fresh_store):
        result = fresh_store.add_task("nonexistent", "whoami")
        assert result is None

    def test_next_task_dispatches(self, fresh_store):
        info = {"hostname": "h", "os": "Linux", "username": "u", "ip": "10.0.0.1"}
        agent_id = fresh_store.register(info)
        fresh_store.add_task(agent_id, "whoami")
        task = fresh_store.next_task(agent_id)
        assert task is not None
        assert task["status"] == "dispatched"

    def test_next_task_returns_none_when_empty(self, fresh_store):
        info = {"hostname": "h", "os": "Linux", "username": "u", "ip": "10.0.0.1"}
        agent_id = fresh_store.register(info)
        task = fresh_store.next_task(agent_id)
        assert task is None

    def test_save_result(self, fresh_store):
        info = {"hostname": "h", "os": "Linux", "username": "u", "ip": "10.0.0.1"}
        agent_id = fresh_store.register(info)
        task = fresh_store.add_task(agent_id, "whoami")
        fresh_store.save_result(agent_id, task["task_id"], "root")
        results = fresh_store.results_for(agent_id)
        assert len(results) == 1
        assert results[0]["output"] == "root"

    def test_list_agents(self, fresh_store):
        info = {"hostname": "h", "os": "Linux", "username": "u", "ip": "10.0.0.1"}
        fresh_store.register(info)
        agents = fresh_store.list_agents()
        assert len(agents) == 1

    def test_thread_safety_register(self, fresh_store):
        import threading

        def register_many():
            for _ in range(50):
                fresh_store.register({"hostname": "h", "os": "Linux", "username": "u", "ip": "10.0.0.1"})

        threads = [threading.Thread(target=register_many) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(fresh_store.agents) == 200
