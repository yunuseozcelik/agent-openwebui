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
    
    llm_supervisor = ChatOpenAI(
        model="gpt-5-mini", 
        temperature=0,
        api_key="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", # (Dosyadaki key'i buraya koyarsın)
        max_retries=3,
        max_tokens=4000,
        reasoning={"effort": "medium"},

    )
    
    llm_worker = ChatOpenAI(
        model="gpt-4o-mini", 
        api_key="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",
        temperature=0.3
    )

    members = ["HR_Agent", "IT_Agent", "Finance_Agent", "Math_Agent"]
    supervisor_node = create_supervisor_node(llm_supervisor, members)

    hr_prompt = (
        "Sen uzman bir İnsan Kaynakları (HR) Asistanısın.\n"
        "Görevin: İzin, maaş ve personel onay süreçlerini yönetmek.\n\n"
        "KURALLAR:\n"
        "1. Çok nazik, yardımsever ve detaylı konuş. Kullanıcıya ismiyle hitap et.\n"
        "2. Hemen işlem yapma! Önce kullanıcının ne istediğini tam anla.\n"
        "3. Eğer izin tarihi, gün sayısı gibi bilgiler eksikse, bunları nazikçe sor.\n"
        "4. KRİTİK ADIM: Herhangi bir resmi işlem yapmadan önce mutlaka ÖZET GEÇ ve ONAY İSTE.\n"
        "   Örnek: '2 gün yıllık izin talebi oluşturuyorum. Onaylıyor musunuz?'\n"
        "5. Kullanıcı onaylamadan tool çağırma."
    )

    it_prompt = (
        "Sen uzman bir IT Destek Asistanısın.\n"
        "Görevin: Teknik arızalar ve donanım taleplerini yönetmek.\n\n"
        "KURALLAR:\n"
        "1. Teknik konularda detaylı bilgi ver, sorunun köküne inmeye çalış.\n"
        "2. Arıza kaydı açmadan önce sorunu anladığını teyit et.\n"
        "3. Donanım taleplerinde neden istendiğini öğren.\n"
        "4. KRİTİK ADIM: Ticket (Bilet) oluşturmadan önce mutlaka kullanıcıdan SON ONAYI al.\n"
        "   Örnek: 'Mouse arızası için kayıt açıyorum. İşlemi onaylıyor musunuz?'"
    )

    finance_prompt = (
        "Sen uzman bir Finans Asistanısın.\n"
        "Görevin: Avans, harcama raporu ve ödemeleri yönetmek.\n\n"
        "KURALLAR:\n"
        "1. Parasal konular hassastır, çok dikkatli ve resmi ol.\n"
        "2. Avans veya harcama taleplerinde miktar ve açıklama eksikse mutlaka sor.\n"
        "3. KRİTİK ADIM: İşlem yapmadan önce mutlaka ÖZETLE ve ONAY İSTE.\n"
        "   Örnek: '5.000 TL avans talebi oluşturulacak. Onaylıyor musunuz?'\n"
        "4. Onay gelmeden işlemi sisteme girme."
    )

    math_prompt = (
        "Sen şirketin Matematik ve Bilim Uzmanısın.\n"
        "Görevin: Wolfram Alpha kullanarak matematiksel/bilimsel hesaplamalar yapmak.\n\n"
        
        "🔧 KULLANIM TALİMATI:\n"
        "1. Kullanıcının sorusunu İNGİLİZCE'ye çevir\n"
        "2. calculate_wolfram() fonksiyonunu MUTLAKA çağır\n"
        "3. Sonucu Türkçe'ye çevirip açıkla\n\n"
        
        "📝 DÖNÜŞTÜRME ÖRNEKLERİ:\n"
        "- 'x^2+5x+6=0 çöz' → 'solve x^2 + 5x + 6 = 0'\n"
        "- '100 dolar kaç TL' → '100 USD to TRY'\n"
        "- 'sin(x) türevi' → 'derivative of sin(x)'\n"
        "- 'Türkiye nüfusu' → 'population of Turkey'\n"
        "- 'Dünya Mars mesafe' → 'distance Earth to Mars'\n\n"
        
        "⚠️ KRİTİK: HER ZAMAN önce tool'u çağır, sonra cevap ver!\n"
        "Asla 'manuel çözeyim' deme, Wolfram'ı kullan."
    )

    hr_node = create_worker_node(llm_worker, DEPARTMENT_TOOLS["HR"], "HR_Agent", hr_prompt)
    it_node = create_worker_node(llm_worker, DEPARTMENT_TOOLS["IT"], "IT_Agent", it_prompt)
    finance_node = create_worker_node(llm_worker, DEPARTMENT_TOOLS["Finance"], "Finance_Agent", finance_prompt)
    
    math_node = create_worker_node(llm_worker, DEPARTMENT_TOOLS["Math"], "Math_Agent", math_prompt)

   
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
    
    graph = StateGraph(AgentState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("chat", chat_node)
    graph.add_node("hr", hr_node)
    graph.add_node("it", it_node)
    graph.add_node("finance", finance_node)
    
    graph.add_node("math", math_node)

    graph.add_edge(START, "supervisor")
    graph.add_edge("chat", END)
    graph.add_edge("hr", END)
    graph.add_edge("it", END)
    graph.add_edge("finance", END)
    graph.add_edge("math", END)

    def route(state: AgentState):
        next_step = state.get("next", "FINISH")
        if next_step == "FINISH": return "chat"
        elif next_step == "HR_Agent": return "hr"
        elif next_step == "IT_Agent": return "it"
        elif next_step == "Finance_Agent": return "finance"
        elif next_step == "Math_Agent": return "math" 
        else: return "chat"

    graph.add_conditional_edges(
        "supervisor", 
        route, 
        {
            "chat": "chat", 
            "hr": "hr", 
            "it": "it", 
            "finance": "finance", 
            "math": "math" # Haritaya eklendi
        }
    )

    return graph.compile()