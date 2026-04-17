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
    allow_custom: bool = False
    required: bool = True


WIZARD_STEPS: list[WizardStep] = [
    # 1. Hedef kitle
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

    # 2. Iletisim tonu
    WizardStep(
        id="tone",
        title="Agent nasil konussun?",
        description="Agent'in iletisim tarzini secin.",
        choices=[
            WizardChoice("Resmi / Kurumsal", "formal", "Profesyonel dil, kisa ve net cevaplar"),
            WizardChoice("Samimi / Yardimci", "friendly", "Sicak, anlasılır, rehberlik eden"),
            WizardChoice("Teknik / Detayli", "technical", "Uzman seviyesi, detayli aciklamalar"),
            WizardChoice("Kisa / Ozet Odakli", "concise", "Minimum kelime, maksimum bilgi"),
        ],
    ),

    # 3. Cikti formati
    WizardStep(
        id="output_format",
        title="Ciktilari nasil versin?",
        description="Agent'in cevaplarini hangi formatta sunmasini istiyorsunuz?",
        choices=[
            WizardChoice("Tablo / Yapilandirilmis", "structured", "Tablolar, listeler, maddeler halinde"),
            WizardChoice("Rapor / Detayli Metin", "report", "Uzun, aciklayici paragraflar"),
            WizardChoice("Kisa Ozet", "summary", "2-3 cumlelik ozetler"),
            WizardChoice("Adim Adim Rehber", "step_by_step", "Numaralandirilmis adimlar halinde"),
            WizardChoice("Karisik / Duruma Gore", "adaptive", "Soruya gore uygun format"),
        ],
    ),

    # 4. Hassas veri
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

    # 5. Insan onayi
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

    # 6. Kapsam siniri
    WizardStep(
        id="scope",
        title="Agent ne YAPMAMALI?",
        description="Agent'in kesinlikle yapmaması gereken seyler neler? (Kapsam disi davranislar)",
        choices=[
            WizardChoice("Finansal tavsiye vermemeli", "no_financial_advice", "Yatirim, kredi, mali karar onerisi yasak"),
            WizardChoice("Kisisel bilgi paylasmamalı", "no_pii_sharing", "Kisisel veri disari cikmamali"),
            WizardChoice("Aksiyon almamali, sadece raporlamali", "report_only", "Hicbir sisteme yazma/degistirme yapmasin"),
            WizardChoice("Kapsam disi sorulara cevap vermemeli", "strict_scope", "Sadece gorevi dahilinde calissin"),
            WizardChoice("Ozel bir kisitlama yok", "no_restriction", "Genel kurallar yeterli"),
        ],
        allow_custom=True,
    ),

    # 7. Ornek senaryo
    WizardStep(
        id="example_scenario",
        title="Ornek bir kullanim senaryosu",
        description=(
            "Agent'in tipik bir kullanim senaryosunu yazin. "
            "Ornegin: 'Kullanici Excel yukler, agent hata kodlarini bulur ve rapor cikartir.'"
        ),
        choices=[
            WizardChoice("Simdilik gecmek istiyorum", "skip", "Ornek senaryo vermeden devam et"),
        ],
        allow_custom=True,
    ),
]


@dataclass
class WizardState:
    """Wizard'in o anki durumu."""
    current_step: int = 0  # -1 = initial desc bekleniyor, 0+ = adim indeksi
    description: str = ""
    answers: dict = field(default_factory=dict)
    agent_name: str = ""
    agent_purpose: str = ""
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
