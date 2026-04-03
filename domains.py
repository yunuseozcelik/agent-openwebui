"""Domain registry limited to real IFS-backed capability areas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from ifs_tools import GENERAL_TOOLS, HR_TOOLS, IT_TOOLS
from mock_test_tools import TEST_TOOLS


AgentName = Literal["HR_Agent", "IT_Agent", "General_Agent", "Test_Agent"]


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
        description="Personel detaylari, izin ozeti ve kullanici bilgileri",
        planner_hints=(
            "izin bakiyesi",
            "yillik izin",
            "izin hakki",
            "kalan izin",
            "personel bilgileri",
            "sicil",
            "ecb",
            "mazeret izin",
        ),
        tools=tuple(HR_TOOLS),
        execution_guidance=(
            "Kullaniciya ait bilgi gerekiyorsa user_email bilgisini kullan. "
            "Bu entegrasyonda sadece kullanici ve izin ozet sorgulari desteklenir. "
            "Izin talebi, bordro veya onay sureci gibi desteklenmeyen islemleri yapabilecegini iddia etme."
        ),
        requires_user_email=True,
    ),
    "IT_Agent": DomainSpec(
        agent="IT_Agent",
        label="IT Destek",
        description="IFS parca detay sorgulari",
        planner_hints=(
            "parca no",
            "parca sorgusu",
            "parca detayi",
            "urun kodu",
            "eo",
            "teknik koordinator",
        ),
        tools=tuple(IT_TOOLS),
        execution_guidance=(
            "Bu entegrasyonda sadece parca detay sorgusu desteklenir. "
            "BT ticket, ariza kaydi veya ekipman talebi olusturabilecegini iddia etme."
        ),
    ),
    "General_Agent": DomainSpec(
        agent="General_Agent",
        label="Genel Asistan",
        description="Yemek listesi bilgileri",
        planner_hints=(
            "yemek menusu",
            "yemek listesi",
            "bugunun menusu",
            "yemek",
        ),
        tools=tuple(GENERAL_TOOLS),
        execution_guidance=(
            "Bu entegrasyonda yemek listesi desteklenir. "
            "Servis saati gibi IFS disi bilgiler icin destek veriyormus gibi davranma."
        ),
    ),
    "Test_Agent": DomainSpec(
        agent="Test_Agent",
        label="Mock Test",
        description="UI ve workflow davranisini test etmek icin sahte talep akisi",
        planner_hints=(
            "mock test",
            "test senaryosu",
            "workflow test",
            "ornek talep",
            "test akisi",
            "demo test",
        ),
        tools=tuple(TEST_TOOLS),
        execution_guidance=(
            "Bu agent sadece test amaclidir. "
            "Kullanicidan talep basligi, oncelik ve hedef tarih bilgilerini topla; "
            "tum zorunlu alanlar tamamlaninca ozet gec ve onay iste; "
            "onay geldikten sonra create_mock_test_request aracini cagir."
        ),
    ),
}


DOMAIN_ORDER: tuple[AgentName, ...] = tuple(DOMAIN_REGISTRY.keys())
AGENT_LABELS = {name: spec.label for name, spec in DOMAIN_REGISTRY.items()}
