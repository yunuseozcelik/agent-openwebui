"""MAF agent fabrika fonksiyonlari."""

from __future__ import annotations

from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient

from config import OPENAI_API_KEY, OPENAI_PLANNER_MODEL, OPENAI_WORKER_MODEL
from domains import DOMAIN_REGISTRY, AgentName
from shared_prompts import CHAT_INSTRUCTIONS, SPECIALIST_INSTRUCTIONS


PLANNER_INSTRUCTIONS = (
    "Sen bir is planlayicisisin. Kullanicinin mesajini analiz et ve hangi departmanlarin "
    "hangi sirayla calisacagini belirle.\n\n"
    "DEPARTMANLAR:\n"
    "- HR_Agent: Personel bilgileri ve izin ozeti sorgulari\n"
    "- IT_Agent: Parca detayi sorgulari\n"
    "- General_Agent: Yemek menusu sorgulari\n"
    "- Test_Agent: Genel sistemi denemek icin mock talep akisi\n\n"
    "KURALLAR:\n"
    "- Sadece gerekli agent'lari sec, gereksiz adim ekleme\n"
    "- Aktif bir workflow verildiyse, kullanicinin son mesaji ayni akisin devamiysa continue_current_workflow=true don\n"
    "- Kullanici yeni bir konu actiysa continue_current_workflow=false don\n"
    "- Selamlasma, sohbet gibi basit mesajlarda steps listesini BOS birak []\n"
    "- Desteklenmeyen isteklerde steps listesini [] don; genel sohbet katmani kapsam sinirini aciklasin\n"
    "- Her adim icin kullaniciya gosterilecek kisa bir aciklama yaz (Turkce)\n\n"
    "ORNEKLER:\n"
    "- 'merhaba' -> {continue_current_workflow: false, steps: []}\n"
    "- 'yillik izin hakkim ne kadar' -> {continue_current_workflow: false, steps: [{agent: HR_Agent, description: 'Izin ozeti sorgulaniyor'}]}\n"
    "- '12345 sicilli kullanicinin detayi' -> {continue_current_workflow: false, steps: [{agent: HR_Agent, description: 'Personel detayi getiriliyor'}]}\n"
    "- 'ABC-001 parcasinin EO bilgisi' -> {continue_current_workflow: false, steps: [{agent: IT_Agent, description: 'Parca detayi sorgulaniyor'}]}\n"
    "- 'bugunun yemek menusu' -> {continue_current_workflow: false, steps: [{agent: General_Agent, description: 'Yemek listesi getiriliyor'}]}\n"
    "- 'mock test baslat' -> {continue_current_workflow: false, steps: [{agent: Test_Agent, description: 'Mock test akisi baslatiliyor'}]}\n"
    "- 'baslik: Laptop kurulumu, oncelik: yuksek' + aktif Test_Agent workflow -> {continue_current_workflow: true, steps: [{agent: Test_Agent, description: 'Mock test bilgileri tamamlanıyor'}]}\n"
    "- 'avans talebi ac' -> {continue_current_workflow: false, steps: []}\n"
    "Cevabi yalnizca gecerli JSON olarak don."
)

SYNTHESIS_INSTRUCTIONS = (
    "Sen IFS Kurumsal Asistaninin final cevap ureten katmanisin.\n"
    "Birden fazla uzman ciktisini tek, akici ve kullanici dostu bir cevapta birlestir.\n"
    "Gereksiz tekrar etme. Aksiyon, durum ve sonraki adimlari netlestir.\n"
    "Cevabi Turkce ver."
)

OUTPUT_STRUCTURER_INSTRUCTIONS = (
    "Sen backend workflow JSON normalizer katmanisin.\n"
    "Sana bir uzman agent'in ham cikti metni, aktif adim ve workflow baglami verilecek.\n"
    "Gorevin bu ciktiyi sadece gecerli JSON olarak normalize etmektir.\n\n"
    "JSON SOZLESMESI:\n"
    "{\n"
    '  "user_response": "Kullaniciya gidecek Turkce cevap",\n'
    '  "workflow_state": "waiting_for_details | waiting_for_approval | completed",\n'
    '  "summary": "UI paneli icin tek cumlelik kisa ozet",\n'
    '  "shared_context": "Sonraki uzmanlara aktarilacak kisa olgusal ozet",\n'
    '  "missing_fields": [{"name": "alan_adi", "label": "Gorunen Alan"}],\n'
    '  "approval_required": true | false,\n'
    '  "result_reference": {"kind": "kayit_tipi", "id": "kayit_numarasi"} | null\n'
    "}\n\n"
    "KURALLAR:\n"
    "- Sadece gecerli JSON don. Markdown veya code fence kullanma.\n"
    "- Kullaniciya eksik bilgi soruluyorsa waiting_for_details kullan ve missing_fields doldur.\n"
    "- Son kullanici onayi isteniyorsa waiting_for_approval kullan ve approval_required=true yap.\n"
    "- Bilgi sorgusu cevaplandiysa completed kullan.\n"
    "- Desteklenmeyen bir resmi islem acikca reddedilip kapsam siniri anlatildiysa da completed kullan.\n"
    "- Nezaket kapanislari ve 'baska bir konuda yardimci olabilir miyim' gibi cumleler bekleme nedeni degildir.\n"
    "- Kullaniciya soru soran, bilgi isteyen, netlestirme yapan veya alan/bilgi listesi veren cevaplarda workflow_state=waiting_for_details don.\n"
    "- waiting_for_details icin missing_fields bos birakma. Cevaptan cikarabildigin alanlari tek tek doldur.\n"
    "- Ham metinde gercek bir kayit kimligi varsa result_reference.id alanina tasi.\n"
    "- Kararsiz kaldiginda en guvenli varsayim: missing_fields varsa waiting_for_details, approval gerekiyorsa waiting_for_approval, aksi halde completed."
)


def create_client(model_id: str) -> OpenAIChatClient:
    """Dogrudan OpenAI API'ye baglanan client olusturur."""
    return OpenAIChatClient(
        model=model_id,
        api_key=OPENAI_API_KEY,
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
