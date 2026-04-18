import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  CheckCircle2,
  Filter,
  Loader2,
  Rocket,
  Search,
  Sparkles,
  X,
  AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, type Template } from "@/lib/api";
import { useAppStore } from "@/store";
import { cn } from "@/lib/utils";

export function TemplatesPage() {
  const templates = useAppStore((s) => s.templates);
  const setTemplates = useAppStore((s) => s.setTemplates);
  const [q, setQ] = useState("");
  const [category, setCategory] = useState<string>("all");
  const [selected, setSelected] = useState<Template | null>(null);

  useEffect(() => {
    api.templates().then(setTemplates).catch(() => {});
  }, [setTemplates]);

  const categories = useMemo(() => {
    const set = new Set<string>();
    templates.forEach((t) => set.add(t.category));
    return ["all", ...Array.from(set)];
  }, [templates]);

  const filtered = useMemo(() => {
    return templates.filter((t) => {
      if (category !== "all" && t.category !== category) return false;
      if (q) {
        const s = q.toLowerCase();
        return (
          t.name.toLowerCase().includes(s) ||
          t.description.toLowerCase().includes(s) ||
          t.category.toLowerCase().includes(s)
        );
      }
      return true;
    });
  }, [templates, q, category]);

  return (
    <div className="max-w-7xl mx-auto p-4 md:p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-primary" />
          Şablon Galerisi
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Hazır senaryolar — tek tıkla deploy et, anında kullanmaya başla.
        </p>
      </div>

      <div className="flex flex-col md:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Şablon ara..."
            className="pl-9"
          />
        </div>
        <div className="flex gap-1.5 flex-wrap rounded-lg border border-border bg-card/40 p-1">
          {categories.map((c) => (
            <button
              key={c}
              onClick={() => setCategory(c)}
              className={cn(
                "px-3 py-1.5 rounded-md text-xs font-medium transition-all",
                category === c
                  ? "bg-primary/15 text-primary"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {c === "all" ? "Tümü" : c}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <AnimatePresence>
          {filtered.map((t, i) => (
            <motion.div
              key={t.id}
              layout
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ delay: i * 0.04 }}
            >
              <TemplateCard template={t} onOpen={() => setSelected(t)} />
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {filtered.length === 0 && (
        <Card>
          <CardContent className="p-12 text-center">
            <Filter className="h-10 w-10 text-muted-foreground/40 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">Eşleşen şablon yok</p>
          </CardContent>
        </Card>
      )}

      <AnimatePresence>
        {selected && (
          <TemplateDrawer template={selected} onClose={() => setSelected(null)} />
        )}
      </AnimatePresence>
    </div>
  );
}

function TemplateCard({
  template,
  onOpen,
}: {
  template: Template;
  onOpen: () => void;
}) {
  return (
    <Card className="group cursor-pointer hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5 transition-all h-full">
      <CardContent className="p-5" onClick={onOpen}>
        <div className="flex items-start gap-3 mb-3">
          <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-primary/15 to-accent/10 flex items-center justify-center text-2xl shrink-0">
            {template.emoji}
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-sm truncate">{template.name}</h3>
            <Badge variant="accent" className="text-[9px] mt-1 px-1.5 py-0">
              {template.category}
            </Badge>
          </div>
        </div>

        <p className="text-xs text-muted-foreground line-clamp-3 min-h-[48px] mb-3">
          {template.description}
        </p>

        <div className="flex flex-wrap gap-1 mb-3 min-h-[22px]">
          {template.tools.slice(0, 3).map((t) => (
            <span
              key={t}
              className="text-[9px] font-mono bg-muted/60 border border-border rounded px-1.5 py-0.5"
            >
              {t}
            </span>
          ))}
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-border/40">
          <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
            {template.pii === "true" && (
              <span className="flex items-center gap-1 text-warning">
                <AlertTriangle className="h-3 w-3" /> PII
              </span>
            )}
            {template.approval === "true" && (
              <span className="flex items-center gap-1 text-accent">
                <CheckCircle2 className="h-3 w-3" /> Onay
              </span>
            )}
          </div>
          <span className="text-xs text-primary opacity-0 group-hover:opacity-100 transition-opacity">
            İncele →
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

function TemplateDrawer({
  template,
  onClose,
}: {
  template: Template;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);

  async function deploy() {
    setBusy(true);
    try {
      const build = await api.buildFromTemplate(template.id, {});
      const res = await api.deploy(build.spec_id);
      if (res.success) {
        toast.success(res.mock ? "Mock deploy tamamlandı" : "Azure'a deploy edildi!");
        await api.agents().then((a) => useAppStore.getState().setAgents(a));
        navigate(`/chat?agent=${encodeURIComponent(res.foundry_agent_id || "")}`);
      } else {
        toast.error("Deploy başarısız: " + (res.error ?? "?"));
      }
    } catch (e) {
      toast.error("Hata: " + String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-40 bg-background/70 backdrop-blur-sm flex justify-end"
      onClick={onClose}
    >
      <motion.div
        initial={{ x: "100%" }}
        animate={{ x: 0 }}
        exit={{ x: "100%" }}
        transition={{ type: "spring", stiffness: 260, damping: 30 }}
        className="w-full max-w-lg h-full bg-card border-l border-border/60 overflow-y-auto scrollbar-thin"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between p-5 border-b border-border/50 bg-card/90 backdrop-blur-xl">
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-primary/15 to-accent/10 flex items-center justify-center text-2xl">
              {template.emoji}
            </div>
            <div>
              <div className="font-semibold">{template.name}</div>
              <div className="text-xs text-muted-foreground">{template.category}</div>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="p-5 space-y-5">
          <p className="text-sm leading-relaxed">{template.description}</p>

          <Block title="Amaç">
            <p className="text-sm text-muted-foreground">{template.purpose}</p>
          </Block>

          <Block title="Örnek Senaryo">
            <div className="rounded-lg border border-primary/20 bg-primary/5 p-3 text-sm italic">
              "{template.example_scenario}"
            </div>
          </Block>

          <Block title="Yetenekler">
            <div className="space-y-1.5">
              {template.capabilities.map((c) => (
                <div key={c} className="flex items-start gap-2 text-sm">
                  <CheckCircle2 className="h-3.5 w-3.5 text-success mt-0.5 shrink-0" />
                  <span>{c}</span>
                </div>
              ))}
            </div>
          </Block>

          <div className="grid grid-cols-2 gap-2">
            <Block title="Araçlar" compact>
              <div className="flex flex-wrap gap-1">
                {template.tools.map((t) => (
                  <Badge key={t} variant="secondary" className="font-mono text-[10px]">
                    {t}
                  </Badge>
                ))}
              </div>
            </Block>
            <Block title="Veri Kaynakları" compact>
              <div className="flex flex-wrap gap-1">
                {template.data_sources.map((d) => (
                  <Badge key={d} variant="outline" className="text-[10px]">
                    {d}
                  </Badge>
                ))}
              </div>
            </Block>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            <Attr label="Hedef" value={template.audience} />
            <Attr label="Ton" value={template.tone} />
            <Attr label="Format" value={template.output_format} />
            <Attr label="Kapsam" value={template.scope} />
            <Attr label="PII" value={template.pii} highlight={template.pii === "true"} />
            <Attr label="Onay" value={template.approval} highlight={template.approval === "true"} />
          </div>

          <Button
            variant="gradient"
            size="lg"
            className="w-full"
            onClick={deploy}
            disabled={busy}
          >
            {busy ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Deploy ediliyor...
              </>
            ) : (
              <>
                <Rocket className="h-4 w-4" />
                Tek Tıkla Deploy Et
              </>
            )}
          </Button>
        </div>
      </motion.div>
    </motion.div>
  );
}

function Block({
  title,
  children,
  compact,
}: {
  title: string;
  children: React.ReactNode;
  compact?: boolean;
}) {
  return (
    <div>
      <div
        className={cn(
          "text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2",
          compact && "mb-1.5"
        )}
      >
        {title}
      </div>
      {children}
    </div>
  );
}

function Attr({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-md border px-2.5 py-1.5",
        highlight ? "border-warning/40 bg-warning/5" : "border-border/60 bg-card/40"
      )}
    >
      <div className="text-[10px] uppercase text-muted-foreground">{label}</div>
      <div className="text-xs font-medium mt-0.5 font-mono">{value}</div>
    </div>
  );
}
