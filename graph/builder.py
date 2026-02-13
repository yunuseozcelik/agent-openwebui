# graph/builder.py
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from schema.state import AgentState
from tools import DEPARTMENT_TOOLS
from agents import create_supervisor_node, create_worker_node
from config import OPENAI_API_KEY

api_key = OPENAI_API_KEY

if not api_key:
        print("[HATA] OPENAI_API_KEY BULUNAMADI!")

def build_graph():

    llm_supervisor = ChatOpenAI(
        model="gpt-5.2",
        temperature=0,
        api_key=api_key,
        max_retries=3,
        max_tokens=4000,
        reasoning={"effort": "medium"},
    )

    llm_worker = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=api_key,
        temperature=0.3,
    )

    members = ["HR_Agent", "IT_Agent", "Finance_Agent", "Math_Agent", "General_Agent"]
    supervisor_node = create_supervisor_node(llm_supervisor, members)

    hr_prompt = (
        "Sen uzman bir İnsan Kaynakları (HR) Asistanısın.\n"
        "Görevin: İzin, maaş, personel bilgileri ve onay süreçlerini yönetmek.\n\n"
        "KURALLAR:\n"
        "1. Çok nazik, yardımsever ve detaylı konuş. Kullanıcıya ismiyle hitap et.\n"
        "2. Hemen işlem yapma! Önce kullanıcının ne istediğini tam anla.\n"
        "3. Eğer izin tarihi, gün sayısı gibi bilgiler eksikse, bunları nazikçe sor.\n"
        "4. KRİTİK ADIM: Herhangi bir resmi işlem yapmadan önce mutlaka ÖZET GEÇ ve ONAY İSTE.\n"
        "   Örnek: '2 gün yıllık izin talebi oluşturuyorum. Onaylıyor musunuz?'\n"
        "5. Kullanıcı onaylamadan tool çağırma.\n"
        "6. KRİTİK: Kullanıcının e-posta adresini sohbet geçmişindeki sistem mesajından al.\n"
        "   'Konuştuğun Kullanıcı' satırındaki e-postayı bul.\n"
        "   Bu e-postayı lookup_user_info, lookup_user_detail, check_leave_balance ve get_employee_info tool'larına parametre olarak geçir.\n"
        "7. Eğer kullanıcı izin bakiyesini veya personel bilgisini soruyorsa, otomatik olarak context'teki e-postayı kullan.\n"
        "8. GÜVENLİK: Sadece giriş yapan kullanıcının kendi bilgilerini sorgula. Başka birinin email veya sicil numarasıyla sorgulama yapma.\n"
        "   Kullanıcı başkasının bilgilerini isterse nazikçe 'Sadece kendi bilgilerinizi görüntüleyebilirsiniz' de.\n"
    )

    it_prompt = (
        "Sen uzman bir IT Destek Asistanısın.\n"
        "Görevin: Teknik arızalar, donanım talepleri ve parça sorgulamayı yönetmek.\n\n"
        "KURALLAR:\n"
        "1. Teknik konularda detaylı bilgi ver, sorunun köküne inmeye çalış.\n"
        "2. Arıza kaydı açmadan önce sorunu anladığını teyit et.\n"
        "3. Donanım taleplerinde neden istendiğini öğren.\n"
        "4. KRİTİK ADIM: Ticket (Bilet) oluşturmadan önce mutlaka kullanıcıdan SON ONAYI al.\n"
        "   Örnek: 'Mouse arızası için kayıt açıyorum. İşlemi onaylıyor musunuz?'\n"
        "5. Parça detayı sorulduğunda lookup_part_detail tool'unu parça numarasıyla çağır.\n"
        "6. Parça numarası yoksa kullanıcıdan iste.\n"
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

    general_prompt = (
        "Sen FNSS Genel Ofis Asistanısın.\n"
        "Görevin: Yemek menüsü, servis saatleri ve genel ofis bilgilerini sunmak.\n\n"
        "KURALLAR:\n"
        "1. Yemek menüsü sorulduğunda get_real_lunch_menu tool'unu çağır.\n"
        "2. Bugünün menüsünü özellikle vurgula ve güzel formatla.\n"
        "3. Servis saatleri sorulduğunda get_shuttle_times tool'unu çağır.\n"
        "4. Kullanıcıya ismiyle hitap et, samimi ol.\n"
    )

    hr_node = create_worker_node(llm_worker, DEPARTMENT_TOOLS["HR"], "HR_Agent", hr_prompt)
    it_node = create_worker_node(llm_worker, DEPARTMENT_TOOLS["IT"], "IT_Agent", it_prompt)
    finance_node = create_worker_node(llm_worker, DEPARTMENT_TOOLS["Finance"], "Finance_Agent", finance_prompt)
    math_node = create_worker_node(llm_worker, DEPARTMENT_TOOLS["Math"], "Math_Agent", math_prompt)
    general_node = create_worker_node(llm_worker, DEPARTMENT_TOOLS["General"], "General_Agent", general_prompt)


    def chat_node(state: AgentState):
        """
        Genel sohbet ve selamlama işlemlerini yöneten düğüm.
        Herhangi bir tool çağırmaz, sadece kullanıcıyla etkileşime girer.
        """
        system_msg = (
            "Sen IFS Kurumsal Asistanısın. Şu an 'Genel Sohbet' modundasın.\n"
            "GÖREVİN:\n"
            "1. Kullanıcıya ismiyle hitap et (Sohbet geçmişinden veya bağlamdan ismini yakala).\n"
            "2. Samimi, profesyonel, içten ve yardımsever bir dil kullan.\n"
            "3. Kısa kesmene gerek yok, sohbeti doğal bir şekilde sürdür.\n"
            "4. Gerekirse; İK, IT, Finans, Matematiksel hesaplamalar veya "
            "yemek menüsü/servis saatleri konusunda yardımcı olabileceğini hatırlat.\n\n"
            "DİKKAT:\n"
            "- ASLA kendi kendine hayali bir işlem yapma.\n"
            "- Sadece sohbet et ve yönlendir."
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            MessagesPlaceholder(variable_name="messages"),
        ])

        chain = prompt | llm_supervisor

        try:
            response = chain.invoke(state)
        except Exception as e:
            content = "Üzgünüm, şu an bağlantımda küçük bir sorun var. Nasıl yardımcı olabilirim?"
            print(f"[HATA] Chat Node Hatasi: {e}")
            return {"messages": [AIMessage(content=content)]}

        return {"messages": [AIMessage(content=response.content)]}


    graph = StateGraph(AgentState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("chat", chat_node)
    graph.add_node("hr", hr_node)
    graph.add_node("it", it_node)
    graph.add_node("finance", finance_node)
    graph.add_node("math", math_node)
    graph.add_node("general", general_node)

    graph.add_edge(START, "supervisor")
    graph.add_edge("chat", END)
    graph.add_edge("hr", END)
    graph.add_edge("it", END)
    graph.add_edge("finance", END)
    graph.add_edge("math", END)
    graph.add_edge("general", END)

    def route(state: AgentState):
        next_step = state.get("next", "FINISH")
        if next_step == "FINISH": return "chat"
        elif next_step == "HR_Agent": return "hr"
        elif next_step == "IT_Agent": return "it"
        elif next_step == "Finance_Agent": return "finance"
        elif next_step == "Math_Agent": return "math"
        elif next_step == "General_Agent": return "general"
        else: return "chat"

    graph.add_conditional_edges(
        "supervisor",
        route,
        {
            "chat": "chat",
            "hr": "hr",
            "it": "it",
            "finance": "finance",
            "math": "math",
            "general": "general",
        }
    )

    return graph.compile()
