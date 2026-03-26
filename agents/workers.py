# agents/workers.py
import json
from langchain_core.messages import AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from schema.state import AgentState


def create_worker_node(llm, tools, agent_name: str, system_prompt: str):
    """
    Belirli bir rol için 'Worker Agent' (İşçi Ajan) düğümü oluşturur.
    Args:
        llm: Kullanılacak dil modeli
        tools: Bu ajanın kullanabileceği yetenekler listesi
        agent_name: Ajanın ismi (Örn: HR_Agent) - Graph'ta bu isimle görünecek
        system_prompt: Ajanın kişiliği ve görev tanımı
    """

    agent = create_react_agent(llm, tools, prompt=system_prompt)

    # Agent isimlerini departman key'ine cevir
    dept_key = agent_name.replace("_Agent", "")

    def node_func(state: AgentState):
        try:
            # Diger departmanlarin sonuclarini context olarak ekle
            shared = state.get("shared_context") or {}
            context_msgs = []
            if shared:
                ctx_text = "DIGER DEPARTMANLARDAN GELEN BILGILER:\n"
                for dept, data in shared.items():
                    ctx_text += f"\n[{dept}]: {json.dumps(data, ensure_ascii=False)}"
                ctx_text += "\n\nBu bilgileri dikkate alarak islemini yap."
                context_msgs = [SystemMessage(content=ctx_text)]

            # State'e context mesajlarini ekle
            augmented_state = state
            if context_msgs:
                augmented_state = {**state, "messages": list(state["messages"]) + context_msgs}

            result = agent.invoke(augmented_state)
            last_message = result["messages"][-1]
            content = last_message.content

            # Tool sonuclarindan yapisal veri cikar
            dept_data = _extract_tool_results(result.get("messages", []))

        except Exception as e:
            error_msg = f"Islem sirasinda bir hata olustu: {str(e)}. Lutfen tekrar dener misin?"
            print(f"[HATA] ({agent_name}): {e}")
            content = error_msg
            dept_data = {"error": str(e)}

        # shared_context'i guncelle
        new_shared = dict(shared)
        new_shared[dept_key] = dept_data

        return {
            "messages": [
                AIMessage(
                    content=content,
                    name=agent_name
                )
            ],
            "shared_context": new_shared,
        }

    return node_func


def _extract_tool_results(messages) -> dict:
    """
    Agent mesajlarindan tool sonuclarini yapisal olarak cikarir.
    """
    results = {}
    for msg in messages:
        if type(msg).__name__ == "ToolMessage":
            tool_name = getattr(msg, "name", "unknown")
            content = getattr(msg, "content", "")
            try:
                parsed = json.loads(content)
                results[tool_name] = parsed
            except (json.JSONDecodeError, TypeError):
                results[tool_name] = content
    return results
