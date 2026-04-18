"""Template endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import BuildRequest, BuildResponse, TemplateDeployRequest
from ..templates import get_template, list_templates
from .builder import build as build_handler


router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("")
async def get_templates():
    return list_templates()


@router.get("/{template_id}")
async def get_single(template_id: str):
    t = get_template(template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template bulunamadi")
    return t.to_dict()


@router.post("/build", response_model=BuildResponse)
async def build_from_template(req: TemplateDeployRequest):
    t = get_template(req.template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template bulunamadi")

    overrides = req.overrides or {}

    build_req = BuildRequest(
        description=f"{t.name} - {t.description}",
        name=overrides.get("name", t.name),
        purpose=overrides.get("purpose", t.purpose),
        audience=overrides.get("audience", t.audience),
        tone=overrides.get("tone", t.tone),
        output_format=overrides.get("output_format", t.output_format),
        scope=overrides.get("scope", t.scope),
        pii=overrides.get("pii", t.pii),
        approval=overrides.get("approval", t.approval),
        example_scenario=overrides.get("example_scenario", t.example_scenario),
        inferred_tools=t.tools,
        inferred_data_sources=t.data_sources,
        suggested_capabilities=t.capabilities,
        complexity_hints={},
    )

    return await build_handler(build_req)
