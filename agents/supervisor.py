# agents/supervisor.py
from typing import Literal, List
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from schema.state import AgentState

class RouteResponse(BaseModel):
    next: Literal["HR_Agent", "IT_Agent", "Finance_Agent", "FINISH"]

def create_supervisor_node(llm: ChatOpenAI, members: List[str]):
    """
    Supervisor: Sadece iş talepleri için uzmana yönlendirir.
    """
    
    system_prompt = (
        "Sen bir akıllı yönlendiricisin. Kullanıcı mesajını oku ve sadece SPESİFİK İŞ TALEPLERİ için uzmana yönlendir.\n\n"
        
        "📋 HR_Agent:\n"
        "- İzin talebi (almak, sorgulamak, iptal)\n"
        "- Maaş bordrosu, maaş bilgisi\n"
        "- Personel onayları\n\n"
        
        "💻 IT_Agent:\n"
        "- Bilgisayar/laptop arızası\n"
        "- Donanım talebi (mouse, klavye, ekran, kulaklık)\n"
        "- Teknik destek, arıza kaydı\n\n"
        
        "💰 Finance_Agent:\n"
        "- Avans talebi\n"
        "- Harcama raporu\n"
        "- Ödeme durumu\n\n"
        
        "🔚 FINISH (genel sohbet):\n"
        "- Tüm selamlaşmalar (merhaba, selam, nasılsın, naber)\n"
        "- Genel sorular (neler yaparsın, yardım et, ismim ne)\n"
        "- Sohbet (tarih ne, hava nasıl, vb.)\n"
        "- Belirsiz talepler\n\n"
        
        "KURAL: Eğer AÇIK VE NET bir iş talebi yoksa → FINISH\n\n"
        
        "ÖRNEKLER:\n"
        "FINISH: 'merhaba', 'nasılsın', 'tarihi söyle', 'ismim ne', 'yardım eder misin'\n"
        "HR_Agent: 'izin almak istiyorum', 'bordromu göster'\n"
        "IT_Agent: 'bilgisayarım bozuldu', 'laptop istiyorum'\n"
        "Finance_Agent: 'avans talep edeceğim', 'harcama raporu'\n"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        ("system", "Son mesajı analiz et. Bu NET bir iş talebi mi? Kararını ver:"),
    ])

    supervisor_chain = prompt | llm.with_structured_output(RouteResponse)

    def supervisor_func(state: AgentState):
        try:
            response = supervisor_chain.invoke(state)
            return {"next": response.next}
        except Exception as e:
            print(f"⚠️ Supervisor hatası: {e}")
            return {"next": "FINISH"}

    return supervisor_func