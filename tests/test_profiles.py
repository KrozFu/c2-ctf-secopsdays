import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from config import load_profile, LISTENER
from listener import Listener


class TestLoadProfile:
    def test_load_default_profile(self):
        profile = load_profile("profiles/default.yaml")
        assert "listener" in profile
        assert "agent" in profile
        assert "operators" in profile

    def test_default_profile_values(self):
        profile = load_profile("profiles/default.yaml")
        assert profile["listener"]["host"] == "0.0.0.0"
        assert profile["listener"]["port"] == 8080
        assert profile["agent"]["sleep"] == 5
        assert profile["agent"]["jitter"] == 20

    def test_example_profile_values(self):
        profile = load_profile("profiles/example.yaml")
        assert profile["listener"]["port"] == 443
        assert profile["listener"]["protocol"] == "https"
        assert profile["agent"]["sleep"] == 120

    def test_load_nonexistent_profile_fallback(self):
        profile = load_profile("profiles/nonexistent.yaml")
        assert profile["listener"]["host"] == "0.0.0.0"
        assert profile["agent"]["sleep"] == 30

    def test_profile_has_operators(self):
        profile = load_profile("profiles/default.yaml")
        assert len(profile["operators"]) >= 1
        assert "token" in profile["operators"][0]


class TestListener:
    def test_create_listener_from_config(self):
        config = {
            "host": "127.0.0.1",
            "port": 9090,
            "protocol": "https",
            "uris": ["/api/v1/callback"],
            "headers": {"user_agent": "TestBot"},
            "response": {"server": "nginx", "headers": {"X-Test": "value"}},
        }
        listener = Listener(config)
        assert listener.host == "127.0.0.1"
        assert listener.port == 9090
        assert listener.protocol == "https"

    def test_listener_defaults(self):
        listener = Listener({})
        assert listener.host == "0.0.0.0"
        assert listener.port == 8080
        assert listener.protocol == "http"
        assert listener.uris == []

    def test_get_callback_uris(self):
        uris = ["/register", "/heartbeat", "/task"]
        listener = Listener({"uris": uris})
        assert listener.get_callback_uris() == uris

    def test_get_fake_headers(self):
        headers = {"user_agent": "Mozilla/5.0", "content_type": "application/json"}
        listener = Listener({"headers": headers})
        assert listener.get_fake_headers() == headers

    def test_get_response_headers(self):
        response = {"headers": {"Server": "nginx", "X-Powered-By": "Flask"}}
        listener = Listener({"response": response})
        assert listener.get_response_headers() == {"Server": "nginx", "X-Powered-By": "Flask"}

    def test_get_server_header(self):
        listener = Listener({"response": {"server": "cloudflare"}})
        assert listener.get_server_header() == "cloudflare"

    def test_get_bind_address(self):
        listener = Listener({"host": "0.0.0.0", "port": 8080})
        assert listener.get_bind_address() == "0.0.0.0:8080"

    def test_get_base_url(self):
        listener = Listener({"host": "example.com", "port": 443, "protocol": "https"})
        assert listener.get_base_url() == "https://example.com:443"

    def test_repr(self):
        listener = Listener({"host": "0.0.0.0", "port": 8080, "protocol": "http"})
        assert "0.0.0.0" in repr(listener)
        assert "8080" in repr(listener)


class TestGlobalListener:
    """Tests for the global LISTENER instance created by config.py."""

    def test_global_listener_exists(self):
        assert LISTENER is not None

    def test_global_listener_from_default_profile(self):
        assert LISTENER.host == "0.0.0.0"
        assert LISTENER.port == 8080
        assert LISTENER.protocol == "http"

    def test_global_listener_has_uris(self):
        uris = LISTENER.get_callback_uris()
        assert isinstance(uris, list)
