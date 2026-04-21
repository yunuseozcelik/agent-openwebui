"""Local multi-agent orchestrator — dynamic agent index.

Akis:
  User message -> Supervisor-Agent -> Secilen agentlar -> Synthesis-Agent

Custom agentlar AGENT_DIR daki JSON dosyalarindan otomatik yuklenir.
Yeni bir deploy sonrasi sunucu yeniden baslatilmadan etkili olur.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator

from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient

from agent_factory.config import OPENAI_API_KEY, OPENAI_MODEL
from agent_factory.deployment.seed_agents import SEED_AGENT_DEFINITIONS
from agent_factory.mock_data.context_loader import get_mock_context
from utils.portkey import get_maf_client_options

AGENT_DIR = Path("generated/agents")

_CONVERSATIONAL_AGENTS = {"Chat-Agent", "General-Agent"}


@dataclass
class StepEvent:
    type: str          # routing | agent_start | agent_done | synthesis | done | error
    agent: str = ""
    text: str = ""
    selected: list[str] = field(default_factory=list)


def _make_client(name: str) -> OpenAIChatClient:
    return OpenAIChatClient(
        **get_maf_client_options(
            model_id=OPENAI_MODEL,
            primary_api_key=OPENAI_API_KEY,
            engine="orchestrator",
            component=name,
        )
    )


# ---------------------------------------------------------------------------
# Dynamic agent index
# ---------------------------------------------------------------------------

def _load_agent_index() -> dict[str, dict]:
    """Merge seed definitions + custom agents from local JSON files."""
    index: dict[str, dict] = {d["name"]: d for d in SEED_AGENT_DEFINITIONS}

    if not AGENT_DIR.exists():
        return index

    for path in AGENT_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            name = data.get("name", "")
            if not name or name in index:
                continue
            instructions = data.get("instructions", "")
            if not instructions:
                continue
            purpose = (
                data.get("metadata", {}).get("purpose", "")
                or data.get("purpose", "")
                or instructions[:120].replace("\n", " ")
            )
            index[name] = {
                "name": name,
                "instructions": instructions,
                "purpose": purpose,
                "tools": data.get("tools", []),
                "metadata": data.get("metadata", {}),
            }
        except Exception:
            continue

    return index


def _supervisor_instructions(index: dict[str, dict]) -> str:
    excluded = {"Supervisor-Agent", "Synthesis-Agent", "FNSS", "FNSS-Workflow"}
    lines = []
    for name, defn in index.items():
        if name in excluded:
            continue
        purpose = defn.get("purpose", "")
        lines.append(f"- {name}: {purpose[:100]}" if purpose else f"- {name}")

    agent_list = "\n".join(lines)
    base = next(
        (d["instructions"] for d in SEED_AGENT_DEFINITIONS if d["name"] == "Supervisor-Agent"),
        ""
    )
    return (
        f"{base}\n\n"
        "## MEVCUT AGENTLAR\n"
        f"Asagidaki agentlari kullanabilirsin:\n{agent_list}\n\n"
        "SELECTED_AGENTS formatinda yalnizca bu listeden sec."
    )


def _make_agent(name: str, user_message: str = "",
                index: dict[str, dict] | None = None) -> Agent | None:
    if index is None:
        index = _load_agent_index()

    if name == "Supervisor-Agent":
        instructions = _supervisor_instructions(index)
    else:
        defn = index.get(name)
        if not defn:
            return None
        mock_ctx = get_mock_context(name, name) or get_mock_context(user_message, "")
        instructions = (
            "## DAVRANIS KURALLARI\n"
            "- Cevaplar kisa ve net olsun.\n"
            "- Asla veri uydurma; asagida 'MEVCUT VERI' varsa yalnizca onu kullan.\n"
            "- Veri yoksa kullanicidan talep et.\n\n"
            "## GOREV\n"
            f"{defn['instructions']}"
        )
        if mock_ctx:
            instructions += f"\n\n{mock_ctx}"

    return Agent(
        client=_make_client(name),
        name=name,
        instructions=instructions,
    )


def _parse_selected_agents(supervisor_text: str, index: dict[str, dict]) -> list[str]:
    match = re.search(r"SELECTED_AGENTS:\s*(.+)", supervisor_text, re.IGNORECASE)
    if not match:
        return ["General-Agent"]
    raw = match.group(1).strip()
    raw = re.split(r"[\.\n]", raw)[0]
    names = [n.strip() for n in raw.split(",")]
    excluded = {"Supervisor-Agent", "Synthesis-Agent"}
    valid = [n for n in names if n in index and n not in excluded]
    return valid or ["General-Agent"]


async def _run_agent(name: str, prompt: str, user_message: str = "",
                     index: dict[str, dict] | None = None) -> str:
    agent = _make_agent(name, user_message, index)
    if not agent:
        return f"{name}: agent tanimli degil."
    resp = await agent.run(prompt)
    return getattr(resp, "text", "") or str(getattr(resp, "value", ""))


# ---------------------------------------------------------------------------
# Orchestration pipeline
# ---------------------------------------------------------------------------

async def orchestrate(user_message: str) -> AsyncIterator[StepEvent]:
    index = _load_agent_index()

    if "Supervisor-Agent" not in index:
        yield StepEvent(type="error", text="Supervisor-Agent bulunamadi.")
        return

    # 1. Supervisor routing
    yield StepEvent(type="routing", agent="Supervisor-Agent", text="Yonlendirme yapiliyor...")

    supervisor_prompt = (
        f"Kullanici mesaji: {user_message}\n\n"
        "SELECTED_AGENTS formatinda hangi agentlarin calisacagini belirt."
    )
    supervisor_resp = await _run_agent("Supervisor-Agent", supervisor_prompt, index=index)
    selected = _parse_selected_agents(supervisor_resp, index)

    yield StepEvent(type="routing", agent="Supervisor-Agent",
                    text=supervisor_resp, selected=selected)

    # 2. Secilen agentlari calistir
    agent_results: dict[str, str] = {}

    async def run_one(name: str):
        yield StepEvent(type="agent_start", agent=name)
        context_prompt = (
            f"Kullanici mesaji: {user_message}\n\n"
            f"Supervisor yonlendirmesi: {supervisor_resp}\n\n"
            "KRITIK KURAL: Elinde 'MEVCUT VERI' varsa yalnizca onu kullan. "
            "Yoksa 'Bu bilgiye sahip degilim, ilgili veriyi paylasmaniz gerekiyor.' de. "
            "Asla uydurma veya ornek veri olusturma.\n\n"
            f"Sen {name} olarak gorevini yap."
        )
        result = await _run_agent(name, context_prompt, user_message, index)
        agent_results[name] = result
        yield StepEvent(type="agent_done", agent=name, text=result)

    for name in selected:
        async for ev in run_one(name):
            yield ev

    # 3. Synthesis
    yield StepEvent(type="synthesis", agent="Synthesis-Agent", text="Sonuclar birlestiriliyor...")

    synthesis_parts = "\n\n".join(
        f"[{name}]: {result}" for name, result in agent_results.items()
    )
    synthesis_prompt = (
        f"Kullanici sorusu: {user_message}\n\n"
        f"Uzman agent cevaplari:\n{synthesis_parts}\n\n"
        "Bu cevaplari birlestirerek kullaniciya tek, net ve kisa bir final cevap ver. "
        "Agent isimlerinden bahsetme, sadece cevabi ver."
    )
    final = await _run_agent("Synthesis-Agent", synthesis_prompt, index=index)

    yield StepEvent(type="done", text=final)
