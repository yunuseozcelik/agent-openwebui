"""Local multi-agent orchestrator.

Akis:
  User message
    → Supervisor-Agent  (routing: SELECTED_AGENTS: ...)
    → Secilen agent'lar (paralel veya sirayla)
    → Synthesis-Agent   (final cevap)
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import AsyncIterator

from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient

from agent_factory.config import OPENAI_API_KEY, OPENAI_MODEL
from agent_factory.deployment.seed_agents import SEED_AGENT_DEFINITIONS
from agent_factory.mock_data.context_loader import get_mock_context
from utils.portkey import get_maf_client_options


# Seed agent instruction'larini isim -> dict olarak indeksle
_SEED_INDEX: dict[str, dict] = {
    d["name"]: d for d in SEED_AGENT_DEFINITIONS
}

# Chat-Agent ve General-Agent icin konusmaya izin ver
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


def _make_agent(name: str, user_message: str = "") -> Agent | None:
    defn = _SEED_INDEX.get(name)
    if not defn:
        return None

    # Kullanici mesajina ve agent adina gore mock veri context'i ekle
    mock_ctx = get_mock_context(name, name) or get_mock_context(user_message, "")

    instructions = (
        "## DAVRANIS KURALLARI\n"
        "- Cevaplar kisa ve net olsun.\n"
        "- Asla veri uydurma; asagida 'MEVCUT VERİ' varsa yalnizca onu kullan.\n"
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


def _parse_selected_agents(supervisor_text: str) -> list[str]:
    """SELECTED_AGENTS: HR-Agent, IT-Agent satırından agent isimlerini çıkar."""
    match = re.search(r"SELECTED_AGENTS:\s*(.+)", supervisor_text, re.IGNORECASE)
    if not match:
        return ["General-Agent"]
    raw = match.group(1).strip()
    # Satır sonu veya nokta ile bitiyorsa temizle
    raw = re.split(r"[\.\n]", raw)[0]
    names = [n.strip() for n in raw.split(",")]
    # Geçerli seed agent isimlerini filtrele
    valid = [n for n in names if n in _SEED_INDEX]
    return valid or ["General-Agent"]


async def _run_agent(name: str, prompt: str, user_message: str = "") -> str:
    agent = _make_agent(name, user_message)
    if not agent:
        return f"{name}: agent tanimli degil."
    resp = await agent.run(prompt)
    return getattr(resp, "text", "") or str(getattr(resp, "value", ""))


async def orchestrate(user_message: str) -> AsyncIterator[StepEvent]:
    """Tam orchestration akisini SSE event olarak yayinlar."""

    # 1. Supervisor routing
    supervisor = _make_agent("Supervisor-Agent")
    if not supervisor:
        yield StepEvent(type="error", text="Supervisor-Agent bulunamadi.")
        return

    yield StepEvent(type="routing", agent="Supervisor-Agent", text="Yönlendirme yapılıyor...")

    supervisor_prompt = (
        f"Kullanici mesaji: {user_message}\n\n"
        f"SELECTED_AGENTS formatinda hangi agent'larin calisacagini belirt."
    )
    supervisor_resp = await _run_agent("Supervisor-Agent", supervisor_prompt)
    selected = _parse_selected_agents(supervisor_resp)

    yield StepEvent(type="routing", agent="Supervisor-Agent",
                    text=supervisor_resp, selected=selected)

    # 2. Secilen agent'lari calistir
    agent_results: dict[str, str] = {}

    async def run_one(name: str):
        yield StepEvent(type="agent_start", agent=name)
        context_prompt = (
            f"Kullanici mesaji: {user_message}\n\n"
            f"Supervisor yonlendirmesi: {supervisor_resp}\n\n"
            f"KRITIK KURAL: Elinde 'MEVCUT VERİ' varsa yalnizca onu kullan. "
            f"Yoksa 'Bu bilgiye sahip degilim, ilgili veriyi paylasmaniz gerekiyor.' de. "
            f"Asla uydurma veya ornek veri olusturma.\n\n"
            f"Sen {name} olarak gorevini yap."
        )
        result = await _run_agent(name, context_prompt, user_message)
        agent_results[name] = result
        yield StepEvent(type="agent_done", agent=name, text=result)

    # Agent'lari sirayla calistir (Supervisor siralamaya karar vermis olabilir)
    for name in selected:
        async for ev in run_one(name):
            yield ev

    # 3. Synthesis
    yield StepEvent(type="synthesis", agent="Synthesis-Agent", text="Sonuçlar birleştiriliyor...")

    synthesis_parts = "\n\n".join(
        f"[{name}]: {result}" for name, result in agent_results.items()
    )
    synthesis_prompt = (
        f"Kullanici sorusu: {user_message}\n\n"
        f"Uzman agent cevaplari:\n{synthesis_parts}\n\n"
        f"Bu cevaplari birlestirerek kullaniciya tek, net ve kisa bir final cevap ver. "
        f"Agent isimlerinden bahsetme, sadece cevabi ver."
    )
    final = await _run_agent("Synthesis-Agent", synthesis_prompt)

    yield StepEvent(type="done", text=final)
