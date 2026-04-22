"""Agent Runner — deploy edilen agent'larla konusma.

Foundry'ye baglilysa gercek agent, degilse local LLM ile agent'in
instructions'ini kullanarak sohbet eder.
"""

from __future__ import annotations

from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient

from agent_factory.config import OPENAI_API_KEY, OPENAI_MODEL
from agent_factory.mock_data.context_loader import get_mock_context
from agent_factory.deployment.foundry_client import get_agent_detail, AgentInfo, FOUNDRY_PROJECT_ENDPOINT
from agent_factory.tools.actions import build_action_tools
from agent_factory.user_context import format_user_block, resolve_user
from utils.portkey import get_maf_client_options


class AgentRunner:
    """Bir deploy edilmis agent ile konusma oturumu."""

    def __init__(self, agent_info: AgentInfo, user_email: str | None = None):
        self.agent_info = agent_info
        self._history: list[dict] = []
        self.user = resolve_user(user_email)

    def set_user(self, user_email: str | None) -> None:
        self.user = resolve_user(user_email)

    async def send(self, user_message: str) -> str:
        """Mesaj gonder, cevap al."""
        # Foundry'ye bagliysa gercek agent calistir
        if FOUNDRY_PROJECT_ENDPOINT and not self.agent_info.id.startswith(("mock_", "draft_")):
            return await self._run_foundry(user_message)

        # Mock/local: LLM ile agent'in instructions'ini kullanarak cevap ver
        return await self._run_local(user_message)

    def _is_action_agent(self) -> bool:
        meta = self.agent_info.metadata or {}
        if meta.get("agent_kind") == "action":
            return True
        # Seed agent isimleri: HR/IT/Finance aksiyona izin verir
        name = (self.agent_info.name or "").lower()
        return any(k in name for k in ("hr", "it-", "finance", "izin", "avans", "ticket", "talep"))

    async def _run_local(self, user_message: str) -> str:
        """Local LLM ile agent'in instructions'ini kullanarak cevap."""
        # gpt-4o ile dene, basarisiz olursa gpt-4o-mini fallback
        for model in [OPENAI_MODEL, "gpt-4o-mini"]:
            try:
                client = OpenAIChatClient(
                    **get_maf_client_options(
                        model_id=model,
                        primary_api_key=OPENAI_API_KEY,
                        engine="agent_runner",
                        component=self.agent_info.name,
                    )
                )
                return await self._run_with_client(client, user_message)
            except Exception:
                if model == "gpt-4o-mini":
                    raise
        raise RuntimeError("Hicbir model ile baglanilamadi")

    async def _run_with_client(self, client: OpenAIChatClient, user_message: str) -> str:
        base_instructions = self.agent_info.instructions or (
            f"Sen {self.agent_info.name} isimli bir AI agent'sin. Kullaniciya yardimci ol."
        )

        mock_context = get_mock_context(self.agent_info.name, self.agent_info.id)
        data_rule = (
            "- Asagida 'MEVCUT VERİ' basliginda gercek veri verilmistir. "
            "YALNIZCA bu veriyi kullan, asla kendinden uydurma veya ornek olusturma."
            if mock_context else
            "- Senden veri, rapor veya liste istenirse: kullanicidan ilgili veriyi iste, uydurma."
        )

        instructions = (
            f"## DAVRANIS KURALLARI (bunlar her seyin onunde gelir)\n"
            f"- Cevaplar kisa ve net olsun.\n"
            f"- Selamlama gibi basit mesajlara tek cumle ile karsilik ver.\n"
            f"- Sen yalnizca '{self.agent_info.name}' agentisin. Gorev taniminin disindaki "
            f"  isteklerde: 'Bu konuda yardimci olamam, gorevim [konu] ile sinirli.' de.\n"
            f"{data_rule}\n\n"
            f"## AGENT TANIMI\n"
            f"{base_instructions}"
        )

        if mock_context:
            instructions += f"\n\n{mock_context}"

        instructions += "\n\n" + format_user_block(self.user)

        tools = None
        if self._is_action_agent():
            tools = build_action_tools(self.user, self.agent_info.name)
            instructions += (
                "\n\n## AKSIYON ARACLARI\n"
                "Asagidaki tool'lara erisimin var. Onay aldiktan sonra bunlardan uygun olani cagir.\n"
                "- request_leave(start_date, end_date, reason)\n"
                "- request_advance(amount_try, reason, repayment_months)\n"
                "- create_ticket(title, description, priority)\n"
                "Tool cagirdiktan sonra donen referans numarasini kullaniciya ilet."
            )

        agent = Agent(
            client=client,
            name=self.agent_info.name,
            instructions=instructions,
            tools=tools,
        )

        context = ""
        if self._history:
            context = "Onceki konusma:\n"
            for msg in self._history[-10:]:
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
