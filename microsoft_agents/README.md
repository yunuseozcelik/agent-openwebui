# Microsoft Azure AI Agent Service - Demo

Mevcut LangGraph supervisor agent sisteminin Azure AI tarafindaki karsiligi.
Ayni senaryo (HR + IT agent) Azure OpenAI ile calisir.

## Kurulum

### 1. Bagimliliklari yukle

```bash
cd microsoft_agents
pip install -r requirements.txt
```

### 2. .env dosyasini ayarla

Proje kokundeki `.env` dosyasina su degiskenleri ekleyin:

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<resource-name>.openai.azure.com/
AZURE_OPENAI_API_KEY=<api-key>
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2025-01-01-preview
```

### 3. Calistir

```bash
python main.py
```

Server http://localhost:9098 adresinde baslar.

### 4. Test et

```bash
curl -X POST http://localhost:9098/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "azure-agent",
    "messages": [{"role": "user", "content": "kalan iznim ne kadar?"}]
  }'
```

### 5. Open WebUI ile test

Open WebUI'de yeni bir OpenAI-uyumlu baglanti ekleyin:
- **URL**: http://localhost:9098/v1
- **Model**: azure-agent

## Dosya Yapisi

```
microsoft_agents/
├── main.py          # FastAPI server (port 9098)
├── agents.py        # Supervisor + HR/IT worker agent'lar
├── tools.py         # Tool tanimlari ve fonksiyonlari
├── config.py        # Azure yapilandirmasi
├── requirements.txt # Python bagimliliklari
├── COMPARISON.md    # 3 platform karsilastirmasi
└── copilot_studio_guide.md  # Copilot Studio kurulum rehberi
```

## Karsilastirma

| | LangGraph (port 9099) | Azure Agent (port 9098) |
|---|---|---|
| Supervisor LLM | GPT-5.2 | GPT-4o (Azure) |
| Worker LLM | GPT-4o-mini | GPT-4o (Azure) |
| Orkestrasyon | StateGraph | JSON routing |
| Tool calling | LangChain @tool | OpenAI function calling |
| State | TypedDict + operator.add | Stateless (mesaj bazli) |

Detayli karsilastirma icin: [COMPARISON.md](COMPARISON.md)
Copilot Studio rehberi icin: [copilot_studio_guide.md](copilot_studio_guide.md)
