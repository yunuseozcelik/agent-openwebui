# Agent Factory

Kurumsal çok-ajanlı sistem için FNSS Agent Factory. Azure AI Foundry üzerinde agent deploy eder, ama uygulamanın kendisi **standalone** çalışır — local JSON dosyalarını source-of-truth olarak kullanır, Foundry arka planda senkronize edilir.

## Mimari

```
┌─────────────┐      ┌──────────────┐      ┌────────────────┐
│   React UI  │─────▶│  FastAPI     │─────▶│  Azure AI       │
│   (Vite)    │◀─────│  (api/)      │◀─────│  Foundry (ARM)  │
└─────────────┘      └──────────────┘      └────────────────┘
                            │
                            ▼
                  ┌────────────────────┐
                  │  generated/agents  │  ← local source-of-truth
                  │  *.json            │
                  └────────────────────┘
```

- **Frontend** (`web/`): React + Vite + Tailwind + React Flow (agent tree).
- **Backend** (`api/`): FastAPI. Agent CRUD, SSE chat/orchestrate endpoint'leri.
- **Agent Factory** (`agent_factory/`): Builder wizard (LLM analyzer + scaffolder), runner, orchestrator, Foundry deploy client.
- **Mock data** (`agent_factory/mock_data/`): Agent'ların runtime'da context olarak aldığı sahte kurumsal veri (yemek menüsü, HR, satış vb.).

## Kurumsal Agent Ekosistemi

Seed agent'lar (`agent_factory/deployment/seed_agents.py`):

- **Supervisor-Agent** — kullanıcı talebini analiz eder, alt agent'ları seçer.
- **Synthesis-Agent** — alt agent çıktılarını birleştirir.
- **HR-Agent / IT-Agent / Finance-Agent / Math-Agent / General-Agent / Chat-Agent** — alan uzmanları.

Kullanıcı yeni agent eklediğinde domain keyword'lerine göre (`_DOMAIN_MAP`) uygun parent'a (HR/IT/Finance vb.) otomatik attach edilir.

## Agent Felsefesi

Tüm agent'lar **presenter / data delivery** agent'ıdır:

- Runtime'da sistem mock/gerçek veriyi `MEVCUT VERI` başlığı altında enjekte eder.
- Agent bu veriyi kullanıcıya iletir — kendinden içerik üretmez, planlamaz, özelleştirmez.
- Veri yoksa "veri bulunamadı" der, uydurmaz.

Bu prensip `agent_factory/builder/copilot/analyzer.py` içindeki `INSTRUCTION_PROMPT` ile zorlanır.

## Standalone Modu

Uygulama Foundry'ye bağımlı değildir:

- **List/Detail**: `list_agents()` sadece seed tanımları + `generated/agents/*_deployed.json` dosyalarını okur. ARM çağrısı yok.
- **Deploy**: Local `_deployed.json` hemen yazılır, agent UI'da anında görünür. Foundry'ye attach (Application / Deployment / Workflow sync) arka plan thread'inde yapılır — başarısız olsa da deploy başarılıdır.
- **Edit**: Local JSON güncellenir.
- **Delete**: Local dosya silinir + Foundry'den ref temizlenir (best-effort, retry'lı).
- **Self-heal**: Application'da orphan ref (project'te karşılığı olmayan agent) tespit edilirse otomatik temizlenir.

## Orchestration

`agent_factory/orchestrator.py` dinamiktir: her request'te seed + custom agent'ları `generated/agents/` dizininden okur. Deploy sonrası server restart gerekmez.

Akış:

1. **Supervisor** kullanıcı mesajını okur, `SELECTED_AGENTS: ...` döner.
2. Seçilen her **alt agent** paralel çalıştırılır.
3. **Synthesis-Agent** çıktıları birleştirip nihai cevabı verir.

SSE event'leri (`/api/agents/chat/orchestrate`): `routing`, `agent_start`, `agent_done`, `synthesis`, `chunk`, `done`.

## Kurulum

### Backend

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`.env` dosyası:

```
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o
OPENAI_COPILOT_MODEL=gpt-4o-mini
FOUNDRY_PROJECT_ENDPOINT=https://....services.ai.azure.com/api/projects/...
FOUNDRY_APPLICATION_NAME=FNSS
AZURE_SUBSCRIPTION_ID=...
AZURE_RESOURCE_GROUP=...
FOUNDRY_ACCOUNT_NAME=...
FOUNDRY_AGENT_MODEL=deepseek-V3.1
```

Foundry config eksikse app mock modunda çalışır.

### Frontend

```bash
cd web
npm install --include=dev
npm run dev
```

### Çalıştırma

```bash
# Backend (repo kökü)
./run_dev.sh   # veya: uvicorn api.main:app --reload --port 8000

# Frontend
cd web && npm run dev
```

UI `http://localhost:5173`, API `http://localhost:8000`.

## Dizin Yapısı

```
microsoft_agents/
├── api/                       # FastAPI routes, schemas, sessions
│   └── routes/
│       ├── agents.py          # list/detail/chat/edit/delete
│       └── builder.py         # wizard analyze/spec/deploy
├── agent_factory/
│   ├── builder/
│   │   ├── copilot/           # LLM analyzer + wizard
│   │   └── scaffolder/        # instruction fallback templates
│   ├── deployment/
│   │   ├── foundry_client.py  # ARM + local CRUD
│   │   └── seed_agents.py     # HR/IT/Finance/... tanımları
│   ├── mock_data/             # runtime context
│   ├── orchestrator.py        # Supervisor → specialists → Synthesis
│   └── runner.py              # AgentRunner (Foundry | local LLM)
├── generated/
│   ├── agents/                # *_deployed.json (source-of-truth)
│   └── workflows/             # Foundry workflow YAML
└── web/                       # React frontend
    └── src/
        ├── pages/             # Agents, AgentEdit, Builder, Chat
        └── components/AgentFlow.tsx
```

## Önemli Endpoints

| Method | Path | Açıklama |
|---|---|---|
| GET | `/api/agents` | Tüm agent'ları listele |
| GET | `/api/agents/{id}` | Detay |
| PATCH | `/api/agents/{id}` | Instructions/name/purpose güncelle |
| DELETE | `/api/agents/{id}` | Local + Foundry'den sil |
| POST | `/api/agents/chat` | Tek agent sync chat |
| POST | `/api/agents/chat/stream` | Tek agent SSE chat |
| POST | `/api/agents/chat/orchestrate` | Supervisor orchestration SSE |
| POST | `/api/builder/analyze` | Agent tarifini parse et |
| POST | `/api/builder/deploy` | Agent'ı Foundry'ye deploy et |

## Geliştirme Notları

- Agent silmek Application `properties.agents` dizisinden ref'i düşürür, Deployment'tan düşürür, Project'ten version'ları siler. Geçici ARM 404'leri için 3 retry vardır.
- Türkçe `İ` → `i` normalizasyonu `_infer_parent_name` içinde yapılır (combining-dot mismatch'ine karşı).
- Workflow YAML her deploy sonrası `generated/workflows/` altına yazılır.
