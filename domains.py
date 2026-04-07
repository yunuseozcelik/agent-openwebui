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
        label="İK Asistanı",
        description="Personel detayları, izin özeti ve kullanıcı bilgileri",
        planner_hints=(
            "izin bakiyesi",
            "yıllık izin",
            "izin hakkı",
            "kalan izin",
            "personel bilgileri",
            "sicil",
            "ecb",
            "mazeret izin",
        ),
        tools=tuple(HR_TOOLS),
        execution_guidance=(
            "Kullanıcıya ait bilgi gerekiyorsa user_email bilgisini kullan. "
            "Bu entegrasyonda sadece kullanıcı ve izin özet sorguları desteklenir. "
            "Izin talebi, bordro veya onay süreci gibi desteklenmeyen işlemleri yapabileceğini iddia etme."
        ),
        requires_user_email=True,
    ),
    "IT_Agent": DomainSpec(
        agent="IT_Agent",
        label="IT Destek",
        description="IFS parça detay sorguları",
        planner_hints=(
            "parça no",
            "parça sorgusu",
            "parça detayı",
            "ürün kodu",
            "eo",
            "teknik koordinatör",
        ),
        tools=tuple(IT_TOOLS),
        execution_guidance=(
            "Bu entegrasyonda sadece parça detay sorgusu desteklenir. "
            "BT ticket, arıza kaydı veya ekipman talebi oluşturabileceğini iddia etme."
        ),
    ),
    "General_Agent": DomainSpec(
        agent="General_Agent",
        label="Genel Asistan",
        description="Yemek listesi bilgileri",
        planner_hints=(
            "yemek menüsü",
            "yemek listesi",
            "bugünün menüsü",
            "yemek",
        ),
        tools=tuple(GENERAL_TOOLS),
        execution_guidance=(
            "Bu entegrasyonda yemek listesi desteklenir. "
            "Servis saati gibi IFS dışı bilgiler için destek veriyormuş gibi davranma."
        ),
    ),
    "Test_Agent": DomainSpec(
        agent="Test_Agent",
        label="Mock Test",
        description="UI ve workflow davranışını test etmek için sahte talep akışı",
        planner_hints=(
            "mock test",
            "test senaryosu",
            "workflow test",
            "örnek talep",
            "test akışı",
            "demo test",
        ),
        tools=tuple(TEST_TOOLS),
        execution_guidance=(
            "Bu agent sadece test amaçlıdır. "
            "Kullanıcıdan talep başlığı, öncelik ve hedef tarih bilgilerini topla; "
            "tüm zorunlu alanlar tamamlanınca özet geç ve onay iste; "
            "onay geldikten sonra create_mock_test_request aracını çağır."
        ),
    ),
}


DOMAIN_ORDER: tuple[AgentName, ...] = tuple(DOMAIN_REGISTRY.keys())
AGENT_LABELS = {name: spec.label for name, spec in DOMAIN_REGISTRY.items()}
