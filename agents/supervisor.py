# agents/supervisor.py
from typing import Literal, List
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from schema.state import AgentState

class RouteResponse(BaseModel):
    next: Literal["HR_Agent", "IT_Agent", "Finance_Agent", "Math_Agent", "General_Agent", "FINISH"]

def create_supervisor_node(llm: ChatOpenAI, members: List[str]):
    """
    Supervisor: Sadece iş talepleri için uzmana yönlendirir.
    """

    system_prompt = (
        "Sen bir akıllı yönlendiricisin. Kullanıcı mesajını oku ve sadece SPESİFİK İŞ TALEPLERİ için uzmana yönlendir.\n\n"

        "📋 HR_Agent:\n"
        "- İzin talebi (almak, sorgulamak, iptal)\n"
        "- Maaş bordrosu, maaş bilgisi\n"
        "- Personel bilgileri, sicil sorgulama\n"
        "- Personel onayları\n\n"

        "💻 IT_Agent:\n"
        "- Bilgisayar/laptop arızası\n"
        "- Donanım talebi (mouse, klavye, ekran, kulaklık)\n"
        "- Teknik destek, arıza kaydı\n"
        "- Parça sorgulama (parça no ile detay bilgisi)\n\n"

        "💰 Finance_Agent:\n"
        "- Avans talebi\n"
        "- Harcama raporu\n"
        "- Ödeme durumu\n\n"

        "🧮 Math_Agent:\n"
        "- Matematik problemleri (denklem, türev, integral)\n"
        "- Bilimsel veriler (uzay, kimya, fizik)\n"
        "- Para birimi çevirme (Dolar kaç TL)\n"
        "- Tarih hesaplamaları\n"
        "- Nüfus, ekonomi gibi genel istatistikler\n\n"

        "🏢 General_Agent:\n"
        "- Yemek menüsü, yemek listesi (bugün yemekte ne var?)\n"
        "- Servis saatleri\n"
        "- Genel ofis bilgileri\n\n"

        "🔚 FINISH (genel sohbet):\n"
        "- Tüm selamlaşmalar (merhaba, selam, nasılsın, naber)\n"
        "- Genel sorular (neler yaparsın, yardım et, ismim ne)\n"
        "- Sohbet (tarih ne, hava nasıl, vb.)\n"
        "- Belirsiz talepler\n\n"

        "KURAL: Açık bir iş/hesaplama talebi yoksa → FINISH\n"
        "KURAL: Eğer soru matematiksel, bilimsel veya güncel veri içeriyorsa MUTLAKA Math_Agent seç.\n"
        "KURAL: Yemek veya servis sorulursa MUTLAKA General_Agent seç.\n"

        "ÖRNEKLER:\n"
        "FINISH: 'merhaba', 'nasılsın', 'tarihi söyle', 'ismim ne', 'yardım eder misin'\n"
        "HR_Agent: 'izin almak istiyorum', 'bordromu göster', 'kalan iznim ne kadar', 'personel bilgilerim'\n"
        "IT_Agent: 'bilgisayarım bozuldu', 'laptop istiyorum', 'parça detayı sorgula'\n"
        "Finance_Agent: 'avans talep edeceğim', 'harcama raporu'\n"
        "General_Agent: 'bugün yemekte ne var', 'servis kaçta', 'yemek listesi'\n"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        ("system", "Sırada kim var? Karar ver:"),
    ])

    supervisor_chain = prompt | llm.with_structured_output(RouteResponse)

    def supervisor_func(state: AgentState):
        try:
            response = supervisor_chain.invoke(state)
            return {"next": response.next}
        except Exception as e:
            print(f"[HATA] Supervisor hatasi: {e}")
            return {"next": "FINISH"}

    return supervisor_func
