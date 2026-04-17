"""Agent Runner — deploy edilen agent'larla konusma.

Foundry'ye baglilysa gercek agent, degilse local LLM ile agent'in
instructions'ini kullanarak sohbet eder.
"""

from __future__ import annotations

from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient

from agent_factory.config import OPENAI_API_KEY, OPENAI_MODEL
from agent_factory.deployment.foundry_client import get_agent_detail, AgentInfo, FOUNDRY_PROJECT_ENDPOINT
from utils.portkey import get_maf_client_options


class AgentRunner:
    """Bir deploy edilmis agent ile konusma oturumu."""

    def __init__(self, agent_info: AgentInfo):
        self.agent_info = agent_info
        self._history: list[dict] = []

    async def send(self, user_message: str) -> str:
        """Mesaj gonder, cevap al."""
        # Foundry'ye bagliysa gercek agent calistir
        if FOUNDRY_PROJECT_ENDPOINT and not self.agent_info.id.startswith("mock_"):
            return await self._run_foundry(user_message)

        # Mock/local: LLM ile agent'in instructions'ini kullanarak cevap ver
        return await self._run_local(user_message)

    async def _run_local(self, user_message: str) -> str:
        """Local LLM ile agent'in instructions'ini kullanarak cevap."""
        client = OpenAIChatClient(
            **get_maf_client_options(
                model_id=self.agent_info.model or OPENAI_MODEL,
                primary_api_key=OPENAI_API_KEY,
                engine="agent_runner",
                component=self.agent_info.name,
            )
        )

        instructions = self.agent_info.instructions or (
            f"Sen {self.agent_info.name} isimli bir AI agent'sin. "
            f"Kullaniciya yardimci ol."
        )

        agent = Agent(
            client=client,
            name=self.agent_info.name,
            instructions=instructions,
        )

        # Basit history management — MAF Agent.run her seferinde yeni
        # conversation baslatiyor, bu yuzden history'yi prompt'a ekliyoruz
        context = ""
        if self._history:
            context = "Onceki konusma:\n"
            for msg in self._history[-10:]:  # Son 10 mesaj
                role = "Kullanici" if msg["role"] == "user" else "Agent"
                context += f"{role}: {msg['content']}\n"
            context += "\n---\nSimdi kullanicinin yeni mesaji:\n"

        full_prompt = context + user_message
        response = await agent.run(full_prompt)

        text = getattr(response, "text", "") or str(getattr(response, "value", ""))

        self._history.append({"role": "user", "content": user_message})
        self._history.append({"role": "assistant", "content": text})

        return text

    async def _run_foundry(self, user_message: str) -> str:
        """Foundry agent'i ile gercek konusma."""
        try:
            from azure.ai.projects import AIProjectClient
            from azure.identity import DefaultAzureCredential

            project = AIProjectClient(
                endpoint=FOUNDRY_PROJECT_ENDPOINT,
                credential=DefaultAzureCredential(),
            )
            agents_client = project.agents

            # Thread yoksa olustur
            if not hasattr(self, "_thread_id") or not self._thread_id:
                thread = agents_client.threads.create()
                self._thread_id = thread.id

            # Mesaj gonder
            agents_client.messages.create(
                thread_id=self._thread_id,
                role="user",
                content=user_message,
            )

            # Agent'i calistir
            run = agents_client.runs.create_and_process(
                thread_id=self._thread_id,
                agent_id=self.agent_info.id,
            )

            # Son assistant mesajini al
            messages = agents_client.messages.list(thread_id=self._thread_id)
            for msg in messages:
                if msg.role == "assistant":
                    # Content text extraction
                    if hasattr(msg, "content") and msg.content:
                        for block in msg.content:
                            if hasattr(block, "text") and hasattr(block.text, "value"):
                                return block.text.value
                    return str(msg.content)

            return "Agent'tan cevap alinamadi."

        except Exception as exc:
            # Foundry basarisiz olursa local'e fallback
            return await self._run_local(user_message)


def create_runner(agent_id: str) -> AgentRunner | None:
    """Agent ID'den runner olustur."""
    agent_info = get_agent_detail(agent_id)
    if not agent_info:
        return None
    return AgentRunner(agent_info)
