"""
Azure AI Agent Service ile multi-agent supervisor sistemi.

Iki farkli yaklasim sunulmustur:
1. azure-ai-projects SDK ile (Foundry Agent Service)
2. Dogrudan Azure OpenAI client ile (daha basit, hemen calisir)

Yaklasim 2 varsayilan olarak aktiftir cunku ek Azure AI Foundry
projesi olusturma gerektirmez - sadece Azure OpenAI endpoint yeterlidir.
"""

import json
from openai import AzureOpenAI
from config import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_DEPLOYMENT,
    AZURE_OPENAI_API_VERSION,
)
from tools import (
    HR_TOOL_DEFINITIONS,
    IT_TOOL_DEFINITIONS,
    TOOL_FUNCTIONS,
)


def get_client() -> AzureOpenAI:
    """Azure OpenAI client olusturur."""
    return AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
    )


# ============================================================
# SUPERVISOR AGENT
# ============================================================

SUPERVISOR_SYSTEM_PROMPT = """Sen bir akilli yonlendiricisin. Kullanici mesajini oku ve uygun departmana yonlendir.

Yonlendirme kurallari:
- HR_Agent: Izin talebi, izin bakiyesi, maas, personel bilgileri
- IT_Agent: Bilgisayar arızası, donanim talebi, teknik destek, ekipman
- CHAT: Selamlasma, genel sohbet, belirsiz talepler

CEVAP FORMATI (sadece JSON dön, baska bir sey yazma):
{"next": "HR_Agent"} veya {"next": "IT_Agent"} veya {"next": "CHAT"}
"""

HR_SYSTEM_PROMPT = """Sen uzman bir Insan Kaynaklari (HR) Asistanisin.
Görevin: Izin, maas, personel bilgileri ve onay sureclerini yonetmek.

KURALLAR:
1. Nazik ve yardimsever ol.
2. Islem yapmadan once onay iste.
3. Tool sonuclarini Turkce olarak kullaniciya aktar.
"""

IT_SYSTEM_PROMPT = """Sen uzman bir IT Destek Asistanisin.
Görevin: Teknik arizalar, donanim talepleri yonetmek.

KURALLAR:
1. Teknik konularda detayli bilgi ver.
2. Ticket olusturmadan once kullanicidan onay al.
3. Tool sonuclarini Turkce olarak kullaniciya aktar.
"""

CHAT_SYSTEM_PROMPT = """Sen IFS Kurumsal Asistanisin. Genel sohbet modundasin.
Samimi, profesyonel ve yardimsever bir dil kullan.
Gerekirse IK, IT konularinda yardimci olabileceğini hatırlat.
"""


def run_supervisor(client: AzureOpenAI, messages: list[dict]) -> str:
    """
    Supervisor: Kullanici mesajini analiz edip hangi agent'a yonlendirecegine karar verir.
    Returns: "HR_Agent", "IT_Agent", veya "CHAT"
    """
    supervisor_messages = [
        {"role": "system", "content": SUPERVISOR_SYSTEM_PROMPT},
        # Sadece son kullanici mesajini gonder (yonlendirme icin yeterli)
        {"role": "user", "content": messages[-1]["content"] if messages else "merhaba"},
    ]

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=supervisor_messages,
        temperature=0,
        max_tokens=50,
        response_format={"type": "json_object"},
    )

    try:
        result = json.loads(response.choices[0].message.content)
        next_agent = result.get("next", "CHAT")
        if next_agent not in ("HR_Agent", "IT_Agent", "CHAT"):
            next_agent = "CHAT"
        return next_agent
    except (json.JSONDecodeError, KeyError):
        return "CHAT"


def run_worker_agent(
    client: AzureOpenAI,
    messages: list[dict],
    system_prompt: str,
    tool_definitions: list[dict],
) -> str:
    """
    Worker agent: Tool calling ile gorevini yerine getirir.
    Azure OpenAI'nin native function calling ozelligini kullanir.
    """
    agent_messages = [
        {"role": "system", "content": system_prompt},
        *messages,
    ]

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=agent_messages,
        tools=tool_definitions,
        tool_choice="auto",
        temperature=0.3,
    )

    assistant_message = response.choices[0].message

    # Tool call varsa calistir
    if assistant_message.tool_calls:
        agent_messages.append(assistant_message)

        for tool_call in assistant_message.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)

            # Tool fonksiyonunu calistir
            fn = TOOL_FUNCTIONS.get(fn_name)
            if fn:
                result = fn(**fn_args)
            else:
                result = json.dumps({"error": f"Bilinmeyen tool: {fn_name}"})

            agent_messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

        # Tool sonuclariyla tekrar LLM'e sor
        second_response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=agent_messages,
            temperature=0.3,
        )
        return second_response.choices[0].message.content

    return assistant_message.content


def run_chat_agent(client: AzureOpenAI, messages: list[dict]) -> str:
    """Genel sohbet agent'i (tool kullanmaz)."""
    chat_messages = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        *messages,
    ]

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=chat_messages,
        temperature=0.7,
    )
    return response.choices[0].message.content


def process_message(messages: list[dict]) -> str:
    """
    Ana orkestrasyon fonksiyonu.
    1. Supervisor mesaji analiz eder
    2. Uygun worker agent'a yonlendirir
    3. Sonucu doner

    Bu akis, LangGraph projesindeki build_graph() ile ayni mantigi izler:
    START -> supervisor -> route -> (hr|it|chat) -> END
    """
    client = get_client()

    # 1) Supervisor karar verir
    next_agent = run_supervisor(client, messages)
    print(f"[SUPERVISOR] Yonlendirme: {next_agent}")

    # 2) Ilgili agent'a yonlendir
    if next_agent == "HR_Agent":
        return run_worker_agent(client, messages, HR_SYSTEM_PROMPT, HR_TOOL_DEFINITIONS)
    elif next_agent == "IT_Agent":
        return run_worker_agent(client, messages, IT_SYSTEM_PROMPT, IT_TOOL_DEFINITIONS)
    else:
        return run_chat_agent(client, messages)
