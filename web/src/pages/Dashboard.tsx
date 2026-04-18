import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Activity,
  ArrowUpRight,
  Bot,
  CheckCircle2,
  LayoutTemplate,
  Plus,
  Sparkles,
  TrendingUp,
  Zap,
  AlertTriangle,
  ShieldCheck,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type AnalyticsOverview } from "@/lib/api";
import { useAppStore } from "@/store";
import { cn, truncate } from "@/lib/utils";

export function Dashboard() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const agents = useAppStore((s) => s.agents);
  const templates = useAppStore((s) => s.templates);

  useEffect(() => {
    api.analytics().then(setOverview).catch(() => {});
  }, []);

  const recentAgents = agents.slice(0, 6);

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-8">
      {/* Hero */}
      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="relative overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-primary/10 via-card to-accent/5 p-6 md:p-10"
      >
        <div className="absolute top-0 right-0 h-72 w-72 bg-primary/10 blur-3xl rounded-full -z-10" />
        <div className="absolute bottom-0 left-0 h-48 w-48 bg-accent/10 blur-3xl rounded-full -z-10" />

        <Badge variant="outline" className="mb-4 gap-1.5">
          <Sparkles className="h-3 w-3 text-primary" /> v2.0 • Azure AI Foundry
        </Badge>
        <h1 className="text-3xl md:text-5xl font-bold tracking-tight leading-tight">
          Doğal dille <span className="gradient-text animate-gradient-shift">AI agent</span>
          <br />
          inşa edin, saniyeler içinde deploy edin.
        </h1>
        <p className="mt-4 text-muted-foreground max-w-2xl">
          Microsoft Agent Framework ve Azure AI Foundry üzerinde çalışan, kullanıcılara
          ihtiyaç duydukları agent'ları tek bir metinle oluşturma imkânı sunan platform.
        </p>

        <div className="mt-6 flex flex-wrap gap-3">
          <Button asChild variant="gradient" size="lg" className="group">
            <Link to="/build">
              <Plus className="h-4 w-4" />
              Yeni Agent Oluştur
              <ArrowUpRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <Link to="/templates">
              <LayoutTemplate className="h-4 w-4" /> Şablonları İncele
            </Link>
          </Button>
        </div>
      </motion.section>

      {/* Stats */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
        <StatCard
          icon={Bot}
          label="Toplam Agent"
          value={overview?.agents.total ?? agents.length}
          accent="primary"
        />
        <StatCard
          icon={CheckCircle2}
          label="Aktif"
          value={overview?.agents.active ?? 0}
          accent="success"
        />
        <StatCard
          icon={Zap}
          label="Şablon"
          value={templates.length}
          accent="accent"
        />
        <StatCard
          icon={Activity}
          label="Oluşturulan Spec"
          value={overview?.specs.total ?? 0}
          accent="warning"
        />
      </section>

      {/* Recent agents + Quick actions */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between pb-4">
            <div>
              <CardTitle>Son Agent'lar</CardTitle>
              <CardDescription>Ekosistemde yer alan agent'lar</CardDescription>
            </div>
            <Button asChild variant="ghost" size="sm">
              <Link to="/agents">
                Tümünü gör <ArrowUpRight className="h-3.5 w-3.5" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            {recentAgents.length === 0 ? (
              <EmptyAgents />
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {recentAgents.map((a, i) => (
                  <motion.div
                    key={a.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.04 }}
                  >
                    <Link
                      to={`/chat?agent=${encodeURIComponent(a.id)}`}
                      className="group flex items-start gap-3 rounded-lg border border-border/60 bg-card/40 p-3 hover:border-primary/40 hover:bg-card/80 transition-all"
                    >
                      <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center shrink-0">
                        <Bot className="h-4 w-4 text-primary" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm truncate">{a.name}</span>
                          {a.status === "mock" && (
                            <Badge variant="warning" className="text-[9px] px-1.5 py-0">mock</Badge>
                          )}
                          {a.status === "draft" && (
                            <Badge variant="secondary" className="text-[9px] px-1.5 py-0">taslak</Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                          {truncate(a.instructions.replace(/\n/g, " "), 80) || a.model}
                        </p>
                        <div className="flex gap-1 mt-1.5 flex-wrap">
                          {a.tools.slice(0, 3).map((t, idx) => (
                            <span
                              key={idx}
                              className="text-[9px] font-mono bg-muted/60 border border-border rounded px-1 py-0"
                            >
                              {t.type}
                            </span>
                          ))}
                        </div>
                      </div>
                    </Link>
                  </motion.div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-4">
            <CardTitle>Hızlı Aksiyonlar</CardTitle>
            <CardDescription>Sık kullanılan yollar</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <QuickAction
              to="/build"
              title="Sohbetle agent oluştur"
              desc="Doğal dilden yapılandırılmış spec'e"
              icon={Plus}
            />
            <QuickAction
              to="/templates"
              title="Hazır şablon kullan"
              desc="Tek tıkla deploy et"
              icon={LayoutTemplate}
            />
            <QuickAction
              to="/analytics"
              title="Maliyet ve kullanım"
              desc="Token / USD metrikler"
              icon={TrendingUp}
            />
          </CardContent>
        </Card>
      </section>

      {/* Security & policy footer */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <FeatureHighlight
          icon={ShieldCheck}
          title="Policy Engine"
          desc="PII, risk, onay kuralları her deploy öncesi otomatik kontrol edilir."
        />
        <FeatureHighlight
          icon={Sparkles}
          title="Akıllı Architect"
          desc="Prompt / Workflow / Hosted agent seçimi spec karmaşıklığına göre."
        />
        <FeatureHighlight
          icon={AlertTriangle}
          title="Risk Uyarıları"
          desc="PII veya yüksek risk içeren senaryolarda onay ekrana düşer."
        />
      </section>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  accent,
}: {
  icon: typeof Bot;
  label: string;
  value: number;
  accent: "primary" | "accent" | "success" | "warning";
}) {
  const colors = {
    primary: "text-primary bg-primary/10",
    accent: "text-accent bg-accent/10",
    success: "text-success bg-success/10",
    warning: "text-warning bg-warning/10",
  }[accent];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ y: -2 }}
    >
      <Card>
        <CardContent className="p-4">
          <div className={cn("h-10 w-10 rounded-lg flex items-center justify-center mb-3", colors)}>
            <Icon className="h-5 w-5" />
          </div>
          <div className="text-2xl font-bold tracking-tight">{value}</div>
          <div className="text-xs text-muted-foreground mt-0.5">{label}</div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

function QuickAction({
  to, title, desc, icon: Icon,
}: {
  to: string; title: string; desc: string; icon: typeof Bot;
}) {
  return (
    <Link
      to={to}
      className="flex items-start gap-3 rounded-lg p-3 hover:bg-accent/5 transition-colors group"
    >
      <div className="h-9 w-9 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 text-primary">
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-sm font-medium">{title}</div>
        <div className="text-xs text-muted-foreground">{desc}</div>
      </div>
      <ArrowUpRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all" />
    </Link>
  );
}

function FeatureHighlight({
  icon: Icon, title, desc,
}: { icon: typeof Bot; title: string; desc: string }) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="h-9 w-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center mb-3">
          <Icon className="h-4 w-4" />
        </div>
        <div className="text-sm font-semibold mb-1">{title}</div>
        <div className="text-xs text-muted-foreground leading-relaxed">{desc}</div>
      </CardContent>
    </Card>
  );
}

function EmptyAgents() {
  return (
    <div className="flex flex-col items-center justify-center py-10 text-center">
      <Bot className="h-12 w-12 text-muted-foreground/40 mb-3" />
      <p className="text-sm text-muted-foreground mb-3">Henüz agent oluşturulmadı</p>
      <Button asChild size="sm" variant="gradient">
        <Link to="/build">İlk agent'ı oluştur</Link>
      </Button>
    </div>
  );
}
