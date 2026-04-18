export interface WizardChoice {
  label: string;
  value: string;
}

export interface WizardStep {
  id: string;
  title: string;
  choices: WizardChoice[];
}

export const WIZARD_STEPS: WizardStep[] = [
  {
    id: "audience",
    title: "Kimler kullanacak?",
    choices: [
      { label: "Müşteri Hizmetleri", value: "musteri_hizmetleri" },
      { label: "Yönetim", value: "yonetim" },
      { label: "IT", value: "it" },
      { label: "Finans", value: "finans" },
      { label: "Operasyon", value: "operasyon" },
      { label: "İnsan Kaynakları", value: "ik" },
      { label: "Tüm Şirket", value: "tum_sirket" },
    ],
  },
  {
    id: "tone",
    title: "Nasıl konuşsun?",
    choices: [
      { label: "Resmi", value: "formal" },
      { label: "Samimi", value: "friendly" },
      { label: "Teknik", value: "technical" },
      { label: "Özet", value: "concise" },
    ],
  },
  {
    id: "output_format",
    title: "Çıktı formatı",
    choices: [
      { label: "Yapılandırılmış", value: "structured" },
      { label: "Rapor", value: "report" },
      { label: "Kısa özet", value: "summary" },
      { label: "Adım adım", value: "step_by_step" },
      { label: "Duruma göre", value: "adaptive" },
    ],
  },
  {
    id: "pii",
    title: "Hassas veri var mı?",
    choices: [
      { label: "Evet", value: "true" },
      { label: "Hayır", value: "false" },
      { label: "Emin değilim", value: "maybe" },
    ],
  },
  {
    id: "approval",
    title: "İnsan onayı gerekli mi?",
    choices: [
      { label: "Evet", value: "true" },
      { label: "Hayır", value: "false" },
      { label: "Bazen", value: "conditional" },
    ],
  },
];
