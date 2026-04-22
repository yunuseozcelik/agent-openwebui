"""Role-based access kontrol testleri.

Her test bir rolu simule eder, X-User-Email header'i ile istek atar,
agent gorunurlugu + deploy + chat erisimini dogrular.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


ADMIN = "admin@fnss.com.tr"
HR = "ahmet.yilmaz@fnss.com.tr"
FINANCE = "seda.kaya@fnss.com.tr"
ENG = "mehmet.demir@fnss.com.tr"
EMPLOYEE = "demo@fnss.com.tr"


@pytest.fixture(scope="module")
def client():
    from api.main import app
    return TestClient(app)


def _agent_names(resp_json):
    return {a["name"] for a in resp_json}


# ── Kullanici endpoint ──

def test_users_list(client):
    r = client.get("/api/users")
    assert r.status_code == 200
    emails = {u["email"] for u in r.json()}
    assert {ADMIN, HR, FINANCE, ENG, EMPLOYEE} <= emails


def test_me_admin(client):
    r = client.get("/api/users/me", headers={"X-User-Email": ADMIN})
    data = r.json()
    assert "admin" in data["roles"]
    # Admin tum parent'lari gorur
    assert "HR-Agent" in data["allowed_parents"]
    assert "Finance-Agent" in data["allowed_parents"]
    assert "Supervisor-Agent" in data["allowed_parents"]


def test_me_hr(client):
    r = client.get("/api/users/me", headers={"X-User-Email": HR})
    data = r.json()
    assert data["allowed_parents"] == ["HR-Agent", "General-Agent", "Chat-Agent"]


def test_me_engineering(client):
    r = client.get("/api/users/me", headers={"X-User-Email": ENG})
    data = r.json()
    assert "IT-Agent" in data["allowed_parents"]
    assert "HR-Agent" not in data["allowed_parents"]
    assert "Finance-Agent" not in data["allowed_parents"]


def test_me_employee(client):
    r = client.get("/api/users/me", headers={"X-User-Email": EMPLOYEE})
    data = r.json()
    assert set(data["allowed_parents"]) == {"General-Agent", "Chat-Agent"}


# ── Agent listesi — gorunurluk ──

def test_admin_sees_all_agents(client):
    r = client.get("/api/agents", headers={"X-User-Email": ADMIN})
    names = _agent_names(r.json())
    assert {"HR-Agent", "IT-Agent", "Finance-Agent",
            "Math-Agent", "General-Agent", "Chat-Agent",
            "Supervisor-Agent"} <= names


def test_hr_sees_only_hr_and_public(client):
    r = client.get("/api/agents", headers={"X-User-Email": HR})
    names = _agent_names(r.json())
    assert "HR-Agent" in names           # kendi departmani
    assert "General-Agent" in names      # public
    assert "Math-Agent" in names         # public
    assert "IT-Agent" not in names       # yetkisiz
    assert "Finance-Agent" not in names  # yetkisiz


def test_engineering_sees_it_not_finance(client):
    r = client.get("/api/agents", headers={"X-User-Email": ENG})
    names = _agent_names(r.json())
    assert "IT-Agent" in names
    assert "Finance-Agent" not in names
    assert "HR-Agent" not in names


def test_finance_manager_sees_finance_and_all_restricted(client):
    r = client.get("/api/agents", headers={"X-User-Email": FINANCE})
    names = _agent_names(r.json())
    # manager rolune sahip: hepsini gorur
    assert {"HR-Agent", "IT-Agent", "Finance-Agent"} <= names


def test_employee_only_public(client):
    r = client.get("/api/agents", headers={"X-User-Email": EMPLOYEE})
    names = _agent_names(r.json())
    assert "General-Agent" in names
    assert "HR-Agent" not in names
    assert "IT-Agent" not in names
    assert "Finance-Agent" not in names


# ── Agent detay — 403 ──

def test_hr_cannot_fetch_it_agent_detail(client):
    r = client.get("/api/agents/IT-Agent", headers={"X-User-Email": HR})
    assert r.status_code == 403


def test_admin_can_fetch_any(client):
    for aid in ("IT-Agent", "Finance-Agent", "HR-Agent"):
        r = client.get(f"/api/agents/{aid}", headers={"X-User-Email": ADMIN})
        assert r.status_code == 200


def test_hr_can_fetch_hr_agent(client):
    r = client.get("/api/agents/HR-Agent", headers={"X-User-Email": HR})
    assert r.status_code == 200


# ── Chat erisimi — 403 ──

def test_hr_cannot_chat_with_finance(client):
    sess = client.post("/api/agents/session/new").json()["session_id"]
    r = client.post("/api/agents/chat", json={
        "agent_id": "Finance-Agent",
        "session_id": sess,
        "message": "test",
    }, headers={"X-User-Email": HR})
    assert r.status_code == 403


# ── Deploy — parent yetkisi ──

def _make_spec(client, name="Test-Agent"):
    """Hizlica bir spec olustur (build endpoint cagirmadan dogrudan save)."""
    from agent_factory.builder.spec.schema import AgentSpec
    from agent_factory.builder.spec.store import save_spec
    spec = AgentSpec(name=name, purpose="test", user_audience="test")
    save_spec(spec)
    return spec.id


def test_hr_cannot_deploy_under_finance(client):
    spec_id = _make_spec(client, "HR-Tries-Finance")
    r = client.post("/api/builder/deploy", json={
        "spec_id": spec_id,
        "parent_agent_name": "Finance-Agent",
    }, headers={"X-User-Email": HR})
    assert r.status_code == 403
    assert "yetki" in r.json()["detail"].lower()


def test_admin_can_deploy_under_any(client, monkeypatch):
    # deploy_prompt_agent'i mocka al — gercek Foundry cagirmayalim
    from agent_factory.deployment import foundry_client
    called = {}
    def fake_deploy(definition):
        called["parent"] = definition.get("metadata", {}).get("parent_agent_name")
        from agent_factory.deployment.foundry_client import DeploymentResult
        return DeploymentResult(success=True, foundry_agent_id="mock_xyz", mock=True)
    monkeypatch.setattr(foundry_client, "deploy_prompt_agent", fake_deploy)
    # builder.py import'undan da patch
    from api.routes import builder as builder_module
    monkeypatch.setattr(builder_module, "deploy_prompt_agent", fake_deploy)

    spec_id = _make_spec(client, "Admin-Tries-Finance")
    r = client.post("/api/builder/deploy", json={
        "spec_id": spec_id,
        "parent_agent_name": "Finance-Agent",
    }, headers={"X-User-Email": ADMIN})
    assert r.status_code == 200
    assert called["parent"] == "Finance-Agent"


def test_employee_cannot_deploy_under_hr(client):
    spec_id = _make_spec(client, "Employee-Tries-HR")
    r = client.post("/api/builder/deploy", json={
        "spec_id": spec_id,
        "parent_agent_name": "HR-Agent",
    }, headers={"X-User-Email": EMPLOYEE})
    assert r.status_code == 403


# ── Helper unit tests ──

def test_can_see_agent_admin_bypasses():
    from agent_factory.user_context import can_see_agent, resolve_user
    admin = resolve_user(ADMIN)
    assert can_see_agent(admin, {"allowed_roles": ["finance"]}) is True
    assert can_see_agent(admin, {"allowed_roles": ["nobody"]}) is True


def test_can_see_agent_no_metadata_is_public():
    from agent_factory.user_context import can_see_agent, resolve_user
    emp = resolve_user(EMPLOYEE)
    assert can_see_agent(emp, None) is True
    assert can_see_agent(emp, {}) is True


def test_can_see_agent_role_intersection():
    from agent_factory.user_context import can_see_agent, resolve_user
    hr = resolve_user(HR)
    assert can_see_agent(hr, {"allowed_roles": ["hr", "manager"]}) is True
    assert can_see_agent(hr, {"allowed_roles": ["finance"]}) is False
