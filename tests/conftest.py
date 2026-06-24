import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from app import create_app
from models import AgentStore, store


import pytest


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def auth_headers():
    return {"X-Auth-Token": "supersecret-ctf-token", "Content-Type": "application/json"}


@pytest.fixture
def fresh_store():
    old_agents = store.agents.copy()
    old_tasks = store.tasks.copy()
    old_results = store.results[:]
    store.agents.clear()
    store.tasks.clear()
    store.results.clear()
    yield store
    store.agents.update(old_agents)
    store.tasks.update(old_tasks)
    store.results[:] = old_results
