import json
from pathlib import Path
from .schema import AgentSpec

SPEC_DIR = Path("generated/specs")
SPEC_DIR.mkdir(parents=True, exist_ok=True)


def save_spec(spec: AgentSpec) -> Path:
    path = SPEC_DIR / f"{spec.id}.json"
    path.write_text(spec.model_dump_json(indent=2, ensure_ascii=False))
    return path


def load_spec(spec_id: str) -> AgentSpec:
    path = SPEC_DIR / f"{spec_id}.json"
    data = json.loads(path.read_text())
    return AgentSpec(**data)


def list_specs() -> list[AgentSpec]:
    specs = []
    for path in SPEC_DIR.glob("spec_*.json"):
        data = json.loads(path.read_text())
        specs.append(AgentSpec(**data))
    return sorted(specs, key=lambda s: s.created_at, reverse=True)
