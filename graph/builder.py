# graph/builder.py
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from schema.state import AgentState
from tools import DEPARTMENT_TOOLS
from agents import create_supervisor_node, create_worker_node
from config import OPENAI_API_KEY
from utils.cost_control import LangChainCostCallbackHandler, cost_tracker
from utils.portkey import get_langchain_client_options
from utils.shared_prompts import (
    CHAT_INSTRUCTIONS,
    FINANCE_INSTRUCTIONS,
    GENERAL_INSTRUCTIONS,
    HR_INSTRUCTIONS,
    IT_INSTRUCTIONS,
    MATH_INSTRUCTIONS,
)

api_key = OPENAI_API_KEY
if not api_key:
    print("[HATA] OPENAI_API_KEY BULUNAMADI!")


def build_graph():
    supervisor_callback = LangChainCostCallbackHandler(
        engine="langgraph",
        component="supervisor",
        tracker=cost_tracker,
    )
    worker_callback = LangChainCostCallbackHandler(
        engine="langgraph",
        component="worker",
        tracker=cost_tracker,
    )

    llm_supervisor = ChatOpenAI(
        temperature=0,
        max_retries=3,
        max_tokens=4000,
        reasoning={"effort": "medium"},
        callbacks=[supervisor_callback],
        **get_langchain_client_options(
            model_id="gpt-5.2",
            primary_api_key=api_key,
            engine="langgraph",
            component="supervisor",
        ),
    )

    llm_worker = ChatOpenAI(
        temperature=0.3,
        callbacks=[worker_callback],
        **get_langchain_client_options(
            model_id="gpt-4o-mini",
            primary_api_key=api_key,
            engine="langgraph",
            component="worker",
        ),
    )

    members = ["HR_Agent", "IT_Agent", "Finance_Agent", "Math_Agent", "General_Agent"]
    supervisor_node = create_supervisor_node(llm_supervisor, members)

    hr_prompt = HR_INSTRUCTIONS
    it_prompt = IT_INSTRUCTIONS
    finance_prompt = FINANCE_INSTRUCTIONS
    math_prompt = MATH_INSTRUCTIONS
    general_prompt = GENERAL_INSTRUCTIONS

    hr_node = create_worker_node(llm_worker, DEPARTMENT_TOOLS["HR"], "HR_Agent", hr_prompt)
    it_node = create_worker_node(llm_worker, DEPARTMENT_TOOLS["IT"], "IT_Agent", it_prompt)
    finance_node = create_worker_node(llm_worker, DEPARTMENT_TOOLS["Finance"], "Finance_Agent", finance_prompt)
    math_node = create_worker_node(llm_worker, DEPARTMENT_TOOLS["Math"], "Math_Agent", math_prompt)
    general_node = create_worker_node(llm_worker, DEPARTMENT_TOOLS["General"], "General_Agent", general_prompt)

    def chat_node(state: AgentState):
        """
        Genel sohbet ve selamlama islemlerini yoneten dugum.
        Herhangi bir tool cagirmaz, sadece kullaniciyla etkilesime girer.
        """
        system_msg = CHAT_INSTRUCTIONS

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_msg),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        chain = prompt | llm_supervisor

        try:
            response = chain.invoke(state)
        except Exception as e:
            content = "Su an kisa bir baglanti sorunu var. Yine de yardimci olmaya hazirim."
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
    graph.add_edge("hr", "supervisor")
    graph.add_edge("it", "supervisor")
    graph.add_edge("finance", "supervisor")
    graph.add_edge("math", "supervisor")
    graph.add_edge("general", "supervisor")

    def route(state: AgentState):
        next_step = state.get("next", "FINISH")
        visited = state.get("visited_agents") or []

        if next_step == "FINISH":
            if visited:
                return END
            return "chat"
        if next_step == "HR_Agent":
            return "hr"
        if next_step == "IT_Agent":
            return "it"
        if next_step == "Finance_Agent":
            return "finance"
        if next_step == "Math_Agent":
            return "math"
        if next_step == "General_Agent":
            return "general"
        if visited:
            return END
        return "chat"

    graph.add_conditional_edges(
        "supervisor",
        route,
        {
            END: END,
            "chat": "chat",
            "hr": "hr",
            "it": "it",
            "finance": "finance",
            "math": "math",
            "general": "general",
        },
    )

    return graph.compile()
