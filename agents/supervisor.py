# agents/supervisor.py
from typing import Literal, List

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from schema.state import AgentState


class RouteResponse(BaseModel):
    next: Literal["HR_Agent", "IT_Agent", "Finance_Agent", "Math_Agent", "General_Agent", "FINISH"]


class PlanStep(BaseModel):
    agent: Literal["HR_Agent", "IT_Agent", "Finance_Agent", "Math_Agent", "General_Agent"]
    description: str


class PlanResponse(BaseModel):
    steps: List[PlanStep]


class RoutePlanResponse(BaseModel):
    next: Literal["HR_Agent", "IT_Agent", "Finance_Agent", "Math_Agent", "General_Agent", "FINISH"]
    steps: List[PlanStep] = []


def create_supervisor_node(llm: ChatOpenAI, members: List[str]):
    """
    Supervisor: Sadece is talepleri icin uzmana yonlendirir.
    """

    system_prompt = (
        "Sen bir akilli yonlendiricisin. Kullanici mesajini oku ve sadece spesifik is talepleri icin uzmana yonlendir.\n\n"
        "HR_Agent:\n"
        "- Izin talebi, izin sorgulama, bordro, maas bilgisi, personel bilgileri, personel onaylari\n\n"
        "IT_Agent:\n"
        "- Bilgisayar veya laptop arizasi, donanim talebi, teknik destek, parca sorgulama\n\n"
        "Finance_Agent:\n"
        "- Avans talebi, harcama raporu, odeme durumu\n\n"
        "Math_Agent:\n"
        "- Matematik problemleri, bilimsel veriler, para birimi cevirme, tarih hesaplari, genel istatistikler\n\n"
        "General_Agent:\n"
        "- Yemek menusu, servis saatleri, genel ofis bilgileri\n\n"
        "FINISH:\n"
        "- Selamlasma, genel sohbet, yardim isteme, belirsiz talepler\n\n"
        "KURALLAR:\n"
        "- Acik bir is veya hesaplama talebi yoksa FINISH sec.\n"
        "- Soru matematiksel, bilimsel veya sayisal veri gerektiriyorsa Math_Agent sec.\n"
        "- Yemek veya servis soruluyorsa General_Agent sec.\n"
        "- Kullanici birden fazla departman isteyen bir talep verirse her turda sadece bir agent sec.\n"
        "- Bir agent islemi tamamladiktan sonra henuz islenmeyen talep varsa bir sonraki uygun agent'i sec.\n"
        "- Tum talepler tamamlandiysa FINISH de.\n"
    )

    route_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="messages"),
            ("system", "Sirada kim var? Karar ver:"),
        ]
    )

    planning_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                system_prompt
                + "\n"
                + "ILK ADIMDA AYRICA TUM IS AKISINI `steps` alaninda planla.\n"
                + "Her step icin `agent` ve `description` don.\n"
                + "Eger sadece genel sohbet varsa `steps` bos liste olsun.\n"
                + "Birden fazla departman gerekiyorsa dogru sirayi steps alaninda kur.\n",
            ),
            MessagesPlaceholder(variable_name="messages"),
            ("system", "Hem `next` hem de tam `steps` planini uret:"),
        ]
    )

    supervisor_chain = route_prompt | llm.with_structured_output(RouteResponse)
    planning_chain = planning_prompt | llm.with_structured_output(RoutePlanResponse)

    def supervisor_func(state: AgentState):
        try:
            import json as _json
            from langchain_core.messages import SystemMessage

            visited = state.get("visited_agents") or []
            shared = state.get("shared_context") or {}
            current_plan = state.get("plan_steps") or []

            extra_info_parts = []

            if visited:
                extra_info_parts.append(
                    f"TAMAMLANAN AGENTLAR: {', '.join(visited)}. "
                    "Bu agent'lari tekrar secme. Baska islenecek talep kalmadiysa FINISH de."
                )

            if shared:
                extra_info_parts.append("DEPARTMAN SONUCLARI:")
                for dept, data in shared.items():
                    extra_info_parts.append(f"  [{dept}]: {_json.dumps(data, ensure_ascii=False)[:500]}")
                extra_info_parts.append(
                    "Bu sonuclari dikkate al. Ornegin HR izin bilgisini cikardiysa Finance bunu kullanabilir."
                )

            if extra_info_parts:
                extra_msg = SystemMessage(content="\n".join(extra_info_parts))
                augmented_state = {**state, "messages": list(state["messages"]) + [extra_msg]}
            else:
                augmented_state = state

            if not visited and not current_plan:
                plan_response = planning_chain.invoke(augmented_state)
                next_agent = plan_response.next
                current_plan = [
                    {"agent": step.agent, "description": step.description}
                    for step in plan_response.steps
                ]
            else:
                response = supervisor_chain.invoke(augmented_state)
                next_agent = response.next

            if next_agent != "FINISH" and next_agent in visited:
                print(f"[SUPERVISOR] {next_agent} zaten calisti, FINISH'e zorlaniyor.")
                next_agent = "FINISH"

            new_visited = visited.copy()
            if next_agent != "FINISH":
                new_visited.append(next_agent)

            return {
                "next": next_agent,
                "visited_agents": new_visited,
                "plan_steps": current_plan,
            }
        except Exception as e:
            print(f"[HATA] Supervisor hatasi: {e}")
            return {"next": "FINISH"}

    return supervisor_func


def create_planner(llm: ChatOpenAI):
    """
    Planner: Kullanici mesajini analiz edip hangi agent'larin hangi sirayla
    calisacagini belirler. Chainlit UI'da adimlar olarak gosterilir.
    """

    plan_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "Sen bir is planlayicisisin. Kullanicinin mesajini analiz et ve hangi departmanlarin "
                    "hangi sirayla calisacagini belirle.\n\n"
                    "DEPARTMANLAR:\n"
                    "- HR_Agent: Izin, maas, personel islemleri\n"
                    "- IT_Agent: Teknik destek, donanim talepleri, parca sorgulama\n"
                    "- Finance_Agent: Avans, harcama, odeme islemleri\n"
                    "- Math_Agent: Matematik, bilim, hesaplama\n"
                    "- General_Agent: Yemek menusu, servis saatleri\n\n"
                    "KURALLAR:\n"
                    "- Sadece gerekli agent'lari sec, gereksiz adim ekleme\n"
                    "- Bagimlilik varsa dogru sirayla koy (ornegin: izin -> avans)\n"
                    "- Selamlasma, sohbet gibi basit mesajlarda steps listesini BOS birak []\n"
                    "- Her adim icin kullaniciya gosterilecek kisa bir aciklama yaz (Turkce)\n\n"
                    "ORNEKLER:\n"
                    "- 'merhaba' -> steps: []\n"
                    "- 'izin almak istiyorum' -> steps: [{{agent: HR_Agent, description: 'Izin talebi olusturuluyor'}}]\n"
                    "- 'izin al ve avans iste' -> steps: [{{agent: HR_Agent, description: 'Izin talebi isleniyor'}}, {{agent: Finance_Agent, description: 'Avans talebi olusturuluyor'}}]\n"
                ),
            ),
            MessagesPlaceholder(variable_name="messages"),
            ("system", "Plani olustur:"),
        ]
    )

    plan_chain = plan_prompt | llm.with_structured_output(PlanResponse)

    def plan_func(messages):
        try:
            response = plan_chain.invoke({"messages": messages})
            return response.steps
        except Exception as e:
            print(f"[HATA] Planner hatasi: {e}")
            return []

    return plan_func
