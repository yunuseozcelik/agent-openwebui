# graph/builder.py
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from config.settings import settings
from schema.state import AgentState
from tools import DEPARTMENT_TOOLS
from agents import create_supervisor_node, create_worker_node

def build_graph():
    # 1. LLM Ayarları
    llm_supervisor = ChatOpenAI(
        model="gpt-5-mini", # veya gpt-4o
        temperature=0,
        api_key="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", # (Dosyadaki key'i buraya koyarsın)
        max_retries=3,
        max_tokens=4000,
        reasoning={"effort": "minimal"},

    )
    
    # Workerlar için de token limitini rahatlatalım
    llm_worker = ChatOpenAI(
        model="gpt-4o-mini", 
        api_key="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",
        temperature=0.3
    )

    members = ["HR_Agent", "IT_Agent", "Finance_Agent"]
    supervisor_node = create_supervisor_node(llm_supervisor, members)

    # ORTAK PRENSİP:
    # 1. Kullanıcıyı dinle.
    # 2. Eksik bilgi varsa SOR.
    # 3. Bilgiler tamsa, yapacağın işlemi ÖZETLE.
    # 4. "Onaylıyor musunuz?" diye sor.
    # 5. SADECE kullanıcı "Evet/Onaylıyorum" derse tool çalıştır.

    hr_prompt = (
        "Sen uzman bir İnsan Kaynakları (HR) Asistanısın.\n"
        "Görevin: İzin, maaş ve personel onay süreçlerini yönetmek.\n\n"
        "KURALLAR:\n"
        "1. Çok nazik, yardımsever ve detaylı konuş. Kullanıcıya ismiyle hitap et.\n"
        "2. Hemen işlem yapma! Önce kullanıcının ne istediğini tam anla.\n"
        "3. Eğer izin tarihi, gün sayısı gibi bilgiler eksikse, bunları nazikçe sor.\n"
        "4. KRİTİK ADIM: Herhangi bir resmi işlem yapmadan (izin girmek, onay vermek vb.) önce mutlaka ÖZET GEÇ ve ONAY İSTE.\n"
        "   Örnek: 'Sayın [İsim], 20-22 Ocak tarihleri arasında 2 gün yıllık izin talebi oluşturuyorum. Onaylıyor musunuz?'\n"
        "5. Kullanıcı onaylamadan tool çağırma."
    )

    it_prompt = (
        "Sen uzman bir IT Destek Asistanısın.\n"
        "Görevin: Teknik arızalar ve donanım taleplerini yönetmek.\n\n"
        "KURALLAR:\n"
        "1. Teknik konularda detaylı bilgi ver, sorunun köküne inmeye çalış.\n"
        "2. Arıza kaydı açmadan önce sorunu anladığını teyit et.\n"
        "3. Donanım taleplerinde (mouse, pc vb.) neden istendiğini öğren.\n"
        "4. KRİTİK ADIM: Ticket (Bilet) oluşturmadan önce mutlaka kullanıcıdan SON ONAYI al.\n"
        "   Örnek: 'Mouse arızası için IT ekibine yüksek öncelikli bir kayıt açıyorum. İşlemi onaylıyor musunuz?'"
    )

    finance_prompt = (
        "Sen uzman bir Finans Asistanısın.\n"
        "Görevin: Avans, harcama raporu ve ödemeleri yönetmek.\n\n"
        "KURALLAR:\n"
        "1. Parasal konular hassastır, çok dikkatli ve resmi ol.\n"
        "2. Avans veya harcama taleplerinde miktar ve açıklama eksikse mutlaka sor.\n"
        "3. KRİTİK ADIM: İşlem yapmadan önce mutlaka ÖZETLE ve ONAY İSTE.\n"
        "   Örnek: 'Ocak ayı için 5.000 TL avans talebi oluşturulacak. Gönderilmesini onaylıyor musunuz?'\n"
        "4. Onay gelmeden işlemi sisteme girme."
    )

    # 4. Worker Nodes (Güncellenmiş Promptlar ile)
    hr_node = create_worker_node(llm_worker, DEPARTMENT_TOOLS["HR"], "HR_Agent", hr_prompt)
    it_node = create_worker_node(llm_worker, DEPARTMENT_TOOLS["IT"], "IT_Agent", it_prompt)
    finance_node = create_worker_node(llm_worker, DEPARTMENT_TOOLS["Finance"], "Finance_Agent", finance_prompt)
    
    # 5. Genel Sohbet Node (Supervisor.py içindeki FINISH yönlendirmesi buraya düşer)
    def chat_node(state: AgentState):
        system_msg = (
            "Sen IFS Kurumsal Asistanısın. Şu an genel sohbet modundasın.\n"
            "Kullanıcıya ismiyle hitap et. Samimi, içten ve yardımsever ol.\n"
            "Kısa kesmene gerek yok, sohbeti sürdürebilirsin.\n"
            "Şirket içi konularda (İK, IT, Finans) yönlendirme yapabileceğini hatırlat."
            # Tarih bilgisi zaten messages[0] içindeki SystemMessage'dan gelecek.
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            MessagesPlaceholder(variable_name="messages"),
        ])
        chain = prompt | llm_supervisor
        response = chain.invoke(state)
        return {"messages": [AIMessage(content=response.content)]}

    # ... (Graph oluşturma kodları, edge'ler aynı kalacak) ...
    # Sadece graph.add_node ve edge kısımlarını builder.py'deki orijinal haliyle koru.
    
    graph = StateGraph(AgentState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("chat", chat_node)
    graph.add_node("hr", hr_node)
    graph.add_node("it", it_node)
    graph.add_node("finance", finance_node)

    graph.add_edge(START, "supervisor")
    graph.add_edge("chat", END)
    graph.add_edge("hr", END)
    graph.add_edge("it", END)
    graph.add_edge("finance", END)

    def route(state: AgentState):
        next_step = state.get("next", "FINISH")
        if next_step == "FINISH": return "chat"
        elif next_step == "HR_Agent": return "hr"
        elif next_step == "IT_Agent": return "it"
        elif next_step == "Finance_Agent": return "finance"
        else: return "chat"

    graph.add_conditional_edges("supervisor", route, {"chat": "chat", "hr": "hr", "it": "it", "finance": "finance"})

    return graph.compile()