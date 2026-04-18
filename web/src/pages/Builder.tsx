import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronRight,
  Loader2,
  Rocket,
  Sparkles,
  Wand2,
  X,
  AlertTriangle,
  Cpu,
  ShieldCheck,
  FileText,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input, Textarea } from "@/components/ui/input";
import { WIZARD_STEPS } from "@/lib/wizard";
import {
  api,
  streamBuild,
  type AnalyzeResult,
  type BuildPayload,
  type BuildResult,
  type PipelineStage,
} from "@/lib/api";
import { cn } from "@/lib/utils";

type Phase = "describe" | "analyzing" | "wizard" | "building" | "review";

export function BuilderPage() {
  const navigate = useNavigate();
  const [phase, setPhase] = useState<Phase>("describe");
  const [description, setDescription] = useState("");
  const [analyze, setAnalyze] = useState<AnalyzeResult | null>(null);
  const [stepIdx, setStepIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [customValues, setCustomValues] = useState<Record<string, string>>({});
  const [customInput, setCustomInput] = useState("");

  const [stages, setStages] = useState<PipelineStage[]>([]);
  const [buildResult, setBuildResult] = useState<BuildResult | null>(null);
  const [deploying, setDeploying] = useState(false);
  const [cancel, setCancel] = useState<(() => void) | null>(null);

  const step = WIZARD_STEPS[stepIdx];
  const totalSteps = WIZARD_STEPS.length;
  const progress = useMemo(() => {
    if (phase === "describe") return 0;
    if (phase === "analyzing") return 8;
    if (phase === "wizard") return 15 + Math.round((stepIdx / totalSteps) * 55);
    if (phase === "building") {
      const done = stages.filter((s) => s.status === "pass").length;
      return 75 + Math.round((done / Math.max(stages.length || 1, 1)) * 20);
    }
    if (phase === "review") return 100;
    return 0;
  }, [phase, stepIdx, totalSteps, stages]);

  async function handleAnalyze() {
    if (description.trim().length < 10) {
      toast.error("Lütfen en az birkaç cümlelik açıklama yazın");
      return;
    }
    setPhase("analyzing");
    try {
      const res = await api.analyze(description);
      setAnalyze(res);
      setPhase("wizard");
      setStepIdx(0);
      toast.success("Analiz tamamlandı — şimdi detayları tamamlayalım");
    } catch (e) {
      toast.error("Analiz başarısız: " + String(e));
      setPhase("describe");
    }
  }

  function pickAnswer(value: string) {
    setAnswers((a) => ({ ...a, [step.id]: value }));
    setCustomInput("");
    setTimeout(() => goNext(), 120);
  }

  function applyCustom() {
    const v = customInput.trim();
    if (!v) return;
    setCustomValues((c) => ({ ...c, [step.id]: v }));
    setAnswers((a) => ({ ...a, [step.id]: v }));
    setCustomInput("");
    setTimeout(() => goNext(), 120);
  }

  function goNext() {
    if (stepIdx < totalSteps - 1) {
      setStepIdx((i) => i + 1);
    } else {
      startBuild();
    }
  }
  function goBack() {
    if (stepIdx > 0) setStepIdx((i) => i - 1);
    else setPhase("describe");
  }

  function startBuild() {
    if (!analyze) return;
    setPhase("building");
    setStages([
      { name: "spec", status: "pending", data: {} },
      { name: "policy", status: "pending", data: {} },
      { name: "architecture", status: "pending", data: {} },
      { name: "scaffold", status: "pending", data: {} },
      { name: "review", status: "pending", data: {} },
    ]);

    const payload: BuildPayload = {
      description,
      name: analyze.name,
      purpose: analyze.purpose,
      audience: answers.audience ?? "tum_sirket",
      tone: answers.tone ?? "friendly",
      output_format: answers.output_format ?? "adaptive",
      scope: answers.scope ?? "no_restriction",
      pii: answers.pii ?? "maybe",
      approval: answers.approval ?? "conditional",
      example_scenario: answers.example_scenario ?? "skip",
      inferred_tools: analyze.inferred_tools,
      inferred_data_sources: analyze.inferred_data_sources,
      suggested_capabilities: analyze.suggested_capabilities,
      complexity_hints: analyze.complexity_hints as Record<string, unknown>,
    };

    const stop = streamBuild(payload, {
      onStage: (s) => {
        setStages((prev) => {
          const ix = prev.findIndex((x) => x.name === s.name);
          const next = {
            name: s.name,
            status: s.status as PipelineStage["status"],
            data: (s.data as Record<string, unknown>) ?? {},
          };
          if (ix >= 0) {
            const copy = [...prev];
            copy[ix] = next;
            return copy;
          }
          return [...prev, next];
        });
      },
      onResult: (r) => {
        setBuildResult(r);
      },
      onDone: () => {
        setPhase("review");
        toast.success("Agent hazır! İnceleyip deploy edebilirsiniz.");
      },
      onError: (e) => {
        toast.error("Build hatası: " + e);
        setPhase("wizard");
      },
    });
    setCancel(() => stop);
  }

  async function deploy() {
    if (!buildResult) return;
    setDeploying(true);
    try {
      const res = await api.deploy(buildResult.spec_id);
      if (res.success) {
        toast.success(res.mock ? "Mock agent oluşturuldu" : "Azure'a deploy edildi!");
        const agents = await api.agents();
        navigate(`/chat?agent=${encodeURIComponent(res.foundry_agent_id || "")}`);
        void agents;
      } else {
        toast.error("Deploy başarısız: " + (res.error ?? "bilinmeyen hata"));
      }
    } catch (e) {
      toast.error("Deploy hatası: " + String(e));
    } finally {
      setDeploying(false);
    }
  }

  function reset() {
    cancel?.();
    setPhase("describe");
    setDescription("");
    setAnalyze(null);
    setStepIdx(0);
    setAnswers({});
    setCustomValues({});
    setStages([]);
    setBuildResult(null);
  }

  return (
    <div className="max-w-6xl mx-auto p-4 md:p-8 space-y-6">
      {/* Progress rail */}
      <div className="sticky top-14 z-20 -mx-4 md:-mx-8 px-4 md:px-8 py-3 bg-background/80 backdrop-blur-xl border-b border-border/50">
        <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
          <span className="flex items-center gap-2">
            <Sparkles className="h-3.5 w-3.5 text-primary" />
            Agent Oluşturma
          </span>
          <span className="font-mono">{progress}%</span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-primary via-primary to-accent"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ type: "spring", stiffness: 120, damping: 20 }}
          />
        </div>
      </div>

      <AnimatePresence mode="wait">
        {phase === "describe" && (
          <motion.div
            key="describe"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="space-y-6"
          >
            <Card className="overflow-hidden border-primary/20 bg-gradient-to-br from-card via-card to-primary/5">
              <CardHeader className="pb-4">
                <div className="flex items-center gap-2">
                  <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
                    <Wand2 className="h-4 w-4 text-white" />
                  </div>
                  <div>
                    <CardTitle>Ne yapmasını istiyorsunuz?</CardTitle>
                    <CardDescription>
                      Doğal dilde anlatın — sistem analiz etsin, öneriler sunsun.
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <Textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Örn: Müşteri destek ekibi Excel dosyası yüklesin, agent hata kodlarını bulup sınıflandırsın ve özet rapor çıkartsın. Ayrıca SAP'den müşteri bilgisi çekebilsin."
                  className="min-h-[140px] text-sm leading-relaxed"
                  autoFocus
                />
                <div className="flex items-center justify-between mt-4">
                  <div className="text-xs text-muted-foreground">
                    {description.length} karakter • minimum 10
                  </div>
                  <Button
                    variant="gradient"
                    size="lg"
                    onClick={handleAnalyze}
                    disabled={description.trim().length < 10}
                    className="group"
                  >
                    <Sparkles className="h-4 w-4" />
                    Analiz Et
                    <ChevronRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                  </Button>
                </div>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <Suggestion
                icon="📊"
                title="Excel hata analizi"
                desc="Kullanıcı Excel yükler, hata kodlarını bulur, rapor çıkarır."
                onClick={(v) => setDescription(v)}
              />
              <Suggestion
                icon="🧾"
                title="Harcama denetimi"
                desc="Gider formlarını politika kurallarına göre denetler."
                onClick={(v) => setDescription(v)}
              />
              <Suggestion
                icon="🎧"
                title="Destek triaj"
                desc="Müşteri ticket'larını önceliklendirir ve yönlendirir."
                onClick={(v) => setDescription(v)}
              />
            </div>
          </motion.div>
        )}

        {phase === "analyzing" && (
          <motion.div
            key="analyzing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center justify-center py-20"
          >
            <div className="relative h-16 w-16">
              <div className="absolute inset-0 rounded-full border-2 border-primary/20" />
              <div className="absolute inset-0 rounded-full border-2 border-primary border-t-transparent animate-spin" />
              <Sparkles className="absolute inset-0 m-auto h-6 w-6 text-primary" />
            </div>
            <p className="mt-6 text-sm text-muted-foreground">
              Açıklamanız analiz ediliyor...
            </p>
            <p className="mt-1 text-xs text-muted-foreground/70">
              LLM araçları ve veri kaynaklarını çıkarıyor
            </p>
          </motion.div>
        )}

        {phase === "wizard" && analyze && (
          <motion.div
            key="wizard"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="grid grid-cols-1 lg:grid-cols-3 gap-6"
          >
            <div className="lg:col-span-2 space-y-4">
              {/* Analysis summary */}
              <Card className="border-primary/20">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <CardTitle className="text-base flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-primary" />
                        {analyze.name}
                      </CardTitle>
                      <CardDescription className="mt-1">{analyze.purpose}</CardDescription>
                    </div>
                    <Badge variant="accent">{analyze.domain}</Badge>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex flex-wrap gap-1.5">
                    {analyze.inferred_tools.map((t) => (
                      <Badge key={t} variant="secondary" className="font-mono text-[10px]">
                        {t}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Current step */}
              <Card>
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                    <span className="font-mono">
                      {stepIdx + 1}/{totalSteps}
                    </span>
                    <span>•</span>
                    <span className="uppercase tracking-wide">{step.id}</span>
                  </div>
                  <CardTitle>{step.title}</CardTitle>
                  <CardDescription>{step.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={step.id}
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      transition={{ duration: 0.25 }}
                      className="space-y-2"
                    >
                      {step.choices.map((c) => {
                        const selected = answers[step.id] === c.value;
                        return (
                          <button
                            key={c.value}
                            onClick={() => pickAnswer(c.value)}
                            className={cn(
                              "w-full text-left rounded-lg border p-3 transition-all",
                              "hover:border-primary/40 hover:bg-accent/5",
                              selected
                                ? "border-primary bg-primary/10 shadow-sm"
                                : "border-border/60 bg-card/40"
                            )}
                          >
                            <div className="flex items-center gap-3">
                              <div
                                className={cn(
                                  "h-5 w-5 rounded-full border-2 flex items-center justify-center shrink-0 transition-all",
                                  selected
                                    ? "border-primary bg-primary"
                                    : "border-muted-foreground/40"
                                )}
                              >
                                {selected && <Check className="h-3 w-3 text-primary-foreground" />}
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="text-sm font-medium">{c.label}</div>
                                {c.description && (
                                  <div className="text-xs text-muted-foreground mt-0.5">
                                    {c.description}
                                  </div>
                                )}
                              </div>
                            </div>
                          </button>
                        );
                      })}

                      {step.allowCustom && (
                        <div className="pt-2 space-y-2 border-t border-border/50 mt-3">
                          <div className="text-xs text-muted-foreground">
                            veya kendi yanıtınızı yazın:
                          </div>
                          <div className="flex gap-2">
                            <Input
                              value={customInput}
                              onChange={(e) => setCustomInput(e.target.value)}
                              onKeyDown={(e) => e.key === "Enter" && applyCustom()}
                              placeholder="Özel yanıt..."
                            />
                            <Button onClick={applyCustom} disabled={!customInput.trim()}>
                              Uygula
                            </Button>
                          </div>
                          {customValues[step.id] && (
                            <div className="text-xs text-primary">
                              Özel yanıt: {customValues[step.id]}
                            </div>
                          )}
                        </div>
                      )}
                    </motion.div>
                  </AnimatePresence>
                </CardContent>
              </Card>

              <div className="flex items-center justify-between">
                <Button variant="outline" onClick={goBack}>
                  <ArrowLeft className="h-4 w-4" />
                  Geri
                </Button>
                <div className="flex items-center gap-2">
                  {WIZARD_STEPS.map((_, i) => (
                    <div
                      key={i}
                      className={cn(
                        "h-1.5 rounded-full transition-all",
                        i === stepIdx
                          ? "w-6 bg-primary"
                          : i < stepIdx
                          ? "w-3 bg-primary/50"
                          : "w-3 bg-muted"
                      )}
                    />
                  ))}
                </div>
                <Button
                  variant={stepIdx === totalSteps - 1 ? "gradient" : "default"}
                  onClick={goNext}
                  disabled={!answers[step.id] && step.required !== false}
                >
                  {stepIdx === totalSteps - 1 ? (
                    <>
                      <Rocket className="h-4 w-4" />
                      Oluştur
                    </>
                  ) : (
                    <>
                      İleri
                      <ArrowRight className="h-4 w-4" />
                    </>
                  )}
                </Button>
              </div>
            </div>

            <div className="space-y-4">
              <LivePreview
                analyze={analyze}
                answers={answers}
                description={description}
              />
            </div>
          </motion.div>
        )}

        {phase === "building" && (
          <motion.div
            key="building"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="space-y-6"
          >
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 text-primary animate-spin" />
                  <CardTitle>Pipeline çalışıyor</CardTitle>
                </div>
                <CardDescription>
                  Agent'ınız oluşturuluyor — her adım canlı olarak gözlemleniyor
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {stages.map((s, i) => (
                  <StageCard key={s.name} stage={s} index={i} />
                ))}
              </CardContent>
            </Card>
          </motion.div>
        )}

        {phase === "review" && buildResult && (
          <motion.div
            key="review"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            <Card className="border-success/30 bg-gradient-to-br from-success/5 to-transparent">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <div className="h-9 w-9 rounded-full bg-success/20 flex items-center justify-center">
                    <CheckCircle2 className="h-5 w-5 text-success" />
                  </div>
                  <div>
                    <CardTitle>Agent Hazır</CardTitle>
                    <CardDescription>
                      Tüm doğrulamalar başarıyla tamamlandı
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {stages.map((s) => (
                    <div
                      key={s.name}
                      className="rounded-lg border border-border/60 bg-card/60 p-3 text-center"
                    >
                      <div className="text-[10px] uppercase text-muted-foreground">{s.name}</div>
                      <div className="mt-1 flex items-center justify-center">
                        <CheckCircle2 className="h-4 w-4 text-success" />
                      </div>
                    </div>
                  ))}
                </div>

                <div className="rounded-lg border border-border/60 bg-card/60 p-4">
                  <div className="text-xs text-muted-foreground mb-2">Review Özeti</div>
                  <div className="text-sm">
                    {buildResult.pipeline.review_summary || "Agent tüm kontrollerden geçti."}
                  </div>
                </div>

                {buildResult.integrations.length > 0 && (
                  <div>
                    <div className="text-xs text-muted-foreground mb-2">Entegrasyonlar</div>
                    <div className="flex flex-wrap gap-1.5">
                      {buildResult.integrations.map((i) => (
                        <Badge key={i} variant="accent" className="font-mono text-[10px]">
                          {i}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
                    <FileText className="h-3.5 w-3.5" />
                    Instructions (örnek)
                  </div>
                  <pre className="text-xs whitespace-pre-wrap font-mono text-foreground/80 max-h-40 overflow-y-auto scrollbar-thin">
                    {buildResult.instructions.slice(0, 600) + (buildResult.instructions.length > 600 ? "..." : "")}
                  </pre>
                </div>

                <div className="flex flex-col sm:flex-row gap-2 pt-2">
                  <Button variant="outline" onClick={reset}>
                    <ArrowLeft className="h-4 w-4" />
                    Yeni Agent
                  </Button>
                  <Button
                    variant="gradient"
                    size="lg"
                    onClick={deploy}
                    disabled={deploying}
                    className="flex-1"
                  >
                    {deploying ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Deploy ediliyor...
                      </>
                    ) : (
                      <>
                        <Rocket className="h-4 w-4" />
                        Azure Foundry'ye Deploy Et
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function StageCard({ stage, index }: { stage: PipelineStage; index: number }) {
  const icons = { spec: FileText, policy: ShieldCheck, architecture: Cpu, scaffold: Wand2, review: CheckCircle2 };
  const Icon = (icons as Record<string, typeof FileText>)[stage.name] ?? FileText;

  const statusColor = {
    pending: "bg-muted/40 text-muted-foreground border-border/40",
    running: "bg-primary/10 text-primary border-primary/40",
    pass: "bg-success/10 text-success border-success/40",
    fail: "bg-destructive/10 text-destructive border-destructive/40",
  }[stage.status];

  const names: Record<string, string> = {
    spec: "Spec Builder",
    policy: "Policy Engine",
    architecture: "Architect",
    scaffold: "Scaffolder",
    review: "Reviewer",
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      className={cn("rounded-lg border p-3 flex items-center gap-3", statusColor)}
    >
      <div className="h-9 w-9 rounded-lg bg-background/50 flex items-center justify-center shrink-0">
        {stage.status === "running" ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : stage.status === "pass" ? (
          <Check className="h-4 w-4" />
        ) : stage.status === "fail" ? (
          <X className="h-4 w-4" />
        ) : (
          <Icon className="h-4 w-4" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold">{names[stage.name] ?? stage.name}</div>
        <div className="text-[11px] opacity-70">
          {stage.status === "pass"
            ? "Tamamlandı"
            : stage.status === "running"
            ? "Çalışıyor..."
            : stage.status === "fail"
            ? "Başarısız"
            : "Bekliyor"}
        </div>
      </div>
      {stage.status === "pass" && Object.keys(stage.data || {}).length > 0 && (
        <Badge variant="outline" className="text-[10px]">
          {Object.keys(stage.data).length} alan
        </Badge>
      )}
    </motion.div>
  );
}

function LivePreview({
  analyze,
  answers,
  description,
}: {
  analyze: AnalyzeResult;
  answers: Record<string, string>;
  description: string;
}) {
  const riskLevel =
    answers.pii === "true" ? "high" : answers.pii === "maybe" ? "medium" : "low";
  const riskColor =
    riskLevel === "high" ? "destructive" : riskLevel === "medium" ? "warning" : "success";

  return (
    <div className="sticky top-28 space-y-3">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <FileText className="h-4 w-4 text-primary" />
            Canlı Önizleme
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <Field label="Ad" value={analyze.name} />
          <Field label="Amaç" value={analyze.purpose} mono={false} />
          <Field label="Açıklama" value={description.slice(0, 100) + (description.length > 100 ? "..." : "")} mono={false} />

          {Object.keys(answers).length > 0 && (
            <div className="pt-3 border-t border-border/50 space-y-2">
              {Object.entries(answers).map(([k, v]) => (
                <div key={k} className="flex items-start justify-between gap-2 text-xs">
                  <span className="text-muted-foreground font-mono uppercase text-[10px]">{k}</span>
                  <span className="text-right font-medium">{v}</span>
                </div>
              ))}
            </div>
          )}

          <div className="pt-3 border-t border-border/50 flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Risk Seviyesi</span>
            <Badge variant={riskColor as "destructive" | "warning" | "success"}>
              {riskLevel === "high" ? "Yüksek" : riskLevel === "medium" ? "Orta" : "Düşük"}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {riskLevel === "high" && (
        <div className="rounded-lg border border-warning/40 bg-warning/5 p-3 flex gap-2 text-xs">
          <AlertTriangle className="h-4 w-4 text-warning shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-warning">Yüksek riskli agent</div>
            <div className="text-muted-foreground mt-0.5">
              PII içeriyor — insan onayı önerilir.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, value, mono = true }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div className="text-[10px] uppercase text-muted-foreground tracking-wide">{label}</div>
      <div className={cn("mt-0.5 text-sm", mono && "font-mono")}>{value || "—"}</div>
    </div>
  );
}

function Suggestion({
  icon,
  title,
  desc,
  onClick,
}: {
  icon: string;
  title: string;
  desc: string;
  onClick: (v: string) => void;
}) {
  return (
    <button
      onClick={() => onClick(desc)}
      className="text-left rounded-lg border border-border/60 bg-card/40 p-4 hover:border-primary/40 hover:bg-card/80 transition-all group"
    >
      <div className="text-2xl mb-2">{icon}</div>
      <div className="text-sm font-semibold mb-1">{title}</div>
      <div className="text-xs text-muted-foreground line-clamp-2">{desc}</div>
      <div className="text-[10px] text-primary mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
        Tıkla ve kullan →
      </div>
    </button>
  );
}
