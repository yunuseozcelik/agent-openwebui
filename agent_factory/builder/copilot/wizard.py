"""Wizard step definitions for the Agent Builder.

Her adim bir soru, secenekler ve varsayilan deger icerir.
Chainlit UI bu adimlari sirayla gosterir.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WizardChoice:
    label: str
    value: str
    description: str = ""


@dataclass
class WizardStep:
    id: str
    title: str
    description: str
    choices: list[WizardChoice] = field(default_factory=list)
    allow_custom: bool = False  # Serbest metin de girebilir mi
    required: bool = True


# Wizard adimlari
WIZARD_STEPS: list[WizardStep] = [
    WizardStep(
        id="audience",
        title="Kimler kullanacak?",
        description="Bu agent'i hangi ekip veya departman kullanacak?",
        choices=[
            WizardChoice("Musteri Hizmetleri", "musteri_hizmetleri", "Cagri merkezi, destek ekibi"),
            WizardChoice("Yonetim", "yonetim", "Ust duzey yoneticiler, karar vericiler"),
            WizardChoice("IT Ekibi", "it", "Yazilim, altyapi, teknik destek"),
            WizardChoice("Finans", "finans", "Muhasebe, butce, mali isler"),
            WizardChoice("Operasyon", "operasyon", "Uretim, lojistik, saha ekipleri"),
            WizardChoice("Insan Kaynaklari", "ik", "IK, personel islemleri"),
            WizardChoice("Tum Sirket", "tum_sirket", "Herkese acik"),
        ],
        allow_custom=True,
    ),
    WizardStep(
        id="pii",
        title="Hassas veri iceriyor mu?",
        description="Bu agent kisisel verilere (isim, TC, e-posta, telefon, adres vb.) erisecek mi?",
        choices=[
            WizardChoice("Evet, hassas veri var", "true", "Musteri/calisan kisisel bilgileri isleniyor"),
            WizardChoice("Hayir", "false", "Kisisel veri yok veya anonimlestirilmis"),
            WizardChoice("Emin degilim", "maybe", "Sistem otomatik belirlesin"),
        ],
    ),
    WizardStep(
        id="approval",
        title="Insan onayi gerekli mi?",
        description="Agent'in urettigi sonuclar icin bir kisinin onay vermesi gerekiyor mu?",
        choices=[
            WizardChoice("Evet, onay gerekli", "true", "Sonuclar aksiyona donusmeden once onaylanmali"),
            WizardChoice("Hayir, sadece bilgi/rapor", "false", "Sadece raporlama, aksiyon yok"),
            WizardChoice("Bazen gerekebilir", "conditional", "Bazi durumlarda onay gerekli"),
        ],
    ),
]


@dataclass
class WizardState:
    """Wizard'in o anki durumu."""
    current_step: int = 0  # -1 = initial desc bekleniyor, 0+ = adim indeksi
    description: str = ""  # Kullanicinin ilk tanimi
    answers: dict = field(default_factory=dict)  # step_id -> answer value
    agent_name: str = ""  # LLM'in urettigi isim
    agent_purpose: str = ""  # LLM'in urettigi amac
    completed: bool = False

    @property
    def is_collecting_description(self) -> bool:
        return self.current_step == -1

    @property
    def is_in_steps(self) -> bool:
        return 0 <= self.current_step < len(WIZARD_STEPS)

    @property
    def current_wizard_step(self) -> WizardStep | None:
        if self.is_in_steps:
            return WIZARD_STEPS[self.current_step]
        return None

    @property
    def is_ready_for_summary(self) -> bool:
        return self.current_step >= len(WIZARD_STEPS) and not self.completed

    def advance(self):
        self.current_step += 1

    def set_answer(self, step_id: str, value: str):
        self.answers[step_id] = value
