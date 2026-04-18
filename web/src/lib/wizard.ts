export interface WizardChoice {
  label: string;
  value: string;
  description?: string;
}

export interface WizardStep {
  id: string;
  title: string;
  description: string;
  choices: WizardChoice[];
  allowCustom?: boolean;
  required?: boolean;
}

export const WIZARD_STEPS: WizardStep[] = [
  {
    id: "audience",
    title: "Kimler kullanacak?",
    description: "Bu agent'ı hangi ekip veya departman kullanacak?",
    choices: [
      { label: "Müşteri Hizmetleri", value: "musteri_hizmetleri", description: "Çağrı merkezi, destek ekibi" },
      { label: "Yönetim", value: "yonetim", description: "Üst düzey yöneticiler, karar vericiler" },
      { label: "IT Ekibi", value: "it", description: "Yazılım, altyapı, teknik destek" },
      { label: "Finans", value: "finans", description: "Muhasebe, bütçe, mali işler" },
      { label: "Operasyon", value: "operasyon", description: "Üretim, lojistik, saha ekipleri" },
      { label: "İnsan Kaynakları", value: "ik", description: "İK, personel işlemleri" },
      { label: "Tüm Şirket", value: "tum_sirket", description: "Herkese açık" },
    ],
    allowCustom: true,
  },
  {
    id: "tone",
    title: "Agent nasıl konuşsun?",
    description: "Agent'ın iletişim tarzını seçin.",
    choices: [
      { label: "Resmi / Kurumsal", value: "formal", description: "Profesyonel dil, kısa ve net cevaplar" },
      { label: "Samimi / Yardımcı", value: "friendly", description: "Sıcak, anlaşılır, rehberlik eden" },
      { label: "Teknik / Detaylı", value: "technical", description: "Uzman seviyesi, detaylı açıklamalar" },
      { label: "Kısa / Özet Odaklı", value: "concise", description: "Minimum kelime, maksimum bilgi" },
    ],
  },
  {
    id: "output_format",
    title: "Çıktıları nasıl versin?",
    description: "Agent'ın cevaplarını hangi formatta sunmasını istiyorsunuz?",
    choices: [
      { label: "Tablo / Yapılandırılmış", value: "structured", description: "Tablolar, listeler, maddeler halinde" },
      { label: "Rapor / Detaylı Metin", value: "report", description: "Uzun, açıklayıcı paragraflar" },
      { label: "Kısa Özet", value: "summary", description: "2-3 cümlelik özetler" },
      { label: "Adım Adım Rehber", value: "step_by_step", description: "Numaralandırılmış adımlar halinde" },
      { label: "Karışık / Duruma Göre", value: "adaptive", description: "Soruya göre uygun format" },
    ],
  },
  {
    id: "pii",
    title: "Hassas veri içeriyor mu?",
    description: "Bu agent kişisel verilere (isim, TC, e-posta, telefon, adres vb.) erişecek mi?",
    choices: [
      { label: "Evet, hassas veri var", value: "true", description: "Müşteri/çalışan kişisel bilgileri işleniyor" },
      { label: "Hayır", value: "false", description: "Kişisel veri yok veya anonimleştirilmiş" },
      { label: "Emin değilim", value: "maybe", description: "Sistem otomatik belirlesin" },
    ],
  },
  {
    id: "approval",
    title: "İnsan onayı gerekli mi?",
    description: "Agent'ın ürettiği sonuçlar için bir kişinin onay vermesi gerekiyor mu?",
    choices: [
      { label: "Evet, onay gerekli", value: "true", description: "Sonuçlar aksiyona dönüşmeden önce onaylanmalı" },
      { label: "Hayır, sadece bilgi/rapor", value: "false", description: "Sadece raporlama, aksiyon yok" },
      { label: "Bazen gerekebilir", value: "conditional", description: "Bazı durumlarda onay gerekli" },
    ],
  },
  {
    id: "scope",
    title: "Agent ne YAPMAMALI?",
    description: "Agent'ın kesinlikle yapmaması gereken şeyler neler?",
    choices: [
      { label: "Finansal tavsiye vermemeli", value: "no_financial_advice", description: "Yatırım, kredi, mali karar önerisi yasak" },
      { label: "Kişisel bilgi paylaşmamalı", value: "no_pii_sharing", description: "Kişisel veri dışarı çıkmamalı" },
      { label: "Aksiyon almamalı, sadece raporlamalı", value: "report_only", description: "Hiçbir sisteme yazma/değiştirme yapmasın" },
      { label: "Kapsam dışı sorulara cevap vermemeli", value: "strict_scope", description: "Sadece görevi dahilinde çalışsın" },
      { label: "Özel bir kısıtlama yok", value: "no_restriction", description: "Genel kurallar yeterli" },
    ],
    allowCustom: true,
  },
  {
    id: "example_scenario",
    title: "Örnek bir kullanım senaryosu",
    description: "Agent'ın tipik bir kullanım senaryosunu yazın. Örn: 'Kullanıcı Excel yükler, agent hata kodlarını bulur.'",
    choices: [
      { label: "Şimdilik geçmek istiyorum", value: "skip", description: "Örnek senaryo vermeden devam et" },
    ],
    allowCustom: true,
  },
];
