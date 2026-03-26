# Microsoft Agent Framework - IFS Kurumsal Asistan

Microsoft Agent Framework (`agent-framework`) kullanilarak olusturulmus multi-agent supervisor sistemi.
Chainlit UI uzerinden calisir.

## Mimari

```
Kullanici (Chainlit UI)
    |
    v
Triage Agent (yonlendirici)
    |
    +-- hr_agent      : Izin, maas, personel bilgileri (IFS API)
    +-- it_agent      : Destek talebi, ekipman (IFS API)
    +-- finance_agent : Avans, harcama raporu
    +-- general_agent : Yemek menusu, parca sorgulama (IFS API)
```

**HandoffBuilder** ile triage agent kullanici mesajini analiz edip uygun departman agent'ina yonlendirir.

## Kurulum

### 1. Bagimliliklari yukle

```bash
cd microsoft_agents
pip install -r requirements.txt
```

### 2. .env dosyasini ayarla

Proje kokundeki `.env` dosyasina su degiskenleri ekleyin:

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# IFS ERP (gercek API icin)
IFS_API_BASE_URL=https://commonapi.fnss.com.tr
IFS_AUTH_URL=https://fnssaiservice.fnss.com.tr/api/Auth/Login
IFS_CLIENT_ID=<client-id>
IFS_CLIENT_SECRET=<client-secret>
```

### 3. Chainlit ile calistir

```bash
cd microsoft_agents
chainlit run app.py
```

Tarayicinizda `http://localhost:8000` adresinde acilir.

## Dosya Yapisi

```
microsoft_agents/
├── app.py              # Chainlit UI (ana giris noktasi)
├── agent_setup.py      # Agent tanimlari + HandoffBuilder workflow
├── ifs_tools.py        # IFS tool'lari (@tool decorator)
├── config.py           # OpenAI + IFS yapilandirmasi
├── requirements.txt    # Python bagimliliklari
├── COMPARISON.md       # Platform karsilastirmasi
└── copilot_studio_guide.md
```

## Kullanilan Teknolojiler

- **Microsoft Agent Framework** (`agent-framework`): Agent olusturma ve orkestrasyon
- **HandoffBuilder**: Multi-agent routing (triage -> specialist)
- **Chainlit**: Web tabanli sohbet arayuzu
- **OpenAI API**: LLM backend (gpt-4o)
- **IFS ERP API**: Gercek kurumsal veri entegrasyonu
