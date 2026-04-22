"""Kullanici dizini — JSON dosyasinda persist olur.

Roller -> parent agent haritasi ile role-based varsayilan erisim,
ayrica admin tarafindan her kullaniciya verilebilen `extra_agents` listesi
(per-user grant) ile bireysel yetkilendirme.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

_EMPLOYEES_FILE = Path(__file__).parent / "mock_data" / "employees.json"
_DEFAULT_EMAIL = "admin@fnss.com.tr"
_LOCK = threading.Lock()


def _read_file() -> dict:
    try:
        return json.loads(_EMPLOYEES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"employees": []}


def _write_file(data: dict) -> None:
    _EMPLOYEES_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _all_employees() -> list[dict]:
    return _read_file().get("employees", [])


def _index_by_email() -> dict[str, dict]:
    return {e["email"].lower(): e for e in _all_employees()}


def resolve_user(email: str | None) -> dict:
    employees = _index_by_email()
    if email:
        u = employees.get(email.lower())
        if u:
            return u
    return employees.get(_DEFAULT_EMAIL, {
        "email": _DEFAULT_EMAIL,
        "name": "Admin",
        "department": "IT",
        "title": "Admin",
        "roles": ["admin"],
        "leave_balance_days": 0,
        "extra_agents": [],
    })


def list_users(include_grants: bool = False) -> list[dict]:
    out = []
    for e in _all_employees():
        base = {
            "email": e["email"],
            "name": e["name"],
            "department": e.get("department", ""),
            "title": e.get("title", ""),
            "roles": e.get("roles", []),
        }
        if include_grants:
            base["extra_agents"] = e.get("extra_agents", [])
        out.append(base)
    return out


def create_user(name: str, department: str, level: str,
                email: str | None = None) -> dict:
    """Departman + kademe -> unvan ve rol otomatik turetilir."""
    from agent_factory.catalog import resolve_title_and_role, slugify_email

    if not name.strip():
        raise ValueError("Isim bos olamaz")
    title, role = resolve_title_and_role(department, level)

    with _LOCK:
        data = _read_file()
        emps = data.setdefault("employees", [])
        existing = {e["email"].lower() for e in emps}
        if email:
            email = email.strip().lower()
            if email in existing:
                raise ValueError("Bu email zaten kayitli")
        else:
            email = slugify_email(name, existing)

        new_user = {
            "email": email,
            "name": name.strip(),
            "department": department,
            "title": title,
            "roles": [role],
            "leave_balance_days": 12,
            "manager": None,
            "extra_agents": [],
        }
        emps.append(new_user)
        _write_file(data)
        return new_user


def set_user_agents(email: str, agent_names: list[str]) -> dict:
    email = email.strip().lower()
    with _LOCK:
        data = _read_file()
        emps = data.get("employees", [])
        for e in emps:
            if e["email"].lower() == email:
                e["extra_agents"] = list(dict.fromkeys(agent_names))
                _write_file(data)
                return e
        raise ValueError("Kullanici bulunamadi")


_ALL_PARENTS = {
    "Supervisor-Agent", "HR-Agent", "IT-Agent", "Finance-Agent",
    "Math-Agent", "General-Agent", "Chat-Agent",
}

_ROLE_PARENT_MAP: dict[str, set[str]] = {
    "admin": _ALL_PARENTS,
    "manager": _ALL_PARENTS,
    "hr": {"HR-Agent", "General-Agent", "Chat-Agent"},
    "finance": {"Finance-Agent", "General-Agent", "Chat-Agent"},
    "engineering": {"IT-Agent", "General-Agent", "Chat-Agent"},
    "employee": {"General-Agent", "Chat-Agent"},
}


def is_admin(user: dict) -> bool:
    return "admin" in {r.lower() for r in user.get("roles", [])}


def allowed_parents_for(user: dict) -> list[str]:
    roles = {r.lower() for r in user.get("roles", [])}
    allowed: set[str] = set()
    for r in roles:
        allowed |= _ROLE_PARENT_MAP.get(r, set())
    if not allowed:
        allowed = {"General-Agent", "Chat-Agent"}
    order = ["Supervisor-Agent", "HR-Agent", "IT-Agent", "Finance-Agent",
             "Math-Agent", "General-Agent", "Chat-Agent"]
    return [n for n in order if n in allowed]


def can_see_agent(user: dict, agent_metadata: dict | None,
                  agent_name: str | None = None) -> bool:
    """Admin her zaman gorur. Per-user `extra_agents` grant varsa gorur.
    Agent'in allowed_roles'u yoksa herkese acik; varsa rol kesisimine bakilir."""
    if is_admin(user):
        return True
    if agent_name:
        extra = [a.lower() for a in user.get("extra_agents", []) or []]
        if agent_name.lower() in extra:
            return True
    allowed = (agent_metadata or {}).get("allowed_roles")
    if not allowed:
        return True
    allowed_set = {r.lower() for r in allowed}
    if "all" in allowed_set:
        return True
    user_roles = {r.lower() for r in user.get("roles", [])}
    return bool(allowed_set & user_roles)


def format_user_block(user: dict) -> str:
    return (
        "## KULLANICI (oturum baglami)\n"
        f"- Isim: {user.get('name', '-')}\n"
        f"- Email: {user.get('email', '-')}\n"
        f"- Departman: {user.get('department', '-')}\n"
        f"- Unvan: {user.get('title', '-')}\n"
        f"- Yillik izin bakiyesi (gun): {user.get('leave_balance_days', '-')}\n"
        f"- Yonetici: {user.get('manager') or '-'}\n"
        "Bu bilgileri agent kendisi bilir, kullaniciya tekrar sorma."
    )
