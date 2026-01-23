# agents/workers.py
from langchain_core.messages import AIMessage
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
    
    # 2. Graph Node Fonksiyonu
    def node_func(state: AgentState):
        try:
            # Ajanı mevcut durumla çalıştır
            result = agent.invoke(state)
            last_message = result["messages"][-1]
            content = last_message.content

        except Exception as e:
            # Hata olursa sistemi çökertme, kullanıcıya bilgi ver
            error_msg = f"⚠️ İşlem sırasında bir hata oluştu: {str(e)}. Lütfen tekrar dener misin?"
            print(f"HATA ({agent_name}): {e}")
            content = error_msg
        
        return {
            "messages": [
                AIMessage(
                    content=content,
                    name=agent_name
                )
            ]
        }
        
    return node_func