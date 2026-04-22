"""Smoke tests — endpoint'lerin 500 atmamasini dogrular. LLM cagrisi yok."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from api.main import app
    return TestClient(app)


def test_list_agents_returns_seed(client):
    r = client.get("/api/agents")
    assert r.status_code == 200
    names = {a["name"] for a in r.json()}
    assert "Supervisor-Agent" in names
    assert "HR-Agent" in names


def test_list_agents_respects_user_header(client):
    r = client.get("/api/agents", headers={"X-User-Email": "demo@fnss.com.tr"})
    assert r.status_code == 200


def test_seed_agent_detail(client):
    r = client.get("/api/agents/HR-Agent")
    assert r.status_code == 200
    assert r.json()["name"] == "HR-Agent"


def test_cannot_delete_seed(client):
    r = client.delete("/api/agents/HR-Agent")
    assert r.status_code == 403


def test_delete_missing_agent_404(client):
    r = client.delete("/api/agents/Does-Not-Exist-Xyz")
    assert r.status_code == 404


def test_audit_log_written_by_action_tool(tmp_path, monkeypatch):
    """Action tool cagrisi gercekten dosyaya yaziyor mu."""
    from agent_factory.tools import audit, actions

    monkeypatch.setattr(audit, "_AUDIT_PATH", tmp_path / "audit.log")
    monkeypatch.setattr(actions, "_REQUEST_DIR", tmp_path / "requests")

    tools = actions.build_action_tools(
        {"email": "t@fnss.com.tr", "name": "T"}, agent_name="HR-Agent"
    )
    request_leave = next(t for t in tools if t.__name__ == "request_leave")
    out = request_leave(start_date="2026-05-01", end_date="2026-05-05", reason="tatil")

    assert "Referans" in out
    log_lines = (tmp_path / "audit.log").read_text(encoding="utf-8").strip().splitlines()
    assert len(log_lines) == 1
    entry = json.loads(log_lines[0])
    assert entry["user"] == "t@fnss.com.tr"
    assert entry["action"] == "request_leave"
    assert entry["result"]["status"] == "PENDING_APPROVAL"

    # Request dosyasi da yazilmis olmali
    files = list((tmp_path / "requests").glob("LV-*.json"))
    assert len(files) == 1


def test_user_context_resolves_default():
    from agent_factory.user_context import resolve_user
    u = resolve_user(None)
    assert u["email"] == "admin@fnss.com.tr"
    u2 = resolve_user("seda.kaya@fnss.com.tr")
    assert u2["department"] == "Finance"
