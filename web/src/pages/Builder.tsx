import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Check, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button, Card, Input, Textarea } from "@/components/ui";
import { AgentFlow } from "@/components/AgentFlow";
import { WIZARD_STEPS } from "@/lib/wizard";
import { api, type AnalyzeResult, type BuildPayload, type BuildResult } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useStore } from "@/store";

type Phase = "describe" | "analyzing" | "wizard" | "building" | "done";

export function Builder() {
  const navigate = useNavigate();
  const [phase, setPhase] = useState<Phase>("describe");
  const [description, setDescription] = useState("");
  const [analyze, setAnalyze] = useState<AnalyzeResult | null>(null);
  const [stepIdx, setStepIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<BuildResult | null>(null);
  const [deploying, setDeploying] = useState(false);
  const [deployStatus, setDeployStatus] = useState("");
  const [inferredParent, setInferredParent] = useState<string | undefined>();
  const [editName, setEditName] = useState("");
  const [editPurpose, setEditPurpose] = useState("");
  const [editInstructions, setEditInstructions] = useState("");
  const [editParent, setEditParent] = useState<string>("");

  const me = useStore((s) => s.me);
  const PARENT_OPTIONS = me?.allowed_parents?.length
    ? me.allowed_parents
    : ["Supervisor-Agent", "HR-Agent", "IT-Agent", "Finance-Agent",
       "Math-Agent", "General-Agent", "Chat-Agent"];

  const step = WIZARD_STEPS[stepIdx];

  async function doAnalyze() {
    if (description.trim().length < 10) {
      toast.error("Biraz daha detay yazın");
      return;
    }
    setPhase("analyzing");
    try {
      const r = await api.analyze(description);
      setAnalyze(r);
      setInferredParent(r.inferred_parent);
      setPhase("wizard");
    } catch (e) {
      toast.error(String(e));
      setPhase("describe");
    }
  }

  function pick(v: string) {
    setAnswers((a) => ({ ...a, [step.id]: v }));
    if (stepIdx < WIZARD_STEPS.length - 1) {
      setTimeout(() => setStepIdx((i) => i + 1), 150);
    } else {
      setTimeout(doBuild, 150);
    }
  }

  async function doBuild() {
    if (!analyze) return;
    setPhase("building");
    const payload: BuildPayload = {
      description,
      name: analyze.name,
      purpose: analyze.purpose,
      audience: answers.audience ?? "tum_sirket",
      tone: answers.tone ?? "friendly",
      output_format: answers.output_format ?? "adaptive",
      scope: answers.scope ?? "strict_scope",
      pii: answers.pii ?? "maybe",
      approval: answers.approval ?? "conditional",
      example_scenario: "skip",
      inferred_tools: analyze.inferred_tools,
      inferred_data_sources: analyze.inferred_data_sources,
      suggested_capabilities: analyze.suggested_capabilities,
      complexity_hints: analyze.complexity_hints,
    };
    try {
      const r = await api.build(payload);
      setResult(r);
      setEditName(String(r.spec?.name ?? analyze.name ?? ""));
      setEditPurpose(String(r.spec?.purpose ?? analyze.purpose ?? ""));
      setEditInstructions(r.instructions || "");
      const desired = inferredParent || "Supervisor-Agent";
      setEditParent(PARENT_OPTIONS.includes(desired) ? desired : PARENT_OPTIONS[0]);
      setPhase("done");
      // Backend'den gelen uyarıları göster
      if ((r as any).warnings?.length) {
        for (const w of (r as any).warnings) {
          toast.warning(w);
        }
      }
    } catch (e) {
      toast.error("Oluşturma başarısız: " + String(e));
      setPhase("wizard");
    }
  }

  async function doDeploy() {
    if (!result || deploying) return;
    console.log("deploy clicked", result.spec_id);
    setDeploying(true);
    setDeployStatus("Deploy istegi gonderiliyor...");
    toast.info("Azure AI Foundry deploy basladi. Bu islem biraz surebilir.");
    try {
      const r = await api.deploy(result.spec_id, {
        name: editName.trim() || undefined,
        purpose: editPurpose.trim() || undefined,
        instructions: editInstructions.trim() || undefined,
        parent_agent_name: editParent || undefined,
      });
      setDeployStatus("Deploy cevabi alindi.");
      if (r.success) {
        if (r.mock) {
          toast.success("Agent oluşturuldu (mock — Foundry bağlantısı kurulamadı)");
        } else {
          toast.success("Agent başarıyla Azure'a deploy edildi");
        }
        if (r.application_update_error) {
          toast.warning("Application güncelleme uyarısı: " + r.application_update_error);
        }
        navigate(`/chat?agent=${encodeURIComponent(r.foundry_agent_id || "")}`);
      } else {
        toast.error("Deploy başarısız: " + (r.error || "Bilinmeyen hata"));
      }
    } catch (e) {
      toast.error(String(e));
    } finally {
      setDeploying(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-6 md:px-10 py-14 md:py-20">
      <div className="flex-1 min-w-0">
      {phase === "describe" && (
        <div className="space-y-6 animate-in fade-in duration-300">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight mb-2">
              Ne yapmasını istiyorsunuz?
            </h1>
            <p className="text-muted text-[14px]">
              Birkaç cümle yeterli. Sistem analiz edip öneriler sunacak.
            </p>
          </div>
          <Textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Örn: Excel dosyası yükleyip hata kodlarını bulsun ve özet rapor çıkarsın."
            className="min-h-[140px] text-[15px] leading-relaxed p-4"
            autoFocus
          />
          <div className="flex justify-end">
            <Button
              size="lg"
              onClick={doAnalyze}
              disabled={description.trim().length < 10}
            >
              Devam
            </Button>
          </div>

          {/* Ekosistem grafiği */}
          <div className="pt-4 border-t border-border">
            <p className="text-[10px] uppercase tracking-widest text-muted mb-3 text-center">
              Mevcut Ekosistem
            </p>
            <AgentFlow height={340} />
          </div>
        </div>
      )}

      {phase === "analyzing" && <Center text="Analiz ediliyor" />}

      {phase === "wizard" && analyze && (
        <div className="space-y-8 animate-in fade-in duration-300">
          <div className="flex items-center gap-3">
            <div className="text-[12px] text-muted">
              {stepIdx + 1} / {WIZARD_STEPS.length}
            </div>
            <div className="flex-1 h-[2px] bg-border rounded-full overflow-hidden">
              <div
                className="h-full bg-ink transition-all duration-300"
                style={{ width: `${((stepIdx + 1) / WIZARD_STEPS.length) * 100}%` }}
              />
            </div>
          </div>

          <div>
            <div className="text-[12px] text-muted mb-2">{analyze.name}</div>
            <h2 className="text-2xl font-semibold tracking-tight">{step.title}</h2>
          </div>

          <div className="space-y-2">
            {step.choices.map((c) => {
              const selected = answers[step.id] === c.value;
              return (
                <button
                  key={c.value}
                  onClick={() => pick(c.value)}
                  className={cn(
                    "w-full flex items-center justify-between rounded-lg border px-4 py-3.5 text-left transition-colors",
                    selected
                      ? "border-ink bg-ink/[0.03]"
                      : "border-border bg-white hover:border-ink/40"
                  )}
                >
                  <span className="text-[14px] font-medium">{c.label}</span>
                  {selected && <Check className="h-4 w-4" />}
                </button>
              );
            })}
          </div>

          <div className="flex justify-between">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                if (stepIdx === 0) setPhase("describe");
                else setStepIdx((i) => i - 1);
              }}
            >
              <ArrowLeft className="h-4 w-4" />
              Geri
            </Button>
          </div>

          {/* Ön izleme: yeni agent ekosistemde nereye gidecek */}
          <div className="pt-4 border-t border-border">
            <p className="text-[10px] uppercase tracking-widest text-muted mb-3 text-center">
              Ekosistemde Ön İzleme
            </p>
            <AgentFlow
              height={300}
              previewAgent={{ name: analyze.name, parentName: inferredParent }}
            />
          </div>
        </div>
      )}

      {phase === "building" && <Center text="Agent oluşturuluyor" />}

      {phase === "done" && result && (

        <div className="space-y-6 animate-in fade-in duration-300">
          <div>
            <div className="inline-flex items-center gap-2 text-[13px] text-muted mb-3">
              <span className="h-1.5 w-1.5 rounded-full bg-green-500" /> Ön izleme
            </div>
            <h1 className="text-3xl font-semibold tracking-tight mb-2">
              Deploy öncesi kontrol
            </h1>
            <p className="text-muted text-[14px]">
              Agent bilgilerini gözden geçirin. Yanlış anlaşılmışsa düzenleyip deploy edin.
            </p>
          </div>

          {/* Ekosistem önizlemesi */}
          <div>
            <p className="text-[10px] uppercase tracking-widest text-muted mb-3 text-center">
              Ekosistemde Nereye Eklenecek
            </p>
            <AgentFlow
              height={280}
              previewAgent={{ name: editName || "Yeni Agent", parentName: editParent }}
            />
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-[11px] uppercase tracking-widest text-muted mb-1.5 block">İsim</label>
              <Input value={editName} onChange={(e) => setEditName(e.target.value)} />
            </div>

            <div>
              <label className="text-[11px] uppercase tracking-widest text-muted mb-1.5 block">Bağlanacağı Dal</label>
              <select
                value={editParent}
                onChange={(e) => setEditParent(e.target.value)}
                className="w-full rounded-lg border border-border bg-white px-3 py-2 text-[14px]"
              >
                {PARENT_OPTIONS.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-[11px] uppercase tracking-widest text-muted mb-1.5 block">Amaç</label>
              <Textarea
                value={editPurpose}
                onChange={(e) => setEditPurpose(e.target.value)}
                className="min-h-[70px]"
              />
            </div>

            <div>
              <label className="text-[11px] uppercase tracking-widest text-muted mb-1.5 block">
                Sistem Talimatları
              </label>
              <Textarea
                value={editInstructions}
                onChange={(e) => setEditInstructions(e.target.value)}
                className="min-h-[220px] font-mono text-[12px] leading-relaxed"
              />
            </div>
          </div>

          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="lg"
              onClick={() => {
                setPhase("describe");
                setDescription("");
                setAnalyze(null);
                setAnswers({});
                setStepIdx(0);
                setResult(null);
                setDeployStatus("");
              }}
            >
              Yeni
            </Button>
            <Button size="lg" onClick={doDeploy} disabled={deploying} className="flex-1">
              {deploying && <Loader2 className="h-4 w-4 animate-spin" />}
              {deploying ? "Deploy ediliyor..." : "Deploy et"}
            </Button>
          </div>
          {deployStatus && (
            <div className="rounded-lg border border-border bg-surface px-4 py-3 text-[13px] text-muted">
              {deployStatus}
            </div>
          )}
        </div>
      )}
      </div> {/* flex-1 */}
    </div>
  );
}

function Center({ text }: { text: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-32 text-muted">
      <Loader2 className="h-5 w-5 animate-spin mb-3" />
      <div className="text-[13px]">{text}</div>
    </div>
  );
}
