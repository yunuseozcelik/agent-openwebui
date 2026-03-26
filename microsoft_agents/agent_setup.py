"""
Microsoft Agent Framework ile multi-agent supervisor sistemi.
HandoffBuilder kullanarak triage -> specialist agent yonlendirmesi yapar.
"""

import os
from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient
from agent_framework.orchestrations import HandoffBuilder

from config import OPENAI_API_KEY, OPENAI_MODEL
from ifs_tools import HR_TOOLS, IT_TOOLS, FINANCE_TOOLS, GENERAL_TOOLS


def create_client() -> OpenAIChatClient:
    """OpenAI chat client olusturur."""
    return OpenAIChatClient(
        model_id=OPENAI_MODEL,
        api_key=OPENAI_API_KEY,
    )


def create_agents(client: OpenAIChatClient) -> dict:
    """Tum agent'lari olusturur ve doner."""

    triage_agent = Agent(
        client=client,
        name="triage_agent",
        instructions=(
            "Sen akilli bir yonlendiricisin. Kullanici mesajini analiz et ve uygun departman agent'ina yonlendir.\n\n"
            "Yonlendirme kurallari:\n"
            "- hr_agent: Izin talebi, izin bakiyesi, maas, personel bilgileri, bordro\n"
            "- it_agent: Bilgisayar arizasi, donanim talebi, teknik destek, ekipman, ticket\n"
            "- finance_agent: Avans talebi, harcama raporu, odeme durumu\n"
            "- general_agent: Yemek menusu, parca sorgulama, genel bilgi\n\n"
            "Eger mesaj genel sohbet (selamlasma, tesekkur vb.) ise kendin cevap ver.\n"
            "Turkce ve samimi bir dil kullan."
        ),
    )

    hr_agent = Agent(
        client=client,
        name="hr_agent",
        instructions=(
            "Sen uzman bir Insan Kaynaklari (HR) Asistanisin.\n"
            "Gorevin: Izin, maas, personel bilgileri ve onay sureclerini yonetmek.\n"
            "Tool sonuclarini Turkce olarak kullaniciya aktar.\n"
            "Islem yapmadan once kullanicidan onay iste."
        ),
        tools=HR_TOOLS,
    )

    it_agent = Agent(
        client=client,
        name="it_agent",
        instructions=(
            "Sen uzman bir IT Destek Asistanisin.\n"
            "Gorevin: Teknik arizalar, donanim talepleri ve destek ticket'lari yonetmek.\n"
            "Tool sonuclarini Turkce olarak kullaniciya aktar.\n"
            "Ticket olusturmadan once kullanicidan onay al."
        ),
        tools=IT_TOOLS,
    )

    finance_agent = Agent(
        client=client,
        name="finance_agent",
        instructions=(
            "Sen uzman bir Finans Asistanisin.\n"
            "Gorevin: Avans talepleri, harcama raporlari ve odeme durumlari hakkinda yardim etmek.\n"
            "Tool sonuclarini Turkce olarak kullaniciya aktar."
        ),
        tools=FINANCE_TOOLS,
    )

    general_agent = Agent(
        client=client,
        name="general_agent",
        instructions=(
            "Sen genel bir kurumsal asistansin.\n"
            "Gorevin: Yemek menusu, parca sorgulama ve genel ofis bilgileri hakkinda yardim etmek.\n"
            "Tool sonuclarini Turkce olarak kullaniciya aktar."
        ),
        tools=GENERAL_TOOLS,
    )

    return {
        "triage": triage_agent,
        "hr": hr_agent,
        "it": it_agent,
        "finance": finance_agent,
        "general": general_agent,
    }


def build_handoff_workflow():
    """HandoffBuilder ile multi-agent workflow olusturur."""
    client = create_client()
    agents = create_agents(client)

    workflow = (
        HandoffBuilder(
            name="ifs_corporate_assistant",
            participants=[
                agents["triage"],
                agents["hr"],
                agents["it"],
                agents["finance"],
                agents["general"],
            ],
        )
        .with_start_agent(agents["triage"])
        .build()
    )

    return workflow
