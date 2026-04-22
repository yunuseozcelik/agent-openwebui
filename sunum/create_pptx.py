"""Agent Factory MVP — PowerPoint Sunum Oluşturucu"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# ── Renkler ──
BLACK = RGBColor(0x11, 0x11, 0x11)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GRAY = RGBColor(0x66, 0x66, 0x66)
LIGHT_GRAY = RGBColor(0x99, 0x99, 0x99)
LIGHT_BG = RGBColor(0xF5, 0xF5, 0xF5)
BLUE = RGBColor(0x25, 0x63, 0xEB)
GREEN = RGBColor(0x16, 0xA3, 0x4A)
RED = RGBColor(0xDC, 0x26, 0x26)
ORANGE = RGBColor(0xEA, 0x58, 0x0C)
TEAL = RGBColor(0x0D, 0x94, 0x88)
PURPLE = RGBColor(0x7C, 0x3A, 0xED)
DARK_BG = RGBColor(0x1A, 0x1A, 0x2E)


def add_bg(slide, color=WHITE):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_text(slide, left, top, width, height, text, size=18, bold=False, color=BLACK, align=PP_ALIGN.LEFT, font_name="Segoe UI"):
    txBox = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.font.name = font_name
    p.alignment = align
    return txBox


def add_multiline(slide, left, top, width, height, lines, size=14, color=BLACK, spacing=Pt(6), font_name="Segoe UI", bold_first=False):
    txBox = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.size = Pt(size)
        p.font.color.rgb = color
        p.font.name = font_name
        p.space_after = spacing
        if bold_first and i == 0:
            p.font.bold = True
    return txBox


def add_rect(slide, left, top, width, height, fill_color, text="", text_color=WHITE, text_size=14, bold=False, radius=False):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.fill.background()
    if text:
        tf = shape.text_frame
        tf.word_wrap = True
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        tf.paragraphs[0].text = text
        tf.paragraphs[0].font.size = Pt(text_size)
        tf.paragraphs[0].font.color.rgb = text_color
        tf.paragraphs[0].font.bold = bold
        tf.paragraphs[0].font.name = "Segoe UI"
    return shape


def add_arrow(slide, x, y, w=0.4, h=0.25):
    arrow = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x), Inches(y), Inches(w), Inches(h))
    arrow.fill.solid()
    arrow.fill.fore_color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
    arrow.line.fill.background()
    return arrow


def slide_header(slide, title, subtitle=None):
    add_text(slide, 0.8, 0.5, 11, 0.8, title, size=32, bold=True, color=BLACK)
    if subtitle:
        add_text(slide, 0.8, 1.2, 11, 0.5, subtitle, size=16, color=GRAY)


def section_slide(title, subtitle=""):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(s, DARK_BG)
    add_text(s, 1.5, 2.8, 10, 1.0, title, size=44, bold=True, color=WHITE)
    if subtitle:
        add_text(s, 1.5, 4.0, 10, 0.6, subtitle, size=20, color=RGBColor(0x88, 0x88, 0x88))
    return s


# ════════════════════════════════════════════════════════
# SLIDE 1 — Kapak
# ════════════════════════════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, WHITE)
add_rect(s, 0, 0, 13.333, 7.5, BLACK)
add_text(s, 1.5, 1.5, 10, 1.2, "Agent Factory", size=52, bold=True, color=WHITE)
add_text(s, 1.5, 2.8, 10, 0.6, "Dogal Dil ile AI Agent Olusturma Platformu", size=24, color=RGBColor(0xAA, 0xAA, 0xAA))
add_text(s, 1.5, 4.0, 10, 0.5, "Ne Yaptik  /  Nasil Yaptik  /  Neden Yaptik  /  Ne Yapicaz", size=18, color=RGBColor(0x77, 0x77, 0x77))
add_text(s, 1.5, 6.2, 10, 0.4, "Nisan 2026  ·  Dahili Sunum", size=14, color=RGBColor(0x55, 0x55, 0x55))


# ════════════════════════════════════════════════════════
# SLIDE 2 — Genel Bakis: Ne Yaptik?
# ════════════════════════════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, WHITE)
slide_header(s, "Genel Bakis: Ne Yaptik?", "Uctan uca kurulan altyapi")

components = [
    ("Agent Factory\nUygulamasi", "Dogal dille agent olustur,\nduzenle, sil, chat yap", BLUE),
    ("App Service", "Uygulamayi Azure'a\ndeploy ettik", BLACK),
    ("Front Door", "Guvenli giris kapisi\n+ CDN + SSL", TEAL),
    ("WAF", "Guvenlik duvari\ncustom kurallar", ORANGE),
    ("Origin Lock", "Direkt erisimi\nkapattik → 403", RED),
    ("CI/CD", "Git push → otomatik\nAzure deploy", GREEN),
]

for i, (title, desc, color) in enumerate(components):
    x = 0.5 + (i % 3) * 4.2
    y = 2.2 + (i // 3) * 2.5
    add_rect(s, x, y, 3.8, 2.1, color, title, WHITE, 15, True, radius=True)
    add_text(s, x + 0.2, y + 1.3, 3.4, 0.8, desc, size=12, color=WHITE, align=PP_ALIGN.CENTER)


# ════════════════════════════════════════════════════════
# SLIDE 3 — Trafik Akisi Diyagrami
# ════════════════════════════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, WHITE)
slide_header(s, "Trafik Akisi", "Bir istek nasil ilerliyor?")

# Kutular
boxes = [
    (0.5, "Kullanici\n(Tarayici)", BLUE),
    (3.0, "Azure\nFront Door", TEAL),
    (5.5, "WAF\nKurallari", ORANGE),
    (8.0, "App Service\n(Backend+Frontend)", BLACK),
    (10.5, "Azure AI\nFoundry", GREEN),
]
for x, label, color in boxes:
    add_rect(s, x, 2.8, 2.2, 1.4, color, label, WHITE, 13, True, radius=True)

# Oklar
for x in [2.7, 5.2, 7.7, 10.2]:
    add_arrow(s, x, 3.3)

# Alt aciklamalar
notes = [
    (0.5, "HTTPS istegi\ngonderir"),
    (3.0, "SSL sonlandirir\nCDN cache kontrol\nHeader ekler"),
    (5.5, "Rate limit kontrol\nGeo-filter kontrol\nPayload kontrol"),
    (8.0, "FastAPI isleme alir\nReact UI sunar\nAPI response doner"),
    (10.5, "Agent calistirir\nGPT-4o cagrilir\nSonuc doner"),
]
for x, text in notes:
    add_text(s, x, 4.5, 2.2, 1.2, text, size=11, color=GRAY, align=PP_ALIGN.CENTER)

# Alt kisim: Engellenen trafik
add_rect(s, 0.5, 6.0, 12.2, 0.9, RGBColor(0xFE, 0xF2, 0xF2), radius=True)
add_text(s, 0.8, 6.1, 11.5, 0.6,
         "Engellenen trafik:  Direkt App Service erisimi → 403  |  TR disinda → 403  |  Rate limit asimi → 429  |  Buyuk payload → 403",
         size=13, bold=True, color=RED)


# ════════════════════════════════════════════════════════
# SECTION: App Service
# ════════════════════════════════════════════════════════
section_slide("App Service", "Uygulamayi Azure'a Tasidik")

# SLIDE 5 — App Service: Ne Yaptik
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, WHITE)
slide_header(s, "App Service: Ne Yaptik?", "Backend + Frontend'i Azure'da calistirdik")

# Sol: Ne yaptik
add_rect(s, 0.8, 2.0, 5.8, 5.0, LIGHT_BG, radius=True)
add_text(s, 1.2, 2.2, 5.0, 0.4, "Ne Yaptik", size=20, bold=True, color=BLACK)
add_multiline(s, 1.2, 2.8, 5.0, 4.0, [
    "• Azure Portal'dan App Service olusturduk",
    "   - Python 3.11, Linux, West Europe bolge",
    "   - B1 plan (paylasimli, ucretli katman)",
    "",
    "• Backend: FastAPI + Gunicorn + Uvicorn workers",
    "   - Async destegi icin UvicornWorker kullanildi",
    "   - 2 worker, 120sn timeout",
    "",
    "• Frontend: React build → statik dosyalar",
    "   - npm ci → npm run build",
    "   - Backend uzerinden serve ediliyor",
], size=13, color=GRAY)

# Sag: Neden App Service
add_rect(s, 7.0, 2.0, 5.5, 5.0, LIGHT_BG, radius=True)
add_text(s, 7.4, 2.2, 4.7, 0.4, "Neden App Service?", size=20, bold=True, color=BLACK)
add_multiline(s, 7.4, 2.8, 4.7, 4.0, [
    "• Managed platform — sunucu bakimi Microsoft'ta",
    "   - OS patching, scaling otomatik",
    "",
    "• GitHub Actions entegrasyonu kolay",
    "   - Push → Build → Deploy (3-5 dakika)",
    "",
    "• Auto-scale mumkun",
    "   - Yuk artinca otomatik olceklenir",
    "",
    "• Diger Azure servisleriyle entegrasyon",
    "   - Front Door, WAF, Managed Identity",
    "",
    "• Startup komutu ozellestirilebilir",
], size=13, color=GRAY)

# Alt: Startup komutu
add_rect(s, 0.8, 7.15, 11.7, 0.0, BLACK)
# moved up a bit
add_text(s, 0.8, 6.7, 11.7, 0.4,
         "Startup:  gunicorn api.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120",
         size=11, color=GRAY, font_name="Consolas")


# SLIDE 6 — App Service: Nasil Yaptik (adimlar)
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, WHITE)
slide_header(s, "App Service: Nasil Yaptik?", "Azure Portal uzerinden adim adim")

steps = [
    ("1", "Resource Group", "agentfactory-rg\nWest Europe bolgesi", BLACK),
    ("2", "App Service Plan", "B1 tier (Linux)\nPython 3.11 runtime", BLACK),
    ("3", "Web App Olustur", "agentfactory-api\nGitHub repo baglantisi", BLACK),
    ("4", "Startup Komutu", "Gunicorn + Uvicorn\ncustom startup command", BLACK),
    ("5", "Dogrulama", "/api/health endpoint\ncalisiyor mu kontrol", GREEN),
]

for i, (num, title, desc, color) in enumerate(steps):
    x = 0.3 + i * 2.55
    add_rect(s, x, 2.5, 2.3, 0.6, color, f"{num}. {title}", WHITE, 13, True, radius=True)
    add_text(s, x + 0.1, 3.3, 2.1, 0.8, desc, size=12, color=GRAY, align=PP_ALIGN.CENTER)
    if i < 4:
        add_arrow(s, x + 2.3, 2.65)

# Karsilasilan sorun
add_rect(s, 0.8, 4.5, 11.7, 2.3, RGBColor(0xFF, 0xF7, 0xED), radius=True)
add_text(s, 1.2, 4.7, 10.9, 0.4, "Karsilasilan Sorun & Cozum", size=18, bold=True, color=ORANGE)
add_multiline(s, 1.2, 5.2, 10.9, 1.5, [
    "Sorun: App Service varsayilan sayfayi gosteriyordu — Oryx framework'u algilamadi",
    "   → Backend calismiyor, \"Hey, Python developer!\" sayfasi gorunuyor",
    "",
    "Cozum: Startup komutu manuel olarak ayarlandi",
    "   → GitHub Actions workflow'una startup-command eklendi",
    "   → gunicorn api.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker ayari yapildi",
], size=13, color=GRAY)


# ════════════════════════════════════════════════════════
# SECTION: Front Door
# ════════════════════════════════════════════════════════
section_slide("Azure Front Door", "Guvenli Giris Kapisi + CDN + SSL")

# SLIDE 8 — Front Door: Ne Yaptik / Neden
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, WHITE)
slide_header(s, "Front Door: Ne Yaptik?", "Uygulamanin onune guvenlik + performans katmani koyduk")

# Sol: Ne yaptik
add_rect(s, 0.8, 2.0, 5.8, 4.8, LIGHT_BG, radius=True)
add_text(s, 1.2, 2.2, 5.0, 0.4, "Ne Yaptik", size=20, bold=True, color=BLACK)
add_multiline(s, 1.2, 2.8, 5.0, 4.0, [
    "• Front Door profili olusturduk (Standard tier)",
    "",
    "• Endpoint tanimladik:",
    "   agentfactory-*.azurefd.net",
    "",
    "• Origin group olusturduk",
    "   → App Service'imizi origin olarak bagladik",
    "",
    "• Route tanimladik",
    "   → Tum trafik (/*) backend'e yonlendirildi",
    "",
    "• HTTPS zorunlu, HTTP → HTTPS redirect",
], size=13, color=GRAY)

# Sag: Neden
add_rect(s, 7.0, 2.0, 5.5, 4.8, LIGHT_BG, radius=True)
add_text(s, 7.4, 2.2, 4.7, 0.4, "Neden Front Door?", size=20, bold=True, color=BLACK)
add_multiline(s, 7.4, 2.8, 4.7, 4.0, [
    "• SSL/TLS sifreleme (HTTPS zorunlu)",
    "   - TLS 1.2+ — modern sifreleme standardi",
    "",
    "• Tek giris noktasi",
    "   - Kullanicilar sadece FD URL'ini goruyor",
    "   - Backend URL gizli",
    "",
    "• CDN (Content Delivery Network)",
    "   - Statik dosyalar edge'den sunuluyor",
    "   - Daha hizli sayfa yuklenme",
    "",
    "• WAF baglama noktasi",
    "   - Guvenlik duvari burada aktif",
], size=13, color=GRAY)


# SLIDE 9 — Front Door: Nasil Yaptik
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, WHITE)
slide_header(s, "Front Door: Nasil Yaptik?", "Azure Portal uzerinden kurulum adimlari")

fd_steps = [
    ("1", "Profil Olustur", "Standard tier\nMicrosoft CDN\nagentfactory-fd", TEAL),
    ("2", "Endpoint Tanimla", "agentfactory-*\n.azurefd.net\nHTTPS zorunlu", TEAL),
    ("3", "Origin Group", "App Service bagla\nHealth probe aktif\nPriority: 1", TEAL),
    ("4", "Route Kurali", "/* → origin group\nHTTPS redirect\nCache policy", TEAL),
    ("5", "WAF Bagla", "Security policy\nFD'ye WAF ekle\nDetection mode", ORANGE),
]

for i, (num, title, desc, color) in enumerate(fd_steps):
    x = 0.3 + i * 2.55
    add_rect(s, x, 2.5, 2.3, 1.8, color, f"{num}. {title}", WHITE, 13, True, radius=True)
    add_text(s, x + 0.1, 3.5, 2.1, 1.2, desc, size=11, color=WHITE, align=PP_ALIGN.CENTER)
    if i < 4:
        add_arrow(s, x + 2.3, 3.2)

# Kavramlar aciklamasi
add_rect(s, 0.8, 5.0, 3.7, 2.0, LIGHT_BG, radius=True)
add_text(s, 1.1, 5.1, 3.3, 0.4, "Endpoint", size=15, bold=True, color=TEAL)
add_text(s, 1.1, 5.5, 3.3, 1.2, "Kullanicinin eristigi URL.\nDis dunyaya acilan adres.\nCustom domain baglanabilir.", size=12, color=GRAY)

add_rect(s, 4.8, 5.0, 3.7, 2.0, LIGHT_BG, radius=True)
add_text(s, 5.1, 5.1, 3.3, 0.4, "Origin Group", size=15, bold=True, color=TEAL)
add_text(s, 5.1, 5.5, 3.3, 1.2, "Arkadaki gercek sunucu(lar).\nApp Service buraya bagli.\nHealth probe ile saglik kontrolu.", size=12, color=GRAY)

add_rect(s, 8.8, 5.0, 3.7, 2.0, LIGHT_BG, radius=True)
add_text(s, 9.1, 5.1, 3.3, 0.4, "Route", size=15, bold=True, color=TEAL)
add_text(s, 9.1, 5.5, 3.3, 1.2, "URL pattern → origin eslestirmesi.\n/* = tum trafik yonlendirilir.\nProtocol: HTTPS only.", size=12, color=GRAY)


# ════════════════════════════════════════════════════════
# SECTION: WAF
# ════════════════════════════════════════════════════════
section_slide("WAF (Web Application Firewall)", "Guvenlik Duvari + Custom Kurallar")

# SLIDE 11 — WAF: Ne Yaptik / Neden
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, WHITE)
slide_header(s, "WAF: Ne Yaptik?", "Front Door'a guvenlik duvari bagladik ve custom kurallar yazdik")

# Sol
add_rect(s, 0.8, 2.0, 5.8, 4.8, LIGHT_BG, radius=True)
add_text(s, 1.2, 2.2, 5.0, 0.4, "Ne Yaptik", size=20, bold=True, color=BLACK)
add_multiline(s, 1.2, 2.8, 5.0, 4.0, [
    "• WAF policy olusturduk",
    "   - agentfactory-waf",
    "   - Front Door'a bagladik",
    "",
    "• 3 custom kural yazdik:",
    "   1. Rate Limiting (IP basi istek limiti)",
    "   2. Geo-Filtering (sadece TR)",
    "   3. Payload Size Limiti",
    "",
    "• Su an Detection mode",
    "   - Sadece logluyor, engellemiyor",
    "   - Test edip Prevention'a gecirilecek",
], size=13, color=GRAY)

# Sag
add_rect(s, 7.0, 2.0, 5.5, 4.8, LIGHT_BG, radius=True)
add_text(s, 7.4, 2.2, 4.7, 0.4, "Neden WAF?", size=20, bold=True, color=BLACK)
add_multiline(s, 7.4, 2.8, 4.7, 4.0, [
    "• DDoS ve brute force korumassi",
    "   - Rate limiting ile suistimal engellenir",
    "",
    "• Cografi kisitlama",
    "   - Sirket TR'de, dis erisim gereksiz",
    "   - Saldiri yuzeyini daraltir",
    "",
    "• Buyuk payload saldirilarini engelleme",
    "   - Buffer overflow, zip bomb vb.",
    "",
    "• Ilerde OWASP kurallari",
    "   - SQL injection, XSS, CSRF otomatik",
    "   - Premium tier ile gelecek",
], size=13, color=GRAY)


# SLIDE 12 — WAF Custom Rules Detay
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, WHITE)
slide_header(s, "WAF: Custom Kurallar Detay", "Yazdgimiz 3 guvenlik kurali")

rules = [
    ("RateLimitPerIP", "Rate Limiting", ORANGE,
     "IP basi dakikada max 300 API istegi",
     "DDoS ve brute force saldiri korumasi",
     "Asimda → 429 Too Many Requests",
     "Match: Tum HTTP istekleri\nAction: Rate limit\nThreshold: 300 req/dk"),

    ("AllowTurkeyOnly", "Geo-Filtering", BLUE,
     "Turkiye disindann gelen trafik engellenir",
     "Sirket TR'de, disaridan erisim gereksiz",
     "Diger ulkeler → 403 Forbidden",
     "Match: GeoLocation != TR\nAction: Block\nOncelik: 2"),

    ("BlockLargePayload", "Payload Limiti", RED,
     "512KB ustu istekler engellenir",
     "Buyuk dosya/payload saldirilari onlenir",
     "Buyuk POST/PUT → 403 Forbidden",
     "Match: Content-Length > 524288\nAction: Block\nOncelik: 3"),
]

for i, (rule_id, title, color, what, why, result, config) in enumerate(rules):
    y = 1.9 + i * 1.85
    add_rect(s, 0.8, y, 0.15, 1.6, color)

    add_text(s, 1.2, y, 2.0, 0.35, title, size=16, bold=True, color=BLACK)
    add_text(s, 1.2, y + 0.35, 2.0, 0.3, rule_id, size=10, color=LIGHT_GRAY, font_name="Consolas")

    add_text(s, 3.5, y, 3.0, 0.35, "Ne yapiyor:", size=11, bold=True, color=color)
    add_text(s, 3.5, y + 0.3, 3.0, 0.3, what, size=12, color=GRAY)
    add_text(s, 3.5, y + 0.6, 3.0, 0.3, "Neden: " + why, size=11, color=LIGHT_GRAY)
    add_text(s, 3.5, y + 0.9, 3.0, 0.3, "Sonuc: " + result, size=11, bold=True, color=color)

    add_rect(s, 8.5, y, 4.0, 1.5, RGBColor(0xF0, 0xF0, 0xF0), radius=True)
    add_text(s, 8.8, y + 0.15, 3.5, 1.2, config, size=11, color=GRAY, font_name="Consolas")


# SLIDE 13 — WAF: Nasil Yaptik
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, WHITE)
slide_header(s, "WAF: Nasil Yaptik?", "Azure Portal uzerinden adim adim")

waf_steps = [
    ("1", "WAF Policy Olustur", "Portal → WAF policies\nagentfactory-waf\nFront Door tier", ORANGE),
    ("2", "Custom Rule Ekle", "Custom rules sekmesi\nHer kural tek tek\ntanimlandi", ORANGE),
    ("3", "Front Door'a Bagla", "Security policies → Add\nWAF'i FD endpoint'ine\nbagla", TEAL),
    ("4", "Detection Mode", "Policy settings\nDetection mode sec\nOnce logla, sonra engelle", BLUE),
    ("5", "Test Et", "Disaridan istek at\nLog'lari kontrol et\nKurallar calisiyor mu?", GREEN),
]

for i, (num, title, desc, color) in enumerate(waf_steps):
    x = 0.3 + i * 2.55
    add_rect(s, x, 2.5, 2.3, 1.8, color, f"{num}. {title}", WHITE, 12, True, radius=True)
    add_text(s, x + 0.1, 3.5, 2.1, 1.2, desc, size=11, color=WHITE, align=PP_ALIGN.CENTER)
    if i < 4:
        add_arrow(s, x + 2.3, 3.2)

# Onemli not
add_rect(s, 0.8, 5.2, 11.7, 1.8, RGBColor(0xFE, 0xF7, 0xED), radius=True)
add_text(s, 1.2, 5.3, 10.9, 0.4, "Detection vs Prevention Mode", size=16, bold=True, color=ORANGE)
add_multiline(s, 1.2, 5.8, 5.0, 1.1, [
    "Detection: Kurallara uyan istekleri loglar ama engellemez.",
    "   → Su an biz buradayiz. Test asamasi.",
    "",
    "Prevention: Kurallara uyan istekleri gercekten engeller.",
    "   → Test tamamlaninca gecirilecek.",
], size=12, color=GRAY)
add_multiline(s, 7.5, 5.8, 4.5, 1.1, [
    "Neden once Detection?",
    "   → False positive riski var",
    "   → Normal trafik yanlis engellenebilir",
    "   → Once loglara bakip kurallari ayarlayip",
    "   → Sonra Prevention'a gecmek guvenli",
], size=12, color=GRAY)


# ════════════════════════════════════════════════════════
# SECTION: Origin Locking
# ════════════════════════════════════════════════════════
section_slide("Origin Locking", "Direkt Erisim Engeli — 403 Forbidden")

# SLIDE 15 — Origin Locking Detay
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, WHITE)
slide_header(s, "Origin Locking: Ne Yaptik?", "App Service'e sadece Front Door uzerinden erisim")

# Neden gerekli
add_rect(s, 0.8, 2.0, 5.8, 2.5, RGBColor(0xFE, 0xF2, 0xF2), radius=True)
add_text(s, 1.2, 2.2, 5.0, 0.4, "Neden Gerekli?", size=18, bold=True, color=RED)
add_multiline(s, 1.2, 2.7, 5.0, 1.5, [
    "WAF kurmak tek basina YETMEZ!",
    "",
    "Eger biri direkt App Service URL'ini biliyorsa:",
    "  agentfactory-api-*.azurewebsites.net",
    "→ WAF'i atlayarak backend'e erisebilir!",
    "→ Tum guvenlik kurallari bypass edilir!",
], size=13, color=GRAY)

# Nasil cozuldu
add_rect(s, 7.0, 2.0, 5.5, 2.5, RGBColor(0xF0, 0xFD, 0xF4), radius=True)
add_text(s, 7.4, 2.2, 4.7, 0.4, "Nasil Cozduk?", size=18, bold=True, color=GREEN)
add_multiline(s, 7.4, 2.7, 4.7, 1.5, [
    "App Service → Networking → Access Restrictions",
    "",
    "• AzureFrontDoor.Backend Service Tag ekledik",
    "   → Sadece Front Door IP'leri izinli",
    "• X-Azure-FDID header kontrolu",
    "   → Sadece BIZIM Front Door'dan gelen trafik",
    "• Unmatched rule: DENY (geri kalan engellenir)",
], size=13, color=GRAY)

# Sonuc
add_text(s, 0.8, 5.0, 11.7, 0.4, "Sonuc:", size=20, bold=True, color=BLACK)

add_rect(s, 0.8, 5.6, 5.8, 1.2, RGBColor(0xF0, 0xFD, 0xF4), radius=True)
add_text(s, 1.2, 5.7, 5.0, 0.3, "Front Door uzerinden:", size=14, bold=True, color=GREEN)
add_text(s, 1.2, 6.05, 5.0, 0.4, "agentfactory-*.azurefd.net  →  200 OK", size=13, color=GREEN, font_name="Consolas")

add_rect(s, 7.0, 5.6, 5.5, 1.2, RGBColor(0xFE, 0xF2, 0xF2), radius=True)
add_text(s, 7.4, 5.7, 4.7, 0.3, "Direkt erisim:", size=14, bold=True, color=RED)
add_text(s, 7.4, 6.05, 4.7, 0.4, "agentfactory-api-*.azurewebsites.net  →  403", size=13, color=RED, font_name="Consolas")


# ════════════════════════════════════════════════════════
# SECTION: CI/CD
# ════════════════════════════════════════════════════════
section_slide("CI/CD Pipeline", "Git Push → Otomatik Azure Deploy")

# SLIDE 17 — CI/CD Detay
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, WHITE)
slide_header(s, "CI/CD: Ne Yaptik?", "GitHub Actions ile otomatik deploy pipeline")

# Sol: Ne & Neden
add_rect(s, 0.8, 2.0, 5.8, 2.5, LIGHT_BG, radius=True)
add_text(s, 1.2, 2.2, 5.0, 0.4, "Ne Yaptik & Neden?", size=18, bold=True, color=BLACK)
add_multiline(s, 1.2, 2.7, 5.0, 1.8, [
    "GitHub'a kod push edildiginde uygulama",
    "otomatik olarak Azure'a deploy oluyor.",
    "",
    "• Her guncellemede manuel deploy yok",
    "• Hata olursa pipeline durur",
    "• Bozuk kod canliya cikmaz",
    "• 3-5 dakikada uretimde",
], size=13, color=GRAY)

# Sag: Workflow dosyasi
add_rect(s, 7.0, 2.0, 5.5, 2.5, RGBColor(0x1A, 0x1A, 0x2E), radius=True)
add_text(s, 7.4, 2.2, 4.7, 0.3, "Workflow Tetikleme", size=14, bold=True, color=WHITE)
add_multiline(s, 7.4, 2.6, 4.7, 1.8, [
    "on:",
    "  push:",
    "    branches:",
    "      - feature/agent-factory-mvp",
    "  workflow_dispatch:",
    "",
    "# Manuel tetikleme de mumkun",
], size=12, color=RGBColor(0xAA, 0xAA, 0xAA), font_name="Consolas")

# Pipeline adimlari
pipeline = [
    ("Git Push", "Branch'e\npush", BLACK),
    ("Checkout", "Kodu\nindir", BLACK),
    ("Node.js\nBuild", "React\nnpm ci\nnpm build", BLUE),
    ("Python\nSetup", "venv olustur\npip install", GREEN),
    ("Artifact\nUpload", "Build ciktisi\npaketle", BLACK),
    ("Azure\nDeploy", "App Service'e\nyukle", TEAL),
]

for i, (title, desc, color) in enumerate(pipeline):
    x = 0.3 + i * 2.15
    add_rect(s, x, 5.0, 1.9, 1.2, color, title, WHITE, 11, True, radius=True)
    add_text(s, x, 6.3, 1.9, 0.8, desc, size=10, color=GRAY, align=PP_ALIGN.CENTER)
    if i < 5:
        add_arrow(s, x + 1.9, 5.4, 0.25, 0.2)


# ════════════════════════════════════════════════════════
# SECTION: Agent Factory Uygulama
# ════════════════════════════════════════════════════════
section_slide("Agent Factory Uygulamasi", "Dogal Dil → AI Agent")

# SLIDE 19 — Agent Olusturma Akisi
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, WHITE)
slide_header(s, "Agent Olusturma Akisi", "Kullanici deneyimi adim adim")

flow_steps = [
    ("1. Tanimla", "Kullanici dogal dilde\nagent'in ne yapacagini yazar\n\nOrn: 'Excel yukleyip hata\nkodlarini bulsun'", BLUE),
    ("2. Analiz", "GPT-4o aciklamayi analiz eder\n\n→ Isim onerisi\n→ Amac cikartimi\n→ Arac/veri kaynagi tespiti", BLUE),
    ("3. Wizard", "6 adimli sihirbaz:\n\n→ Hedef kitle\n→ Ton (resmi/samimi)\n→ Cikti formati\n→ Kapsam\n→ PII\n→ Onay", TEAL),
    ("4. Build", "Sistem prompt olusturulur\nTool tanimlari eklenir\nMetadata hazirlanir\n\nOtomatik, LLM destekli", TEAL),
    ("5. Onizleme", "Agent tanimi gozden gecirilir\nTalimatlar okunur\nEkosistem grafiginde\nkonum gosterilir", GREEN),
    ("6. Deploy", "Tek tikla Azure AI\nFoundry'ye deploy\n\nAgent hemen kullanima\nhazir", GREEN),
]

for i, (title, desc, color) in enumerate(flow_steps):
    x = 0.3 + (i % 3) * 4.3
    y = 2.0 + (i // 3) * 2.8
    add_rect(s, x, y, 3.9, 2.4, color, radius=True)
    add_text(s, x + 0.3, y + 0.2, 3.3, 0.4, title, size=16, bold=True, color=WHITE)
    add_text(s, x + 0.3, y + 0.65, 3.3, 1.6, desc, size=11, color=WHITE)


# SLIDE 20 — Foundry Senkronizasyon
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, WHITE)
slide_header(s, "Azure AI Foundry Senkronizasyon", "Tum islemler local + Azure senkronize calisiyor")

ops = [
    ("OLUSTUR", GREEN, "create_agent()",
     "1. Agent spec dosyasi olusturulur\n2. Foundry API'ye create_agent cagrisi\n3. Version olusturulur\n4. Agent listesine eklenir\n5. Lokal + Azure senkron"),
    ("DUZENLE", BLUE, "update_agent()",
     "1. Lokal definition guncellenir\n2. Arka plan thread baslatilir\n3. Foundry'de create_version() cagirilir\n4. Yeni versiyon olusur\n5. UI: 'Azure sync arka planda'"),
    ("SIL", RED, "delete_agent()",
     "1. Foundry'den agent silinir\n2. Lokal agent JSON silinir\n3. Spec dosyasi silinir\n4. Turkce isim normalizasyonu\n5. UI: 'Local + Azure silindi'"),
]

for i, (title, color, func, desc) in enumerate(ops):
    x = 0.5 + i * 4.2
    add_rect(s, x, 2.0, 3.8, 0.7, color, title, WHITE, 16, True, radius=True)
    add_text(s, x + 0.3, 2.85, 3.2, 0.3, func, size=12, color=LIGHT_GRAY, font_name="Consolas")
    add_text(s, x + 0.3, 3.3, 3.2, 3.0, desc, size=12, color=GRAY)

# Turkce karakter notu
add_rect(s, 0.8, 6.0, 11.7, 1.0, RGBColor(0xFF, 0xF7, 0xED), radius=True)
add_text(s, 1.2, 6.1, 10.9, 0.3, "Turkce Karakter Normalizasyonu", size=14, bold=True, color=ORANGE)
add_text(s, 1.2, 6.4, 10.9, 0.4,
         "Azure Foundry Turkce karakterleri desteklemiyor.  'Satis Rapor Asistani' → 'Satis-Rapor-Asistani'  |  Silme/guncelleme her iki isimle eslestirilir.",
         size=12, color=GRAY)


# ════════════════════════════════════════════════════════
# SLIDE 21 — Ne Yapicaz? (Yol Haritasi)
# ════════════════════════════════════════════════════════
section_slide("Ne Yapicaz?", "Sonraki Adimlar & Yol Haritasi")

s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, WHITE)
slide_header(s, "Yol Haritasi", "Su an neredeyiz, nereye gidiyoruz")

# Faz 1 — Tamamlandi
add_rect(s, 0.5, 2.0, 3.9, 5.0, GREEN, radius=True)
add_text(s, 0.8, 2.1, 3.3, 0.5, "Faz 1 — MVP (Tamamlandi)", size=15, bold=True, color=WHITE)
add_multiline(s, 0.8, 2.65, 3.3, 4.0, [
    "✓ Dogal dil ile agent olusturma",
    "✓ Azure AI Foundry entegrasyonu",
    "✓ 6 adimli wizard",
    "✓ Streaming chat arayuzu",
    "✓ Agent CRUD (olustur/duzenle/sil)",
    "✓ App Service deploy",
    "✓ Front Door + CDN",
    "✓ WAF custom rules (3 kural)",
    "✓ Origin locking (403)",
    "✓ CI/CD pipeline",
    "✓ Ekosistem gorsellestirme",
], size=12, color=WHITE, spacing=Pt(3))

# Faz 2 — Guvenlik
add_rect(s, 4.7, 2.0, 3.9, 5.0, BLUE, radius=True)
add_text(s, 5.0, 2.1, 3.3, 0.5, "Faz 2 — Guvenlik & Auth", size=15, bold=True, color=WHITE)
add_multiline(s, 5.0, 2.65, 3.3, 4.0, [
    "○ IFS entegrasyonu (kurumsal login)",
    "○ JWT tabanli kimlik dogrulama",
    "○ Departman bazli yetkilendirme",
    "○ WAF → Prevention mode gecisi",
    "○ WAF Premium + OWASP kurallari",
    "○ Bot Manager",
    "○ Custom domain + SSL sertifikasi",
    "○ RBAC (rol bazli erisim)",
    "○ Audit logging",
], size=12, color=WHITE, spacing=Pt(3))

# Faz 3 — Genisleme
add_rect(s, 8.9, 2.0, 3.9, 5.0, TEAL, radius=True)
add_text(s, 9.2, 2.1, 3.3, 0.5, "Faz 3 — Genisleme", size=15, bold=True, color=WHITE)
add_multiline(s, 9.2, 2.65, 3.3, 4.0, [
    "○ Tool/Function calling",
    "   (gercek servis baglantilari)",
    "○ MCP protokolu entegrasyonu",
    "○ Konusma gecmisi (veritabani)",
    "○ Agent analitik dashboard",
    "○ Multi-tenant mimari",
    "○ Agent marketplace",
    "○ Otomatik test pipeline",
    "○ Agent versiyonlama UI",
], size=12, color=WHITE, spacing=Pt(3))


# ════════════════════════════════════════════════════════
# SECTION: Faz 2 Detay — Governance & Yetkilendirme
# ════════════════════════════════════════════════════════
section_slide("Faz 2: Governance & Yetkilendirme", "Authentication, Authorization, Agent Governance, Audit")

# ── SLIDE: Authentication — IFS + JWT ──
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, WHITE)
slide_header(s, "Authentication: Kim Bu Kullanici?", "IFS entegrasyonu + JWT tabanli kimlik dogrulama")

# Akis diyagrami
flow_boxes = [
    (0.5, "Kullanici", "IFS Login\nekranina gider", BLUE),
    (3.0, "IFS Sistemi", "Kurumsal kimlik\ndogrulama", BLACK),
    (5.5, "Agent Factory\nBackend", "IFS token dogrular\nJWT uretir", TEAL),
    (8.0, "JWT Token", "user_id, department\nrole, permissions", GREEN),
    (10.5, "Her API\nIstegi", "JWT header'da\ngonderilir", PURPLE),
]
for x, label, desc, color in flow_boxes:
    add_rect(s, x, 2.5, 2.2, 1.2, color, label, WHITE, 13, True, radius=True)
    add_text(s, x, 3.9, 2.2, 0.7, desc, size=11, color=GRAY, align=PP_ALIGN.CENTER)

for x in [2.7, 5.2, 7.7, 10.2]:
    add_arrow(s, x, 2.95)

# Detaylar
add_rect(s, 0.8, 5.0, 5.8, 2.2, LIGHT_BG, radius=True)
add_text(s, 1.2, 5.1, 5.0, 0.4, "Nasil Yapilacak?", size=16, bold=True, color=BLACK)
add_multiline(s, 1.2, 5.5, 5.0, 1.5, [
    "• /auth/login endpoint'i olusturulacak",
    "• IFS API'sine token gonderilip dogrulanacak",
    "• Basarili ise JWT uretilecek (HS256/RS256)",
    "• JWT icinde: user_id, department, role, exp",
    "• Her endpoint'e @require_auth decorator",
    "• Token suresi: 8 saat (is gunu)",
], size=12, color=GRAY)

add_rect(s, 7.0, 5.0, 5.5, 2.2, LIGHT_BG, radius=True)
add_text(s, 7.4, 5.1, 4.7, 0.4, "Neden IFS + JWT?", size=16, bold=True, color=BLACK)
add_multiline(s, 7.4, 5.5, 4.7, 1.5, [
    "• Kullanicilar zaten IFS'i biliyior — yeni sifre yok",
    "• Tek kaynak (single source of truth)",
    "• JWT stateless — DB sorgusu gerekmez",
    "• Her istekte kim oldugu biliniyor",
    "• Departman bilgisi otomatik geliyor",
    "• Session yonetimi basit ve guvenli",
], size=12, color=GRAY)


# ── SLIDE: Authorization — RBAC ──
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, WHITE)
slide_header(s, "Authorization: Ne Yapabilir?", "3 katmanli RBAC (Role-Based Access Control)")

# Rol tablosu
roles = [
    ("Viewer", RGBColor(0xE0, 0xE0, 0xE0), BLACK, ["-", "-", "-", "-", "Kendi dept.", "-"]),
    ("Creator", BLUE, WHITE, ["Kendi dept.", "Kendi agent'lari", "Kendi agent'lari", "-", "Kendi dept.", "-"]),
    ("Deployer", TEAL, WHITE, ["Kendi dept.", "Kendi dept.", "Kendi dept.", "Onaylananlar", "Hepsi", "-"]),
    ("Admin", BLACK, WHITE, ["Hepsi", "Hepsi", "Hepsi", "Hepsi", "Hepsi", "Tam erisim"]),
]

headers = ["Rol", "Agent Olustur", "Agent Duzenle", "Agent Sil", "Deploy", "Chat", "Admin Panel"]
col_widths = [1.5, 1.7, 1.7, 1.7, 1.7, 1.5, 1.7]
start_x = 0.5

# Header row
x = start_x
for j, (h, w) in enumerate(zip(headers, col_widths)):
    add_rect(s, x, 2.2, w, 0.5, BLACK, h, WHITE, 11, True)
    x += w

# Data rows
for i, (role, bg, tc, perms) in enumerate(roles):
    x = start_x
    y = 2.7 + i * 0.55
    add_rect(s, x, y, col_widths[0], 0.55, bg, role, tc, 12, True)
    x += col_widths[0]
    for j, (perm, w) in enumerate(zip(perms, col_widths[1:])):
        color = RGBColor(0xF8, 0xF8, 0xF8) if i % 2 == 0 else WHITE
        add_rect(s, x, y, w, 0.55, color, perm, GRAY, 10, False)
        x += w

# Departman izolasyonu
add_rect(s, 0.8, 5.2, 5.8, 2.2, LIGHT_BG, radius=True)
add_text(s, 1.2, 5.3, 5.0, 0.4, "Departman Bazli Izolasyon", size=16, bold=True, color=BLACK)
add_multiline(s, 1.2, 5.7, 5.0, 1.5, [
    "• Her agent bir departmana ait",
    "• Muhasebe sadece muhasebe agent'larini gorur",
    "• IT departmani hepsini gorebilir",
    "• Agent metadata'sinda department alani",
    "• Middleware'de departman filtresi",
], size=12, color=GRAY)

add_rect(s, 7.0, 5.2, 5.5, 2.2, LIGHT_BG, radius=True)
add_text(s, 7.4, 5.3, 4.7, 0.4, "Nasil Uygulanacak?", size=16, bold=True, color=BLACK)
add_multiline(s, 7.4, 5.7, 4.7, 1.5, [
    "• DB'de users, roles, permissions tablolari",
    "• JWT'den role + department okunur",
    "• Her API endpoint'te yetki kontrolu",
    "• UI'da rol bazli buton goster/gizle",
    "• Agent listesi departmana gore filtrelenir",
], size=12, color=GRAY)


# ── SLIDE: Agent Governance — Onay Mekanizmasi ──
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, WHITE)
slide_header(s, "Agent Governance: Onay Mekanizmasi", "Agent'larin kendisi de yonetilmeli — kim ne olusturabilir?")

# Onay akisi
approval_steps = [
    ("Creator\nAgent Olusturur", BLUE),
    ("Onay Bekliyor\nstatusu", ORANGE),
    ("Deployer/Admin\nInceler", TEAL),
    ("Onay → Deploy\nRed → Geri Doner", GREEN),
]

for i, (label, color) in enumerate(approval_steps):
    x = 0.5 + i * 3.3
    add_rect(s, x, 2.3, 2.8, 1.3, color, label, WHITE, 13, True, radius=True)
    if i < 3:
        add_arrow(s, x + 2.8, 2.75, 0.5, 0.25)

add_text(s, 0.8, 3.9, 11, 0.4,
         "Neden: Herkes kafasina gore agent deploy edemesin. Ozellikle PII veya finansal veri iceren agent'lar icin onay sart.",
         size=13, bold=True, color=ORANGE)

# Agent Policy'leri
add_rect(s, 0.8, 4.6, 11.7, 2.6, LIGHT_BG, radius=True)
add_text(s, 1.2, 4.7, 10.9, 0.4, "Agent Capability Sinirlari (Zorunlu Policy'ler)", size=18, bold=True, color=BLACK)

policies = [
    ("no_pii_access", "Agent PII veriye erisemez", "Kisisel veri korumasi — KVKK uyumlulugu"),
    ("no_financial_advice", "Finansal tavsiye veremez", "Yasal sorumluluk riski — sadece bilgilendirme"),
    ("read_only", "Sadece rapor uretir, aksiyon almaz", "Yanlislikla veri degistirme onlenir"),
    ("department_scoped", "Sadece kendi departman verisine erisir", "Departmanlar arasi veri sizintisi engellenir"),
    ("tool_whitelist", "Sadece izin verilen tool'lari kullanabilir", "Yetkisiz servis erisimi onlenir"),
]

for i, (policy_id, desc, reason) in enumerate(policies):
    y = 5.25 + i * 0.38
    add_text(s, 1.5, y, 2.2, 0.35, policy_id, size=11, color=PURPLE, font_name="Consolas")
    add_text(s, 3.8, y, 3.5, 0.35, desc, size=11, color=BLACK)
    add_text(s, 7.5, y, 4.5, 0.35, reason, size=11, color=LIGHT_GRAY)

# Not
add_text(s, 0.8, 7.0, 11.7, 0.3,
         "Bu policy'ler agent'in system prompt'una zorla enjekte edilir — creator degistiremez.",
         size=12, bold=True, color=RED)


# ── SLIDE: Tool Erisim Kontrolu ──
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, WHITE)
slide_header(s, "Tool/Servis Erisim Kontrolu", "Ilerde tool calling geldiginde — hangi agent neye erisebilir?")

# Ornek: Satis Raporu agent'i
add_rect(s, 0.8, 2.2, 3.5, 1.0, BLUE, "Agent: Satis Raporu", WHITE, 14, True, radius=True)

# Izinli tool'lar
add_text(s, 0.8, 3.5, 5.5, 0.4, "Izinli Tool'lar:", size=16, bold=True, color=GREEN)
allowed = [
    ("Excel Okuma", "Dosya yukle, veri parse et"),
    ("Rapor Yazma", "Ozet rapor uret, PDF ciktisi"),
    ("Veritabani (READ)", "Satis tablosundan veri cek"),
]
for i, (tool, desc) in enumerate(allowed):
    y = 4.0 + i * 0.5
    add_rect(s, 1.0, y, 0.15, 0.35, GREEN)
    add_text(s, 1.4, y, 2.0, 0.35, tool, size=13, bold=True, color=BLACK)
    add_text(s, 3.5, y, 3.0, 0.35, desc, size=12, color=GRAY)

# Yasakli tool'lar
add_text(s, 7.0, 3.5, 5.5, 0.4, "Yasakli Tool'lar:", size=16, bold=True, color=RED)
blocked = [
    ("Email Gonderme", "Yetkisiz iletisim riski"),
    ("DB Yazma/Silme", "Veri butunlugu korunmali"),
    ("Dis API Cagrisi", "Veri sizintisi riski"),
    ("Dosya Sistemi", "Sunucu guvenligi"),
]
for i, (tool, reason) in enumerate(blocked):
    y = 4.0 + i * 0.5
    add_rect(s, 7.2, y, 0.15, 0.35, RED)
    add_text(s, 7.6, y, 2.0, 0.35, tool, size=13, bold=True, color=BLACK)
    add_text(s, 9.8, y, 3.0, 0.35, reason, size=12, color=GRAY)

# Nasil calisacak
add_rect(s, 0.8, 6.0, 11.7, 1.2, LIGHT_BG, radius=True)
add_text(s, 1.2, 6.1, 10.9, 0.3, "Nasil Calisacak?", size=15, bold=True, color=BLACK)
add_multiline(s, 1.2, 6.4, 10.9, 0.7, [
    "• Her tool bir izin seviyesi gerektirir (low / medium / high / critical)",
    "• Agent olusturulurken izin verilen tool'lar belirlenir → tool_whitelist policy'si",
    "• Runtime'da agent bir tool cagirdiginda → izin kontrolu yapilir → yetkisizse engellenir ve loglanir",
], size=12, color=GRAY)


# ── SLIDE: Audit & Compliance ──
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, WHITE)
slide_header(s, "Audit & Compliance", "Kim ne yapti? Her sey kayit altinda.")

# Log turleri
log_types = [
    ("Auth Log", "Kim login oldu, ne zaman, nereden (IP),\nbasarili/basarisiz girisler", BLUE,
     "• Basarisiz giris denemeleri tespit\n• Supheli erisim alarmi"),
    ("Agent Log", "Kim hangi agent'i olusturdu,\nduzenledi, sildi — ne zaman", TEAL,
     "• Degisiklik gecmisi takibi\n• Sorumluluk belirleme"),
    ("Deploy Log", "Kim deploy etti, onay veren kim,\nhangi versiyon, basarili mi", GREEN,
     "• Deploy gecmisi\n• Rollback icin versiyon takibi"),
    ("Chat Log", "Kim hangi agent ile ne konustu,\nne sordu, ne cevap aldi", PURPLE,
     "• Kullanim analizi\n• Yanlis/zararli cevap tespiti"),
    ("Policy Log", "Hangi policy tetiklendi,\nne engellendi, kac kez", ORANGE,
     "• Kural etkinligi olcumu\n• Fine-tuning icin veri"),
]

for i, (title, desc, color, usage) in enumerate(log_types):
    y = 1.9 + i * 1.1
    add_rect(s, 0.8, y, 0.15, 0.85, color)
    add_text(s, 1.2, y, 2.0, 0.35, title, size=14, bold=True, color=color)
    add_text(s, 3.3, y, 4.2, 0.8, desc, size=11, color=GRAY)
    add_text(s, 7.8, y, 4.8, 0.8, usage, size=11, color=LIGHT_GRAY)

# Nereye gidecek
add_rect(s, 0.8, 7.0, 11.7, 0.0, BLACK)
add_text(s, 0.8, 6.6, 11.7, 0.3,
         "Loglar → Azure Monitor / Log Analytics → Admin Dashboard'da gorsellestirilir",
         size=13, bold=True, color=BLACK)


# ── SLIDE: Faz 2 Uygulama Plani ──
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, WHITE)
slide_header(s, "Faz 2: Uygulama Plani", "Adim adim ne yapilacak")

impl_steps = [
    ("Adim 1", "Authentication", "~1 Hafta", BLUE, [
        "IFS login endpoint'i",
        "JWT uretimi (HS256)",
        "@require_auth middleware",
        "Login UI sayfasi",
        "Token yenileme mekanizmasi",
    ]),
    ("Adim 2", "RBAC", "~1 Hafta", TEAL, [
        "users, roles, permissions tablolari",
        "Middleware'de rol kontrolu",
        "UI'da rol bazli goster/gizle",
        "Departman filtresi",
        "Admin kullanici yonetim ekrani",
    ]),
    ("Adim 3", "Agent Governance", "~2 Hafta", PURPLE, [
        "Onay workflow (olustur → onayla → deploy)",
        "Policy engine (zorunlu kurallar)",
        "Tool whitelist mekanizmasi",
        "Departman izolasyonu",
        "Agent statu yonetimi",
    ]),
    ("Adim 4", "Audit", "~1 Hafta", ORANGE, [
        "Tum islemler loglanir",
        "Admin panelinde log goruntulemne",
        "Azure Monitor entegrasyonu",
        "Basit dashboard/raporlar",
        "Alert kurallari",
    ]),
]

for i, (step, title, duration, color, items) in enumerate(impl_steps):
    x = 0.3 + i * 3.2
    add_rect(s, x, 2.0, 2.9, 0.6, color, f"{step}: {title}", WHITE, 13, True, radius=True)
    add_text(s, x + 0.1, 2.7, 2.7, 0.3, duration, size=12, bold=True, color=color, align=PP_ALIGN.CENTER)
    add_multiline(s, x + 0.2, 3.1, 2.5, 3.5, [f"• {item}" for item in items], size=11, color=GRAY, spacing=Pt(3))

# Toplam sure
add_rect(s, 0.8, 6.2, 11.7, 1.0, RGBColor(0xF0, 0xF0, 0xF0), radius=True)
add_text(s, 1.2, 6.3, 10.9, 0.3, "Toplam Tahmini Sure: ~5 Hafta", size=18, bold=True, color=BLACK)
add_text(s, 1.2, 6.7, 10.9, 0.3,
         "Her adim bagimsiz deploy edilebilir — incremental yaklasim. Adim 1 tamamlanmadan Adim 2'ye gecilemez (auth gerekli).",
         size=13, color=GRAY)


# ════════════════════════════════════════════════════════
# Kapanış
# ════════════════════════════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, BLACK)
add_text(s, 1.5, 2.0, 10, 1.0, "Sorular?", size=52, bold=True, color=WHITE)
add_text(s, 1.5, 3.3, 10, 0.6, "Agent Factory MVP — Hazir ve Calisiyor", size=24, color=RGBColor(0x88, 0x88, 0x88))

add_text(s, 1.5, 4.8, 10, 0.4, "Ne Yaptik:", size=16, bold=True, color=RGBColor(0xAA, 0xAA, 0xAA))
add_text(s, 1.5, 5.3, 10, 0.8,
         "App Service  →  Front Door  →  WAF  →  Origin Lock  →  CI/CD  →  Agent Factory",
         size=18, color=RGBColor(0x66, 0x66, 0x66))

add_text(s, 1.5, 6.5, 10, 0.4, "Demo:  agentfactory-api.azurewebsites.net", size=14, color=RGBColor(0x55, 0x55, 0x55), font_name="Consolas")


# ── Kaydet ──
output_path = "sunum/AgentFactory_Sunum.pptx"
prs.save(output_path)
print(f"Sunum olusturuldu: {output_path}")
print(f"Toplam slide sayisi: {len(prs.slides)}")
