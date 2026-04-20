import json
from pathlib import Path
from .schema import AgentSpec

SPEC_DIR = Path("generated/specs")
SPEC_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> dict:
    for encoding in ("utf-8", "utf-8-sig", "cp1254", "cp1252"):
        try:
            return json.loads(path.read_text(encoding=encoding))
        except UnicodeDecodeError:
            continue
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def save_spec(spec: AgentSpec) -> Path:
    path = SPEC_DIR / f"{spec.id}.json"
    path.write_text(spec.model_dump_json(indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_spec(spec_id: str) -> AgentSpec:
    path = SPEC_DIR / f"{spec_id}.json"
    data = _read_json(path)
    return AgentSpec(**data)


def list_specs() -> list[AgentSpec]:
    specs = []
    for path in SPEC_DIR.glob("spec_*.json"):
        data = _read_json(path)
        specs.append(AgentSpec(**data))
    return sorted(specs, key=lambda s: s.created_at, reverse=True)
