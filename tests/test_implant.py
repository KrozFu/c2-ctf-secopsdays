import subprocess
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "implant"))


class TestImplantWhitelist:
    """Tests for the implant's local command whitelist and execution."""

    def _run_implant_function(self, func_code, input_data=None):
        script = f"""
import sys
sys.path.insert(0, ".")
from implant import {func_code}
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), "..", "implant"),
            timeout=5,
        )
        return result

    def test_run_command_allowed(self):
        result = subprocess.run(
            [sys.executable, "-c", "from implant import run_command; print(repr(run_command('whoami')))"],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), "..", "implant"),
            timeout=5,
        )
        assert result.returncode == 0
        assert "[implant]" not in result.stdout

    def test_run_command_not_allowed(self):
        result = subprocess.run(
            [sys.executable, "-c", "from implant import run_command; print(repr(run_command('rm -rf /')))"],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), "..", "implant"),
            timeout=5,
        )
        assert result.returncode == 0
        assert "no permitido" in result.stdout

    def test_run_command_with_args(self):
        result = subprocess.run(
            [sys.executable, "-c", "from implant import run_command; print(repr(run_command('ls -la /tmp')))"],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), "..", "implant"),
            timeout=5,
        )
        assert result.returncode == 0

    def test_run_command_empty(self):
        result = subprocess.run(
            [sys.executable, "-c", "from implant import run_command; print(repr(run_command('')))"],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), "..", "implant"),
            timeout=5,
        )
        assert result.returncode == 0
        assert "no permitido" in result.stdout

    def test_generate_id_deterministic(self):
        result = subprocess.run(
            [sys.executable, "-c", "from implant import generate_id; print(generate_id())"],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), "..", "implant"),
            timeout=5,
        )
        assert result.returncode == 0
        id1 = result.stdout.strip()

        result = subprocess.run(
            [sys.executable, "-c", "from implant import generate_id; print(generate_id())"],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), "..", "implant"),
            timeout=5,
        )
        id2 = result.stdout.strip()
        assert id1 == id2, "generate_id should be deterministic for the same host"

    def test_collect_info_returns_dict(self):
        result = subprocess.run(
            [sys.executable, "-c", """
from implant import collect_info
import json
info = collect_info()
assert isinstance(info, dict)
assert 'hostname' in info
assert 'os' in info
assert 'username' in info
assert 'ip' in info
assert 'agent_id' in info
print(json.dumps(info))
"""],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), "..", "implant"),
            timeout=5,
        )
        assert result.returncode == 0


class TestImplantCLI:
    def test_implant_imports_ok(self):
        result = subprocess.run(
            [sys.executable, "-c", "import implant; print('ok')"],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), "..", "implant"),
            timeout=5,
        )
        assert result.returncode == 0
        assert "ok" in result.stdout
