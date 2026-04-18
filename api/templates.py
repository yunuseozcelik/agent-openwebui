"""Prebuilt agent templates — tek tiklamayla deploy icin."""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class AgentTemplate:
    id: str
    name: str
    emoji: str
    category: str
    description: str
    purpose: str
    audience: str
    tone: str
    output_format: str
    scope: str
    pii: str
    approval: str
    tools: list[str]
    data_sources: list[str]
    capabilities: list[str]
    example_scenario: str

    def to_dict(self) -> dict:
        return asdict(self)


TEMPLATES: list[AgentTemplate] = [
    AgentTemplate(
        id="excel_error_analyzer",
        name="Excel Hata Analisti",
        emoji="📊",
        category="Veri Analizi",
        description="Excel dosyalarindaki hata kodlarini ve anomalileri tespit eder, trend raporu cikartir.",
        purpose="Kullanicinin yukledigi Excel dosyalarini analiz eder, en sik tekrarlanan hata kodlarini bulur ve haftalik trend raporu olusturur.",
        audience="Operasyon ve kalite ekipleri",
        tone="technical",
        output_format="structured",
        scope="report_only",
        pii="false",
        approval="false",
        tools=["file_reader", "code_interpreter"],
        data_sources=["Excel dosyalari", "CSV raporlari"],
        capabilities=[
            "Excel/CSV dosyalarini okuma",
            "Hata kodlarini siniflandirma",
            "Trend ve anomali tespit",
            "Istatistiksel ozet cikartma",
            "Grafik uretimi",
        ],
        example_scenario="Kullanici haftalik hata raporunu yukler, agent en sik 10 hata kodunu, trend grafigi ve onerilen aksiyonlari sunar.",
    ),
    AgentTemplate(
        id="customer_support_triage",
        name="Musteri Destek Triaj",
        emoji="🎯",
        category="Musteri Hizmetleri",
        description="Gelen musteri destek taleplerini kategorize eder ve oncelik sirasi belirler.",
        purpose="Musteri destek taleplerini okur, icerige gore kategorize eder, aciliyet seviyesini belirler ve uygun ekibe yonlendirir.",
        audience="Musteri hizmetleri ekibi",
        tone="friendly",
        output_format="structured",
        scope="strict_scope",
        pii="true",
        approval="true",
        tools=["api_call", "db_query"],
        data_sources=["Ticket sistemi", "Musteri CRM"],
        capabilities=[
            "Ticket metinlerini anlama",
            "Kategori ve oncelik atama",
            "Duygu analizi",
            "Ekip yonlendirmesi",
            "Benzer ticket bulma",
        ],
        example_scenario="Yeni bir ticket geldiginde agent otomatik olarak kategoriyi, aciliyeti ve ilgili ekibi belirler, duplicate ise bildirir.",
    ),
    AgentTemplate(
        id="hr_leave_assistant",
        name="IK Izin Asistani",
        emoji="🏖️",
        category="Insan Kaynaklari",
        description="Calisanlarin izin taleplerini kontrol eder, politika uygunlugunu dogrular.",
        purpose="Calisan izin taleplerini alir, yillik izin hakkini ve kalan izinleri veritabanindan sorgular, politika uyumlulugunu kontrol eder ve karar oneri sunar.",
        audience="Insan kaynaklari ekibi",
        tone="formal",
        output_format="summary",
        scope="no_pii_sharing",
        pii="true",
        approval="true",
        tools=["db_query", "api_call"],
        data_sources=["HR veritabani", "Izin politika dokumani"],
        capabilities=[
            "Izin hakki sorgulama",
            "Politika kontrolu",
            "Cakisan izin tespit",
            "Onay/red oneri",
            "Otomatik bildirim",
        ],
        example_scenario="Calisan izin talebi girer, agent izin hakkini kontrol eder, cakisma olup olmadigini bakar, karar onerisi sunar.",
    ),
    AgentTemplate(
        id="finance_expense_auditor",
        name="Harcama Denetleyicisi",
        emoji="💰",
        category="Finans",
        description="Gider raporlarini inceler, politika ihlallerini ve anomalileri tespit eder.",
        purpose="Yuklenen gider raporlarini okur, sirket harcama politikasina uygunlugunu kontrol eder, supheli veya yuksek tutarli islemleri isaretler.",
        audience="Finans ve muhasebe ekibi",
        tone="formal",
        output_format="report",
        scope="no_financial_advice",
        pii="true",
        approval="true",
        tools=["file_reader", "code_interpreter", "db_query"],
        data_sources=["PDF faturalar", "Excel gider raporlari", "Harcama politikasi"],
        capabilities=[
            "Fatura OCR ve parse",
            "Politika ihlal tespiti",
            "Anomali ve outlier analizi",
            "Kategori otomatiklesmesi",
            "Gider ozet raporu",
        ],
        example_scenario="Calisan aylik gider raporunu yukler, agent sirket politikasina uymayan veya anormal tutarlari isaretler, ozet rapor sunar.",
    ),
    AgentTemplate(
        id="doc_qa_rag",
        name="Dokuman Soru-Cevap",
        emoji="📚",
        category="Bilgi Yonetimi",
        description="Sirket dokumanlari uzerinde soru-cevap yapan RAG agent'i.",
        purpose="Yuklenen dokuman koleksiyonu uzerinde arama yapar, kullanici sorularina kaynak referansiyla cevap verir.",
        audience="Tum sirket",
        tone="friendly",
        output_format="adaptive",
        scope="strict_scope",
        pii="false",
        approval="false",
        tools=["file_search", "file_reader"],
        data_sources=["PDF dokumanlari", "Word dosyalari", "Wiki"],
        capabilities=[
            "Dokuman ici semantik arama",
            "Kaynak referansli cevap",
            "Ozet cikartma",
            "Coklu dokuman korelasyonu",
            "Sorgu netlestirme",
        ],
        example_scenario="Kullanici 'yeni izin politikasi nedir?' diye sorar, agent ilgili dokumandan kaynakla birlikte cevap verir.",
    ),
    AgentTemplate(
        id="sales_churn_predictor",
        name="Churn Risk Analizi",
        emoji="📉",
        category="Satis",
        description="CRM verilerinden musteri churn riskini hesaplar, risk grupları onerir.",
        purpose="CRM'den musteri davranisi, aktivite ve etkilesim verilerini ceker, makine ogrenmesi ve kural tabanli yaklasimla churn riskini hesaplar.",
        audience="Satis ve musteri basari ekibi",
        tone="technical",
        output_format="structured",
        scope="no_pii_sharing",
        pii="true",
        approval="false",
        tools=["api_call", "db_query", "code_interpreter"],
        data_sources=["CRM sistemi", "Aktivite loglari", "Satis veritabani"],
        capabilities=[
            "Musteri davranis analizi",
            "Risk skoru hesaplama",
            "Segmentasyon",
            "Alert ve oneri",
            "Trend takibi",
        ],
        example_scenario="Haftalik churn raporu — yuksek riskli musteri listesi, risk nedeni ve onerilen aksiyonlar.",
    ),
    AgentTemplate(
        id="it_incident_responder",
        name="IT Incident Assistant",
        emoji="🛠️",
        category="IT",
        description="IT olaylarini ve hata kayitlarini analiz eder, benzer gecmis cozumleri onerir.",
        purpose="Yeni gelen IT incident'larin log ve aciklamalarini analiz eder, gecmis benzer olaylarla karsilastirir, hizli cozum onerileri uretir.",
        audience="IT ve teknik destek",
        tone="technical",
        output_format="step_by_step",
        scope="strict_scope",
        pii="false",
        approval="false",
        tools=["file_search", "api_call", "db_query"],
        data_sources=["Incident db", "Runbook wiki", "Log sistemi"],
        capabilities=[
            "Log analizi",
            "Benzer incident bulma",
            "Root cause onerileri",
            "Runbook linkleme",
            "Escalation onerisi",
        ],
        example_scenario="Yeni incident aciliyinca agent ilgili runbook'u bulur, gecmis benzer cozumleri listeler, ilk adimlari onerir.",
    ),
]


def list_templates() -> list[dict]:
    return [t.to_dict() for t in TEMPLATES]


def get_template(template_id: str) -> AgentTemplate | None:
    return next((t for t in TEMPLATES if t.id == template_id), None)
