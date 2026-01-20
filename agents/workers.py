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
    
    # DÜZELTME BURADA YAPILDI: 'state_modifier' yerine 'prompt' kullanıyoruz.
    agent = create_react_agent(llm, tools, prompt=system_prompt)
    
    # 2. Graph Node Fonksiyonu
    def node_func(state: AgentState):
        # Ajanı mevcut durumla çalıştır
        result = agent.invoke(state)
        
        # Son mesajı al (AI'ın cevabı)
        last_message = result["messages"][-1]
        
        # Supervisor'ın bu mesajın kimden geldiğini anlaması için
        # mesajı özel bir formatta döndürüyoruz.
        return {
            "messages": [
                AIMessage(
                    content=last_message.content,
                    name=agent_name  # Örn: "HR_Agent"
                )
            ]
        }
        
    return node_func