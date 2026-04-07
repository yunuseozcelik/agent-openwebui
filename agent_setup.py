"""MAF agent fabrika fonksiyonları."""

from __future__ import annotations

from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient

from config import OPENAI_API_KEY, OPENAI_PLANNER_MODEL, OPENAI_WORKER_MODEL
from domains import DOMAIN_REGISTRY, AgentName
from shared_prompts import CHAT_INSTRUCTIONS, SPECIALIST_INSTRUCTIONS


PLANNER_INSTRUCTIONS = (
    "Sen bir iş planlayıcısısın. Kullanıcının mesajını analiz et ve hangi departmanların "
    "hangi sırayla çalışacağını belirle.\n\n"
    "DEPARTMANLAR:\n"
    "- HR_Agent: Personel bilgileri ve izin özeti sorguları\n"
    "- IT_Agent: Parça detayı sorguları\n"
    "- General_Agent: Yemek menüsü sorguları\n"
    "- Test_Agent: Genel sistemi denemek için mock talep akışı\n\n"
    "KURALLAR:\n"
    "- Sadece gerekli agent'ları seç, gereksiz adım ekleme\n"
    "- Aktif bir workflow verildiyse, kullanıcının son mesajı aynı akışın devamıysa continue_current_workflow=true dön\n"
    "- Kullanıcı yeni bir konu açtıysa continue_current_workflow=false dön\n"
    "- Selamlaşma, sohbet gibi basit mesajlarda steps listesini BOŞ bırak []\n"
    "- Desteklenmeyen isteklerde steps listesini [] dön; genel sohbet katmanı kapsam sınırını açıklasın\n"
    "- Her adım için kullanıcıya gösterilecek kısa bir açıklama yaz (Türkçe)\n\n"
    "ÖRNEKLER:\n"
    "- 'merhaba' -> {continue_current_workflow: false, steps: []}\n"
    "- 'yıllık izin hakkım ne kadar' -> {continue_current_workflow: false, steps: [{agent: HR_Agent, description: 'İzin özeti sorgulanıyor'}]}\n"
    "- '12345 sicilli kullanıcının detayı' -> {continue_current_workflow: false, steps: [{agent: HR_Agent, description: 'Personel detayı getiriliyor'}]}\n"
    "- 'ABC-001 parçasının EO bilgisi' -> {continue_current_workflow: false, steps: [{agent: IT_Agent, description: 'Parça detayı sorgulanıyor'}]}\n"
    "- 'bugünün yemek menüsü' -> {continue_current_workflow: false, steps: [{agent: General_Agent, description: 'Yemek listesi getiriliyor'}]}\n"
    "- 'mock test başlat' -> {continue_current_workflow: false, steps: [{agent: Test_Agent, description: 'Mock test akışı başlatılıyor'}]}\n"
    "- 'başlık: Laptop kurulumu, öncelik: yüksek' + aktif Test_Agent workflow -> {continue_current_workflow: true, steps: [{agent: Test_Agent, description: 'Mock test bilgileri tamamlanıyor'}]}\n"
    "- 'avans talebi aç' -> {continue_current_workflow: false, steps: []}\n"
    "Cevabı yalnızca geçerli JSON olarak dön."
)

SYNTHESIS_INSTRUCTIONS = (
    "Sen IFS Kurumsal Asistanının final cevap üreten katmanısın.\n"
    "Birden fazla uzman çıktısını tek, akıcı ve kullanıcı dostu bir cevapta birleştir.\n"
    "Gereksiz tekrar etme. Aksiyon, durum ve sonraki adımları netleştir.\n"
    "Cevabı Türkçe ver."
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
    "KURALLAR:\n"
    "- Sadece geçerli JSON dön. Markdown veya code fence kullanma.\n"
    "- Kullanıcıya eksik bilgi soruluyorsa waiting_for_details kullan ve missing_fields doldur.\n"
    "- Son kullanıcı onayı isteniyorsa waiting_for_approval kullan ve approval_required=true yap.\n"
    "- Bilgi sorgusu cevaplandıysa completed kullan.\n"
    "- Desteklenmeyen bir resmi işlem açıkça reddedilip kapsam sınırı anlatıldıysa da completed kullan.\n"
    "- Nezaket kapanışları ve 'başka bir konuda yardımcı olabilir miyim' gibi cümleler bekleme nedeni değildir.\n"
    "- Kullanıcıya soru soran, bilgi isteyen, netleştirme yapan veya alan/bilgi listesi veren cevaplarda workflow_state=waiting_for_details dön.\n"
    "- waiting_for_details için missing_fields boş bırakma. Cevaptan çıkarabildiğin alanları tek tek doldur.\n"
    "- Ham metinde gerçek bir kayıt kimliği varsa result_reference.id alanına taşı.\n"
    "- Kararsız kaldığında en güvenli varsayım: missing_fields varsa waiting_for_details, approval gerekiyorsa waiting_for_approval, aksi halde completed."
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
