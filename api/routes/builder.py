"""Builder endpoints — analyze, build, deploy + SSE streaming."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from sse_starlette.sse import EventSourceResponse

from agent_factory.builder.copilot.analyzer import (
    build_final_spec_data,
    generate_rich_instructions,
    parse_description,
)
from agent_factory.builder.spec.schema import AgentSpec, RiskLevel, ToolSpec
from agent_factory.builder.spec.store import load_spec, save_spec
from agent_factory.builder.workflow import run_pipeline
from agent_factory.deployment.foundry_client import deploy_prompt_agent
from agent_factory.registry import build_interaction_graph, suggest_integrations_for_new_agent

from ..schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    BuildRequest,
    BuildResponse,
    DeployRequest,
    DeployResponse,
)


router = APIRouter(prefix="/api/builder", tags=["builder"])


def _read_json_with_encoding_fallback(path: Path) -> dict:
    """Read older generated JSON files that may have been written with Windows encoding."""
    for encoding in ("utf-8", "utf-8-sig", "cp1254", "cp1252"):
        try:
            return json.loads(path.read_text(encoding=encoding))
        except UnicodeDecodeError:
            continue
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


# ══════════════════════════════════════════════════
#  1. Analyze
# ══════════════════════════════════════════════════

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    if not req.description.strip():
        raise HTTPException(status_code=400, detail="Aciklama bos olamaz")

    try:
        result = await parse_description(req.description)
        # Infer parent agent for preview
        try:
            from agent_factory.deployment.foundry_client import _infer_parent_name
            inferred_parent = _infer_parent_name(
                f"{result.get('name', '')} {result.get('purpose', '')} {req.description}"
            )
            result["inferred_parent"] = inferred_parent
        except Exception:
            pass
        return AnalyzeResponse(**{k: v for k, v in result.items() if k in AnalyzeResponse.model_fields})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analiz hatasi: {exc}")


@router.get("/analyze/stream")
async def analyze_stream(description: str):
    """SSE ile canli analiz — 'aciliyor' hissi vermek icin."""
    from ..streaming import sse_event

    async def generator():
        yield sse_event("progress", {"step": "start", "message": "Talebiniz inceleniyor..."})
        await asyncio.sleep(0.3)

        yield sse_event("progress", {"step": "understanding", "message": "Amac ve kapsam cikariliyor..."})
        try:
            result = await parse_description(description)
            yield sse_event("progress", {"step": "tools", "message": "Gerekli araclar tespit ediliyor..."})
            await asyncio.sleep(0.2)
            yield sse_event("progress", {"step": "capabilities", "message": "Yetenekler listeleniyor..."})
            await asyncio.sleep(0.2)
            yield sse_event("result", result)
            yield sse_event("done", {})
        except Exception as exc:
            yield sse_event("error", {"message": str(exc)})

    return EventSourceResponse(generator())


# ══════════════════════════════════════════════════
#  2. Build (finalize spec + run pipeline)
# ══════════════════════════════════════════════════

def _to_spec(data: dict, req: BuildRequest) -> AgentSpec:
    tool_specs = []
    for t in data.get("tools", []) or []:
        if isinstance(t, dict) and t.get("name"):
            try:
                tool_specs.append(ToolSpec(
                    name=t["name"],
                    type=t.get("type", "file_reader"),
                    description=t.get("description", ""),
                ))
            except Exception:
                pass

    if not tool_specs:
        for tt in req.inferred_tools:
            tool_specs.append(ToolSpec(name=tt, type=tt, description=f"{tt} araci"))

    try:
        risk = RiskLevel(data.get("risk_level", "low"))
    except ValueError:
        risk = RiskLevel.LOW

    hints = req.complexity_hints or {}

    return AgentSpec(
        name=data.get("name", req.name) or req.name or "Isimsiz Agent",
        purpose=data.get("purpose", req.purpose) or req.purpose,
        user_audience=data.get("user_audience", req.audience),
        data_sources=data.get("data_sources", req.inferred_data_sources),
        tools=tool_specs,
        risk_level=risk,
        contains_pii=data.get("contains_pii", req.pii in ("true", "maybe")),
        approval_required=data.get("approval_required", req.approval in ("true", "conditional")),
        needs_supervisor=hints.get("needs_supervisor", False),
        custom_state_required=hints.get("custom_state_required", False),
        decision_points=hints.get("decision_points", 0),
    )


@router.post("/build", response_model=BuildResponse)
async def build(req: BuildRequest):
    # 1. LLM ile final spec data
    try:
        spec_data = await build_final_spec_data(
            description=req.description,
            name=req.name,
            purpose=req.purpose,
            audience=req.audience,
            pii=req.pii,
            approval=req.approval,
            inferred_tools=req.inferred_tools,
            inferred_data_sources=req.inferred_data_sources,
            tone=req.tone,
            output_format=req.output_format,
            scope=req.scope,
            example_scenario=req.example_scenario,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Spec olusturma hatasi: {exc}")

    spec = _to_spec(spec_data, req)
    save_spec(spec)

    # 2. LLM instructions
    instructions = None
    try:
        instructions = await generate_rich_instructions(
            name=spec.name,
            purpose=spec.purpose,
            audience=req.audience,
            tone=req.tone,
            output_format=req.output_format,
            scope=req.scope,
            example_scenario=req.example_scenario,
            tools=req.inferred_tools,
            data_sources=req.inferred_data_sources,
            pii=req.pii,
            approval=req.approval,
        )
    except Exception:
        instructions = None

    # 3. Pipeline
    wizard_answers = {
        "audience": req.audience,
        "tone": req.tone,
        "output_format": req.output_format,
        "scope": req.scope,
        "pii": req.pii,
        "approval": req.approval,
        "example_scenario": req.example_scenario,
        "inferred_tools": req.inferred_tools,
        "inferred_data_sources": req.inferred_data_sources,
    }

    try:
        pipeline = run_pipeline(
            spec.id,
            wizard_answers=wizard_answers,
            custom_instructions=instructions,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline hatasi: {exc}")

    # 4. Integrations (text-based)
    integrations_md = suggest_integrations_for_new_agent(
        purpose=spec.purpose,
        tool_types=req.inferred_tools,
    )
    integrations_list = []
    if integrations_md:
        for line in integrations_md.split("\n"):
            line = line.strip().lstrip("-").strip()
            if line and not line.startswith("#"):
                integrations_list.append(line)

    # 5. Graph (plotly figure -> JSON)
    graph_json = None
    try:
        fig = build_interaction_graph(
            new_agent_name=spec.name,
            new_agent_purpose=spec.purpose,
            new_agent_tools=req.inferred_tools,
        )
        if fig:
            graph_json = fig.to_plotly_json()
            # datetime/object fields'i serialize edilebilir yap
            import json as _json
            graph_json = _json.loads(_json.dumps(graph_json, default=str))
    except Exception:
        graph_json = None

    pipeline_dict = {
        "stages": [asdict(s) for s in pipeline.stages],
        "review_summary": pipeline.review_summary,
        "definition": pipeline.definition,
    }

    return BuildResponse(
        spec_id=spec.id,
        spec=spec.model_dump(mode="json"),
        instructions=instructions or pipeline.definition.get("instructions", ""),
        pipeline=pipeline_dict,
        ready_for_approval=pipeline.ready_for_approval,
        integrations=integrations_list[:5],
        graph=graph_json,
    )


@router.post("/build/stream")
async def build_stream(req: BuildRequest):
    """SSE ile canli build — her asama icin event."""
    from ..streaming import sse_event

    async def generator():
        yield sse_event("stage", {"name": "spec", "status": "running", "message": "Agent spec'i olusturuluyor..."})
        try:
            spec_data = await build_final_spec_data(
                description=req.description,
                name=req.name,
                purpose=req.purpose,
                audience=req.audience,
                pii=req.pii,
                approval=req.approval,
                inferred_tools=req.inferred_tools,
                inferred_data_sources=req.inferred_data_sources,
                tone=req.tone,
                output_format=req.output_format,
                scope=req.scope,
                example_scenario=req.example_scenario,
            )
        except Exception as exc:
            yield sse_event("error", {"message": f"Spec hatasi: {exc}"})
            return

        spec = _to_spec(spec_data, req)
        save_spec(spec)
        yield sse_event("stage", {"name": "spec", "status": "pass", "data": {"spec_id": spec.id, "name": spec.name}})

        yield sse_event("stage", {"name": "instructions", "status": "running", "message": "Sistem talimatlari yaziliyor..."})
        instructions = None
        try:
            instructions = await generate_rich_instructions(
                name=spec.name, purpose=spec.purpose, audience=req.audience,
                tone=req.tone, output_format=req.output_format, scope=req.scope,
                example_scenario=req.example_scenario,
                tools=req.inferred_tools, data_sources=req.inferred_data_sources,
                pii=req.pii, approval=req.approval,
            )
        except Exception:
            instructions = None
        yield sse_event("stage", {"name": "instructions", "status": "pass", "data": {"length": len(instructions or "")}})

        wizard_answers = {
            "audience": req.audience, "tone": req.tone, "output_format": req.output_format,
            "scope": req.scope, "pii": req.pii, "approval": req.approval,
            "example_scenario": req.example_scenario,
            "inferred_tools": req.inferred_tools,
            "inferred_data_sources": req.inferred_data_sources,
        }

        try:
            pipeline = run_pipeline(spec.id, wizard_answers=wizard_answers, custom_instructions=instructions)
        except Exception as exc:
            yield sse_event("error", {"message": f"Pipeline: {exc}"})
            return

        for stage in pipeline.stages:
            yield sse_event("stage", {"name": stage.name, "status": stage.status, "data": stage.data})
            await asyncio.sleep(0.15)

        integrations_md = suggest_integrations_for_new_agent(
            purpose=spec.purpose, tool_types=req.inferred_tools,
        )
        integrations_list = []
        if integrations_md:
            for line in integrations_md.split("\n"):
                line = line.strip().lstrip("-").strip()
                if line and not line.startswith("#"):
                    integrations_list.append(line)

        graph_json = None
        try:
            fig = build_interaction_graph(
                new_agent_name=spec.name, new_agent_purpose=spec.purpose,
                new_agent_tools=req.inferred_tools,
            )
            if fig:
                import json as _json
                graph_json = _json.loads(_json.dumps(fig.to_plotly_json(), default=str))
        except Exception:
            graph_json = None

        yield sse_event("result", {
            "spec_id": spec.id,
            "spec": spec.model_dump(mode="json"),
            "instructions": instructions or pipeline.definition.get("instructions", ""),
            "pipeline": {
                "stages": [asdict(s) for s in pipeline.stages],
                "review_summary": pipeline.review_summary,
                "definition": pipeline.definition,
            },
            "ready_for_approval": pipeline.ready_for_approval,
            "integrations": integrations_list[:5],
            "graph": graph_json,
        })
        yield sse_event("done", {})

    return EventSourceResponse(generator())


# ══════════════════════════════════════════════════
#  3. Deploy
# ══════════════════════════════════════════════════

@router.post("/deploy", response_model=DeployResponse)
async def deploy(req: DeployRequest, x_user_email: str | None = Header(default=None)):
    from agent_factory.user_context import allowed_parents_for, resolve_user

    user = resolve_user(x_user_email)
    allowed_parents = set(allowed_parents_for(user))

    # Kullanicinin rolu istenen parent'a yetkili mi?
    requested_parent = req.parent_agent_name or "Supervisor-Agent"
    if requested_parent not in allowed_parents:
        raise HTTPException(
            status_code=403,
            detail=f"'{user.get('name')}' rolunun '{requested_parent}' altina agent ekleme yetkisi yok. "
                   f"Izin verilen: {', '.join(sorted(allowed_parents))}",
        )

    try:
        spec = load_spec(req.spec_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Spec bulunamadi: {exc}")

    # Build asamasinda uretilen zengin definition varsa onu kullan.
    # Yoksa geriye uyumluluk icin definition'i yeniden uret.
    from agent_factory.builder.scaffolder.prompt_agent import scaffold_prompt_agent
    definition_path = Path("generated/agents") / f"{spec.id}_definition.json"
    if definition_path.exists():
        definition = _read_json_with_encoding_fallback(definition_path)
    else:
        definition = scaffold_prompt_agent(spec)

    # Uygulama override'larini uygula (builder on izleme ekranindan)
    if req.name:
        definition["name"] = req.name
    if req.purpose:
        definition["purpose"] = req.purpose
    if req.instructions:
        definition["instructions"] = req.instructions
    if req.parent_agent_name is not None:
        metadata = dict(definition.get("metadata", {}))
        metadata["parent_agent_name"] = req.parent_agent_name
        # Parent'in allowed_roles'unu miras al
        from agent_factory.deployment.seed_agents import SEED_AGENT_DEFINITIONS
        parent_def = next((d for d in SEED_AGENT_DEFINITIONS if d["name"] == req.parent_agent_name), None)
        if parent_def:
            inherited = parent_def.get("metadata", {}).get("allowed_roles")
            if inherited:
                metadata["allowed_roles"] = list(inherited)
        definition["metadata"] = metadata

    # Spec dosyasini da guncelle ki UI tutarli kalsin
    if req.name or req.purpose or req.instructions:
        try:
            if req.name:
                spec.name = req.name
            if req.purpose:
                spec.purpose = req.purpose
            save_spec(spec)
        except Exception:
            pass

    result = deploy_prompt_agent(definition)

    return DeployResponse(
        success=result.success,
        foundry_agent_id=result.foundry_agent_id,
        name=spec.name,
        mock=result.mock,
        error=result.error,
        application_updated=result.application_updated,
        application_update_error=result.application_update_error,
        workflow_update=(result.raw or {}).get("workflow_update") if result.raw else None,
    )
