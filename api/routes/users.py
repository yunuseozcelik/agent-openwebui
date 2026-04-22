"""Users endpoint — liste, katalog, kayit, per-user agent grantlari."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from agent_factory.catalog import catalog
from agent_factory.user_context import (
    allowed_parents_for,
    create_user,
    is_admin,
    list_users,
    resolve_user,
    set_user_agents,
)


router = APIRouter(prefix="/api/users", tags=["users"])


class RegisterRequest(BaseModel):
    name: str
    department: str
    level: str


class GrantRequest(BaseModel):
    agents: list[str] = Field(default_factory=list)


@router.get("")
async def get_users(x_user_email: str | None = Header(default=None)):
    user = resolve_user(x_user_email)
    return list_users(include_grants=is_admin(user))


@router.get("/catalog")
async def get_catalog():
    return catalog()


@router.get("/me")
async def me(x_user_email: str | None = Header(default=None)):
    user = resolve_user(x_user_email)
    return {
        "email": user.get("email"),
        "name": user.get("name"),
        "department": user.get("department"),
        "title": user.get("title"),
        "roles": user.get("roles", []),
        "extra_agents": user.get("extra_agents", []),
        "allowed_parents": allowed_parents_for(user),
    }


@router.post("/register")
async def register(req: RegisterRequest):
    try:
        u = create_user(name=req.name, department=req.department, level=req.level)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"success": True, "user": {
        "email": u["email"], "name": u["name"],
        "department": u["department"], "title": u["title"],
        "roles": u["roles"],
    }}


@router.patch("/{email}/agents")
async def grant_agents(email: str, req: GrantRequest,
                       x_user_email: str | None = Header(default=None)):
    caller = resolve_user(x_user_email)
    if not is_admin(caller):
        raise HTTPException(status_code=403, detail="Sadece admin yetki verebilir")
    try:
        u = set_user_agents(email, req.agents)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"success": True, "email": u["email"], "extra_agents": u.get("extra_agents", [])}
