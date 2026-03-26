from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

try:
    from .ifs_tools import FINANCE_TOOLS, GENERAL_TOOLS, HR_TOOLS, IT_TOOLS, MATH_TOOLS
except ImportError:
    from ifs_tools import FINANCE_TOOLS, GENERAL_TOOLS, HR_TOOLS, IT_TOOLS, MATH_TOOLS


AgentName = Literal["HR_Agent", "IT_Agent", "Finance_Agent", "Math_Agent", "General_Agent"]


@dataclass(frozen=True)
class DomainSpec:
    agent: AgentName
    label: str
    description: str
    planner_hints: tuple[str, ...]
    tools: tuple[Any, ...]
    execution_guidance: str
    dependencies: tuple[AgentName, ...] = ()
    requires_user_email: bool = False


DOMAIN_REGISTRY: dict[AgentName, DomainSpec] = {
    "HR_Agent": DomainSpec(
        agent="HR_Agent",
        label="IK Asistani",
        description="Izin, maas, bordro, personel bilgileri ve onay surecleri",
        planner_hints=(
            "izin talebi",
            "izin bakiyesi",
            "bordro",
            "maas bilgisi",
            "personel bilgileri",
            "onaylar",
        ),
        tools=tuple(HR_TOOLS),
        execution_guidance=(
            "Kullaniciya ait bilgi gerekiyorsa user_email bilgisini kullan. "
            "Resmi bir talep olusturmadan once kisa bir ozet gec ve onay iste. "
            "Mock modda e-posta yoksa demo kullanici varsay ve islemi sonuclandir."
        ),
        requires_user_email=True,
    ),
    "IT_Agent": DomainSpec(
        agent="IT_Agent",
        label="IT Destek",
        description="Teknik destek, ariza kaydi, ekipman talebi ve parca sorgusu",
        planner_hints=(
            "bilgisayar arizasi",
            "ekipman talebi",
            "ticket",
            "teknik destek",
            "parca sorgusu",
        ),
        tools=tuple(IT_TOOLS),
        execution_guidance=(
            "Sorunu netlestir. Ticket veya ekipman talebi olusturmadan once son onay iste. "
            "Mock modda eksik veride makul varsayimla kaydi olustur."
        ),
    ),
    "Finance_Agent": DomainSpec(
        agent="Finance_Agent",
        label="Finans Asistani",
        description="Avans, harcama raporu, odeme durumu ve finans onaylari",
        planner_hints=(
            "avans talebi",
            "harcama raporu",
            "odeme durumu",
            "masraf",
            "finans onayi",
        ),
        tools=tuple(FINANCE_TOOLS),
        execution_guidance=(
            "Parasal konularda dikkatli ol. Islem yapmadan once miktari ve nedeni netlestir, sonra onay iste. "
            "Mock modda talebi simule ederek tamamla ve pasif red cevabi verme."
        ),
        dependencies=("HR_Agent",),
    ),
    "Math_Agent": DomainSpec(
        agent="Math_Agent",
        label="Matematik Uzmani",
        description="Matematik, bilim, donusum ve sayisal analizler",
        planner_hints=(
            "matematik",
            "bilimsel hesaplama",
            "birim donusumu",
            "istatistik",
            "kur cevirisi",
        ),
        tools=tuple(MATH_TOOLS),
        execution_guidance=(
            "Matematiksel veya bilimsel istekte calculate_wolfram aracini kullan, sonucu Turkce acikla."
        ),
    ),
    "General_Agent": DomainSpec(
        agent="General_Agent",
        label="Genel Asistan",
        description="Yemek menusu, servis saatleri ve genel ofis bilgileri",
        planner_hints=(
            "yemek menusu",
            "servis saatleri",
            "ofis bilgisi",
            "genel bilgi",
        ),
        tools=tuple(GENERAL_TOOLS),
        execution_guidance=(
            "Yemek ve servis bilgilerini duzenli, okunabilir ve net formatta sun. "
            "Mock modda eksik bilgi nedeniyle reddetme yapma."
        ),
    ),
}


DOMAIN_ORDER: tuple[AgentName, ...] = tuple(DOMAIN_REGISTRY.keys())
AGENT_LABELS = {name: spec.label for name, spec in DOMAIN_REGISTRY.items()}
