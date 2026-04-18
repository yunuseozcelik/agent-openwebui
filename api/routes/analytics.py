"""Analytics endpoints — cost, usage, ecosystem."""

from __future__ import annotations

from fastapi import APIRouter

from agent_factory.builder.spec.store import list_specs
from agent_factory.deployment.foundry_client import list_agents
from agent_factory.registry import TOOL_CATALOG, get_ecosystem_summary
from utils.cost_control import cost_tracker


router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview")
async def overview():
    agents = list_agents()
    specs = list_specs()

    mock_count = sum(1 for a in agents if a.metadata.get("mock"))
    draft_count = sum(1 for a in agents if a.metadata.get("status") == "draft")
    active_count = len(agents) - mock_count - draft_count

    # Tool distribution
    tool_counts: dict[str, int] = {}
    for a in agents:
        for t in a.tools:
            tt = t.get("type") if isinstance(t, dict) else str(t)
            if tt:
                tool_counts[tt] = tool_counts.get(tt, 0) + 1

    # Risk distribution
    risk_counts = {"low": 0, "medium": 0, "high": 0}
    for s in specs:
        risk_counts[s.risk_level.value] += 1

    return {
        "agents": {
            "total": len(agents),
            "active": active_count,
            "mock": mock_count,
            "draft": draft_count,
        },
        "specs": {
            "total": len(specs),
            "by_risk": risk_counts,
        },
        "tools": tool_counts,
    }


@router.get("/cost")
async def cost():
    return cost_tracker.snapshot()


@router.post("/cost/reset")
async def cost_reset():
    cost_tracker.reset()
    return {"ok": True}


@router.get("/tool-catalog")
async def tool_catalog():
    return TOOL_CATALOG


@router.get("/ecosystem")
async def ecosystem():
    return {"summary": get_ecosystem_summary()}
