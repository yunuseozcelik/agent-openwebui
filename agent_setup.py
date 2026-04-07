"""MAF agent fabrika fonksiyonları."""

from __future__ import annotations

from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient

from config import OPENAI_API_KEY, OPENAI_PLANNER_MODEL, OPENAI_WORKER_MODEL
from domains import DOMAIN_REGISTRY, AgentName
from shared_prompts import CHAT_INSTRUCTIONS, SPECIALIST_INSTRUCTIONS


PLANNER_INSTRUCTIONS = (
    "Sen bir iş planlayıcısısın. Kullanıcının mesajını analiz et ve hangi agent'ın çalışacağını belirle.\n\n"
    "DEPARTMANLAR:\n"
    "- HR_Agent: Personel bilgileri ve izin bakiyesi SORGUSU (talep oluşturma YOK)\n"
    "- IT_Agent: Parça detayı sorgusu\n"
    "- General_Agent: Yemek menüsü sorgusu\n"
    "- Test_Agent: Mock workflow test akışı\n\n"
    "KURALLAR:\n"
    "- Sadece gerekli agent'ı seç, gereksiz adım ekleme.\n"
    "- Aktif bir workflow varsa ve kullanıcının mesajı o akışın devamıysa (bilgi veriyor, onay veriyor, iptal ediyor) continue_current_workflow=true dön.\n"
    "- ÖNEMLİ: Kullanıcı 'evet', 'onaylıyorum', 'onayla', 'yap', 'tamam', 'oluştur' gibi onay ifadesi kullanıyorsa ve aktif workflow varsa MUTLAKA continue_current_workflow=true dön.\n"
    "- Kullanıcı yeni bir konu açtıysa continue_current_workflow=false dön.\n"
    "- Selamlaşma, sohbet gibi basit mesajlarda steps=[] dön.\n"
    "- Desteklenmeyen isteklerde (avans, izin talebi oluşturma, BT ticket vb.) steps=[] dön.\n\n"
    "ÖRNEKLER:\n"
    "- 'merhaba' -> {continue_current_workflow: false, steps: []}\n"
    "- 'yıllık izin hakkım ne kadar' -> {continue_current_workflow: false, steps: [{agent: HR_Agent, description: 'İzin bakiyesi sorgulanıyor'}]}\n"
    "- 'personel bilgilerim' -> {continue_current_workflow: false, steps: [{agent: HR_Agent, description: 'Personel bilgileri getiriliyor'}]}\n"
    "- 'ABC-001 parçasının detayı' -> {continue_current_workflow: false, steps: [{agent: IT_Agent, description: 'Parça detayı sorgulanıyor'}]}\n"
    "- 'bugünün yemek menüsü' -> {continue_current_workflow: false, steps: [{agent: General_Agent, description: 'Yemek menüsü getiriliyor'}]}\n"
    "- 'mock test başlat' -> {continue_current_workflow: false, steps: [{agent: Test_Agent, description: 'Mock test akışı başlatılıyor'}]}\n"
    "- 'başlık: Laptop kurulumu, öncelik: yüksek' + aktif Test_Agent workflow -> {continue_current_workflow: true, steps: [{agent: Test_Agent, description: 'Bilgiler tamamlanıyor'}]}\n"
    "- 'onaylıyorum' + aktif workflow -> {continue_current_workflow: true, steps: [{agent: aktif_agent, description: 'Onay işleniyor'}]}\n"
    "- 'evet yap' + aktif workflow -> {continue_current_workflow: true, steps: [{agent: aktif_agent, description: 'Talep oluşturuluyor'}]}\n"
    "- 'avans talebi aç' -> {continue_current_workflow: false, steps: []}\n"
    "- 'hastalık izni talebi aç' -> {continue_current_workflow: false, steps: []}\n"
    "Cevabı yalnızca geçerli JSON olarak dön."
)

SYNTHESIS_INSTRUCTIONS = (
    "Sen FNSS Kurumsal Asistanının final cevap katmanısın.\n"
    "Birden fazla uzman çıktısını tek, net ve kullanıcı dostu bir cevapta birleştir.\n"
    "Gereksiz tekrar etme. Sonucu ve varsa sonraki adımı netleştir.\n"
    "Cevabı Türkçe ver. Kısa ve öz ol.\n"
    "ÖNEMLİ: 'Onay süreci gerekmektedir' gibi belirsiz ifadeler KULLANMA. Ya 'Oluşturulsun mu?' de ya da 'Oluşturuldu.' de."
)

OUTPUT_STRUCTURER_INSTRUCTIONS = (
    "Sen backend workflow JSON normalizer katmanısın.\n"
    "Sana bir uzman agent'in ham çıktı metni, aktif adım ve workflow bağlamı verilecek.\n"
    "Görevin bu çıktıyı sadece geçerli JSON olarak normalize etmektir.\n\n"
    "JSON SÖZLEŞMESİ:\n"
    "{\n"
    '  "user_response": "Kullanıcıya gidecek Türkçe cevap",\n'
    '  "workflow_state": "waiting_for_details | waiting_for_approval | completed",\n'
    '  "summary": "UI paneli için tek cümlelik kısa özet",\n'
    '  "shared_context": "Sonraki uzmanlara aktarılacak kısa olgusal özet",\n'
    '  "missing_fields": [{"name": "alan_adi", "label": "Görünen Alan"}],\n'
    '  "approval_required": true | false,\n'
    '  "result_reference": {"kind": "kayit_tipi", "id": "kayit_numarasi"} | null\n'
    "}\n\n"
    "STATE KARAR TABLOSU:\n"
    "┌─────────────────────────────────────┬──────────────────────┬─────────────────┬──────────────────┐\n"
    "│ DURUM                               │ workflow_state        │ missing_fields  │ approval_required│\n"
    "├─────────────────────────────────────┼──────────────────────┼─────────────────┼──────────────────┤\n"
    "│ Eksik bilgi soruluyor               │ waiting_for_details  │ [eksik alanlar] │ false            │\n"
    "│ Bilgi tamam, onay soruluyor         │ waiting_for_approval │ []              │ true             │\n"
    "│ Kullanıcı onay verdi/tool çağrıldı  │ completed            │ []              │ false            │\n"
    "│ Sorgu cevaplandı                    │ completed            │ []              │ false            │\n"
    "│ Desteklenmeyen istek reddedildi     │ completed            │ []              │ false            │\n"
    "│ Kullanıcı iptal etti               │ completed            │ []              │ false            │\n"
    "│ Nezaket kapanışı                   │ completed            │ []              │ false            │\n"
    "└─────────────────────────────────────┴──────────────────────┴─────────────────┴──────────────────┘\n\n"
    "KRİTİK KURALLAR:\n"
    "- Sadece geçerli JSON dön. Markdown veya code fence kullanma.\n"
    "- ONAY TESPİTİ: Agent çıktısında 'oluşturuldu', 'tamamlandı', 'kaydedildi', 'işlendi' veya bir kayıt ID'si (MOCK-xxx, LEAVE-xxx vb.) varsa workflow_state=completed dön.\n"
    "- ONAY TESPİTİ: Workflow bağlamında state=waiting_for_approval iken agent çıktısı onay işlediğini gösteriyorsa workflow_state=completed, approval_required=false dön.\n"
    "- ASLA aynı anda hem approval_required=true hem missing_fields dolu dönme.\n"
    "- waiting_for_details kullanıyorsan missing_fields boş olamaz.\n"
    "- waiting_for_approval kullanıyorsan approval_required=true olmalı, missing_fields=[] olmalı.\n"
    "- completed durumunda approval_required=false ve missing_fields=[] olmalı.\n"
    "- Ham metinde kayıt kimliği varsa result_reference.id alanına taşı.\n"
    "- 'Onay süreci gerekmektedir', 'onay sürecindedir' gibi belirsiz ifadeler waiting_for_approval DEĞİLDİR. Sadece doğrudan 'Onaylıyor musunuz?' veya 'Oluşturulsun mu?' gibi net sorular waiting_for_approval'dır.\n"
    "- Kararsız kaldığında: kayıt ID varsa completed, eksik alan varsa waiting_for_details, aksi halde completed."
)


def create_client(model_id: str) -> OpenAIChatClient:
    """Doğrudan OpenAI API'ye bağlanan client oluşturur."""
    return OpenAIChatClient(
        model=model_id,
        api_key="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",
    )


def create_planner_agent() -> Agent:
    client = create_client(OPENAI_PLANNER_MODEL)
    return Agent(client=client, name="planner_agent", instructions=PLANNER_INSTRUCTIONS)


def create_chat_agent() -> Agent:
    client = create_client(OPENAI_WORKER_MODEL)
    return Agent(client=client, name="chat_agent", instructions=CHAT_INSTRUCTIONS)


def create_synthesis_agent() -> Agent:
    client = create_client(OPENAI_WORKER_MODEL)
    return Agent(client=client, name="synthesis_agent", instructions=SYNTHESIS_INSTRUCTIONS)


def create_output_structurer_agent() -> Agent:
    client = create_client(OPENAI_WORKER_MODEL)
    return Agent(client=client, name="output_structurer_agent", instructions=OUTPUT_STRUCTURER_INSTRUCTIONS)


def create_specialist_agents() -> dict[AgentName, Agent]:
    agents: dict[AgentName, Agent] = {}
    for name, spec in DOMAIN_REGISTRY.items():
        client = create_client(OPENAI_WORKER_MODEL)
        agents[name] = Agent(
            client=client,
            name=name,
            instructions=SPECIALIST_INSTRUCTIONS[name],
            tools=list(spec.tools),
        )
    return agents
