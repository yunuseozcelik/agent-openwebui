"""Factory functions for the Microsoft Agent Framework specialists."""

from __future__ import annotations

from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient
from agent_framework.orchestrations import HandoffBuilder
from utils.portkey import get_maf_client_options
from utils.shared_prompts import (
    CHAT_INSTRUCTIONS,
    FINANCE_INSTRUCTIONS,
    GENERAL_INSTRUCTIONS,
    HR_INSTRUCTIONS,
    IT_INSTRUCTIONS,
    MATH_INSTRUCTIONS,
    SPECIALIST_INSTRUCTIONS,
)

try:
    from .config import OPENAI_API_KEY, OPENAI_PLANNER_MODEL, OPENAI_WORKER_MODEL
    from .domains import AGENT_LABELS, DOMAIN_ORDER, DOMAIN_REGISTRY, AgentName
except ImportError:
    from config import OPENAI_API_KEY, OPENAI_PLANNER_MODEL, OPENAI_WORKER_MODEL
    from domains import AGENT_LABELS, DOMAIN_ORDER, DOMAIN_REGISTRY, AgentName

PLANNER_INSTRUCTIONS = (
    "Sen bir is planlayicisisin. Kullanicinin mesajini analiz et ve hangi departmanlarin "
    "hangi sirayla calisacagini belirle.\n\n"
    "DEPARTMANLAR:\n"
    "- HR_Agent: Izin, maas, personel islemleri\n"
    "- IT_Agent: Teknik destek, donanim talepleri, parca sorgulama\n"
    "- Finance_Agent: Avans, harcama, odeme islemleri\n"
    "- Math_Agent: Matematik, bilim, hesaplama\n"
    "- General_Agent: Yemek menusu, servis saatleri\n\n"
    "KURALLAR:\n"
    "- Sadece gerekli agent'lari sec, gereksiz adim ekleme\n"
    "- Bagimlilik varsa dogru sirayla koy (ornegin: izin -> avans)\n"
    "- Selamlasma, sohbet gibi basit mesajlarda steps listesini BOS birak []\n"
    "- Her adim icin kullaniciya gosterilecek kisa bir aciklama yaz (Turkce)\n\n"
    "ORNEKLER:\n"
    "- 'merhaba' -> steps: []\n"
    "- 'izin almak istiyorum' -> steps: [{agent: HR_Agent, description: 'Izin talebi olusturuluyor'}]\n"
    "- 'izin al ve avans iste' -> steps: [{agent: HR_Agent, description: 'Izin talebi isleniyor'}, {agent: Finance_Agent, description: 'Avans talebi olusturuluyor'}]\n"
    "Cevabi yalnizca gecerli JSON olarak don."
)

SYNTHESIS_INSTRUCTIONS = (
    "Sen IFS Kurumsal Asistaninin final cevap ureten katmanisin.\n"
    "Birden fazla uzman ciktisini tek, akici ve kullanici dostu bir cevapta birlestir.\n"
    "Gereksiz tekrar etme. Aksiyon, durum ve sonraki adimlari netlestir.\n"
    "Cevabi Turkce ver."
)

TRIAGE_INSTRUCTIONS = (
    "Sen bir akilli yonlendiricisin. Kullanici mesajini oku ve sadece SPESIFIK IS TALEPLERI icin uzmana yonlendir.\n\n"
    "HR_Agent:\n"
    "- Izin talebi, maas bordrosu, personel bilgileri, personel onaylari\n\n"
    "IT_Agent:\n"
    "- Bilgisayar arizasi, donanim talebi, teknik destek, parca sorgulama\n\n"
    "Finance_Agent:\n"
    "- Avans talebi, harcama raporu, odeme durumu\n\n"
    "Math_Agent:\n"
    "- Matematik, bilimsel veri, para birimi cevirme, tarih hesaplari, genel istatistikler\n\n"
    "General_Agent:\n"
    "- Yemek menusu, servis saatleri, genel ofis bilgileri\n\n"
    "FINISH / Genel sohbet:\n"
    "- Selamlasma, yardim, genel sohbet, belirsiz talepler\n\n"
    "KURAL: Acik bir is veya hesaplama talebi yoksa FINISH.\n"
    "KURAL: Soru matematiksel, bilimsel veya guncel sayisal veri iceriyorsa Math_Agent.\n"
    "KURAL: Yemek veya servis sorulursa General_Agent."
)


def create_client(model_id: str, *, component: str) -> OpenAIChatClient:
    return OpenAIChatClient(
        **get_maf_client_options(
            model_id=model_id,
            primary_api_key=OPENAI_API_KEY,
            engine="maf",
            component=component,
        )
    )


def create_planner_client() -> OpenAIChatClient:
    return create_client(OPENAI_PLANNER_MODEL, component="planner")


def create_worker_client() -> OpenAIChatClient:
    return create_client(OPENAI_WORKER_MODEL, component="worker")


def create_chat_client() -> OpenAIChatClient:
    return create_client(OPENAI_WORKER_MODEL, component="chat")


def create_synthesis_client() -> OpenAIChatClient:
    return create_client(OPENAI_WORKER_MODEL, component="synthesis")


def create_specialist_client() -> OpenAIChatClient:
    return create_client(OPENAI_WORKER_MODEL, component="specialist")


def create_planner_agent(client: OpenAIChatClient) -> Agent:
    return Agent(client=client, name="planner_agent", instructions=PLANNER_INSTRUCTIONS)


def create_chat_agent(client: OpenAIChatClient) -> Agent:
    return Agent(client=client, name="chat_agent", instructions=CHAT_INSTRUCTIONS)


def create_synthesis_agent(client: OpenAIChatClient) -> Agent:
    return Agent(client=client, name="synthesis_agent", instructions=SYNTHESIS_INSTRUCTIONS)


def create_specialist_agents(client: OpenAIChatClient) -> dict[AgentName, Agent]:
    agents: dict[AgentName, Agent] = {}
    for name, spec in DOMAIN_REGISTRY.items():
        agents[name] = Agent(
            client=client,
            name=name,
            instructions=SPECIALIST_INSTRUCTIONS[name],
            tools=list(spec.tools),
        )
    return agents


def build_handoff_workflow():
    """Compatibility workflow for direct MAF experiments."""
    worker_client = create_worker_client()
    specialists = create_specialist_agents(worker_client)
    triage_agent = Agent(client=worker_client, name="triage_agent", instructions=TRIAGE_INSTRUCTIONS)

    return (
        HandoffBuilder(
            name="ifs_corporate_assistant",
            participants=[triage_agent, *[specialists[name] for name in DOMAIN_ORDER]],
        )
        .with_start_agent(triage_agent)
        .build()
    )
