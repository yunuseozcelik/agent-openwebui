# Copilot Studio Kurulum Rehberi

Bu rehber, mevcut IFS agent senaryosunu Microsoft Copilot Studio'da kurmanizi saglar.

## Onkosullar

- Microsoft 365 lisansi (E3/E5 veya Copilot Studio lisansi)
- Azure aboneligi + Azure OpenAI erisimi
- Power Platform yonetici erisimi

---

## Adim 1: Copilot Studio'ya Giris

1. https://copilotstudio.microsoft.com adresine gidin
2. Microsoft 365 hesabinizla oturum acin
3. Sol menuden **"Create"** > **"New agent"** secin
4. Agent'a isim verin: **"IFS Kurumsal Asistan"**

## Adim 2: Ana Agent'i Yapilandirma (Supervisor)

**Instructions** bolumune su metni yazin:

```
Sen IFS Kurumsal Asistanisin. Kullanicilara IK (izin, maas, personel)
ve IT (arizalar, donanim talepleri) konularinda yardimci olursun.
Turkce konusursun, nazik ve profesyonelsin.
```

**Knowledge** bolumune sirket bilgilerini ekleyin (opsiyonel):
- Sirket wiki sayfasi URL'si
- SharePoint dokumanlari

## Adim 3: IFS API'yi Custom Connector Olarak Baglama

### 3.1 OpenAPI Spec Hazirlama

IFS API'niz icin bir OpenAPI 2.0 (Swagger) dosyasi hazirlayin:

```yaml
swagger: "2.0"
info:
  title: "IFS ERP API"
  version: "1.0"
host: "commonapi.fnss.com.tr"
basePath: "/"
schemes: ["https"]
paths:
  /api/leave/balance:
    get:
      operationId: getLeaveBalance
      summary: "Calisan izin bakiyesini sorgular"
      parameters:
        - name: email
          in: query
          type: string
          required: true
      responses:
        200:
          description: "Basarili"
  /api/leave/request:
    post:
      operationId: createLeaveRequest
      summary: "Izin talebi olusturur"
      parameters:
        - name: body
          in: body
          schema:
            type: object
            properties:
              email: { type: string }
              leave_type: { type: string }
              start_date: { type: string }
              days: { type: integer }
      responses:
        200:
          description: "Talep olusturuldu"
```

### 3.2 Custom Connector Olusturma

1. https://make.powerautomate.com adresine gidin
2. Sol menuden **"More"** > **"Discover all"** > **"Custom connectors"**
3. **"+ New custom connector"** > **"Import an OpenAPI file"**
4. Hazirladiginiz OpenAPI dosyasini yukleyin
5. **Security** sekmesinde:
   - Authentication type: **API Key** veya **OAuth 2.0**
   - IFS API key/token bilgilerinizi girin
6. **Test** sekmesinde baglantinizi dogrulayin
7. **"Create connector"** butonuna basin

### 3.3 Copilot Studio'da Connector'u Kullanma

1. Copilot Studio'da agent'inizi acin
2. Sol menuden **"Actions"** > **"Add an action"**
3. **"Custom connector"** grubundan IFS connector'unuzu secin
4. Kullanmak istediginiz operasyonlari (getLeaveBalance, createLeaveRequest) ekleyin

## Adim 4: Topic'ler Olusturma

### HR Topic'i

1. **"Topics"** > **"+ Add a topic"** > **"From blank"**
2. Isim: **"Izin Islemleri"**
3. Trigger phrases ekleyin:
   - "izin almak istiyorum"
   - "kalan iznim ne kadar"
   - "izin bakiyem"
   - "yillik izin"
4. Akis icinde:
   - **Message** node: "Izin bakiyenizi kontrol ediyorum..."
   - **Action** node: getLeaveBalance action'ini cagirin
   - **Message** node: Sonucu kullaniciya gosterin
   - **Question** node: "Izin talebi olusturmak ister misiniz?"
   - **Condition** node: Evet ise → createLeaveRequest cagir

### IT Topic'i

1. **"Topics"** > **"+ Add a topic"** > **"From blank"**
2. Isim: **"IT Destek"**
3. Trigger phrases:
   - "bilgisayarim bozuldu"
   - "donanim talebi"
   - "teknik destek"
   - "mouse istiyorum"
4. Akis icinde:
   - **Question** node: Sorun detayini sorun
   - **Question** node: Oncelik secimi (dusuk/orta/yuksek)
   - **Action** node: createSupportTicket cagirin
   - **Message** node: Ticket numarasini gosterin

## Adim 5: Azure OpenAI Entegrasyonu

1. Agent ayarlarinda **"Generative AI"** bolumune gidin
2. **"Boost conversations"** secenegini aktif edin
3. Data source olarak **"Azure OpenAI Service on your data"** secin
4. Azure OpenAI endpoint ve deployment bilgilerinizi girin
5. Bu sayede topic'lere uymayan sorularda Azure OpenAI devreye girer

## Adim 6: Multi-Agent Yapilandirma (Opsiyonel)

Copilot Studio'nun multi-agent ozelligi ile:

1. Her departman icin ayri bir "Connected Agent" olusturabilirsiniz
2. Ana agent (orchestrator) kullanici mesajina gore alt agent'a yonlendirir
3. **"Add other agents"** > **"Connected agents"** bolumunden ekleyin

## Adim 7: Teams'e Deploy Etme

1. Copilot Studio'da **"Publish"** butonuna basin
2. **"Channels"** > **"Microsoft Teams"** secin
3. **"Turn on Teams"** butonuna basin
4. Teams Admin Center'dan agent'i kullanicilara dagitin
5. Kullanicilar Teams'te agent'i aratarak bulabilir

## Adim 8: Web'e Deploy Etme

1. **"Channels"** > **"Custom website"** secin
2. Embed kodu kopyalayin
3. Sirket intranet sayfaniza yapistirin

---

## Sinirlamalar

| Konu | Detay |
|------|-------|
| OpenAPI versiyon | Sadece v2.0 (v3 auto-translate edilir ama sorunlu olabilir) |
| OpenAPI dosya boyutu | Maksimum 1 MB |
| Gercek zamanli indeksleme | Yok - dokuman guncelleme ile yansiması arasinda gecikme var |
| UI ozellestirme | Sinirli - renk/logo degisir ama layout degismez |
| Karmasik akislar | Cok adimli, kosullu akislar zorlasir |
| Lisanslama | Copilot Studio ayri lisans gerektirir |
| Model secimi | Sadece GPT-4/GPT-4o destegi |
