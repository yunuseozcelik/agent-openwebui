import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  Bot,
  Coins,
  FileText,
  RotateCcw,
  ShieldCheck,
  TrendingUp,
  Wrench,
  Zap,
} from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api, type AnalyticsOverview } from "@/lib/api";
import { cn } from "@/lib/utils";

interface CostSnapshot {
  total_calls?: number;
  total_tokens?: number;
  total_usd?: number;
  by_model?: Record<string, { calls: number; tokens: number; usd: number }>;
  [k: string]: unknown;
}

export function AnalyticsPage() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [cost, setCost] = useState<CostSnapshot | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const [ov, co] = await Promise.all([api.analytics(), api.cost()]);
      setOverview(ov);
      setCost(co as CostSnapshot);
    } catch (e) {
      toast.error("Analitik yüklenemedi: " + String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function resetCost() {
    try {
      await fetch("/api/analytics/cost/reset", { method: "POST" });
      toast.success("Maliyet sayacı sıfırlandı");
      load();
    } catch (e) {
      toast.error("Sıfırlama başarısız");
    }
  }

  const tools = overview?.tools ?? {};
  const toolEntries = Object.entries(tools).sort((a, b) => b[1] - a[1]);
  const toolMax = Math.max(1, ...toolEntries.map(([, v]) => v));

  const risk = overview?.specs.by_risk ?? { low: 0, medium: 0, high: 0 };
  const riskTotal = (risk.low ?? 0) + (risk.medium ?? 0) + (risk.high ?? 0);

  return (
    <div className="max-w-7xl mx-auto p-4 md:p-8 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Activity className="h-6 w-6 text-primary" />
            Analitik
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Kullanım, maliyet ve araç dağılımı — gerçek zamanlı
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RotateCcw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
            Yenile
          </Button>
          <Button variant="outline" size="sm" onClick={resetCost}>
            Maliyet Sıfırla
          </Button>
        </div>
      </div>

      {/* Top stats */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
        <StatCard
          icon={Bot}
          label="Toplam Agent"
          value={overview?.agents.total ?? 0}
          sub={`${overview?.agents.active ?? 0} aktif`}
          accent="primary"
        />
        <StatCard
          icon={FileText}
          label="Spec"
          value={overview?.specs.total ?? 0}
          sub="üretilen"
          accent="accent"
        />
        <StatCard
          icon={Coins}
          label="Toplam Maliyet"
          value={`$${(cost?.total_usd ?? 0).toFixed(4)}`}
          sub={`${cost?.total_calls ?? 0} çağrı`}
          accent="warning"
        />
        <StatCard
          icon={Zap}
          label="Token"
          value={fmtNum(cost?.total_tokens ?? 0)}
          sub="toplam"
          accent="success"
        />
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tool distribution */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Wrench className="h-4 w-4 text-primary" />
              Araç Kullanım Dağılımı
            </CardTitle>
            <CardDescription>Agent'larda en çok kullanılan araçlar</CardDescription>
          </CardHeader>
          <CardContent>
            {toolEntries.length === 0 ? (
              <EmptyChart />
            ) : (
              <div className="space-y-2.5">
                {toolEntries.map(([tool, count], i) => (
                  <motion.div
                    key={tool}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.04 }}
                    className="space-y-1"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-mono">{tool}</span>
                      <span className="text-muted-foreground">{count}</span>
                    </div>
                    <div className="h-2 rounded-full bg-muted overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${(count / toolMax) * 100}%` }}
                        transition={{ duration: 0.6, delay: i * 0.04 }}
                        className="h-full bg-gradient-to-r from-primary to-accent"
                      />
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Risk */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-primary" />
              Risk Dağılımı
            </CardTitle>
            <CardDescription>Spec risk seviyeleri</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <RiskRow
              label="Düşük"
              count={risk.low ?? 0}
              total={riskTotal}
              color="success"
            />
            <RiskRow
              label="Orta"
              count={risk.medium ?? 0}
              total={riskTotal}
              color="warning"
            />
            <RiskRow
              label="Yüksek"
              count={risk.high ?? 0}
              total={riskTotal}
              color="destructive"
            />

            <div className="pt-3 border-t border-border/50">
              <div className="flex items-start gap-2 text-xs text-muted-foreground">
                <AlertTriangle className="h-3.5 w-3.5 text-warning shrink-0 mt-0.5" />
                <span>
                  Yüksek riskli agent'larda insan onayı ve PII politikası önerilir.
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Cost by model */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-primary" />
            Model Bazlı Maliyet
          </CardTitle>
          <CardDescription>Her model için çağrı, token ve USD</CardDescription>
        </CardHeader>
        <CardContent>
          {cost?.by_model && Object.keys(cost.by_model).length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-muted-foreground border-b border-border/50">
                    <th className="text-left py-2 font-medium">Model</th>
                    <th className="text-right py-2 font-medium">Çağrı</th>
                    <th className="text-right py-2 font-medium">Token</th>
                    <th className="text-right py-2 font-medium">USD</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(cost.by_model).map(([model, m]) => (
                    <tr key={model} className="border-b border-border/30 last:border-0">
                      <td className="py-2 font-mono text-xs">{model}</td>
                      <td className="py-2 text-right font-mono">{m.calls}</td>
                      <td className="py-2 text-right font-mono">{fmtNum(m.tokens)}</td>
                      <td className="py-2 text-right font-mono text-primary">
                        ${m.usd.toFixed(4)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyChart message="Henüz maliyet kaydı yok" />
          )}
        </CardContent>
      </Card>

      {/* Agent health */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Agent Sağlığı</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-3">
            <HealthCell
              label="Aktif"
              value={overview?.agents.active ?? 0}
              total={overview?.agents.total ?? 0}
              color="success"
            />
            <HealthCell
              label="Mock"
              value={overview?.agents.mock ?? 0}
              total={overview?.agents.total ?? 0}
              color="warning"
            />
            <HealthCell
              label="Taslak"
              value={overview?.agents.draft ?? 0}
              total={overview?.agents.total ?? 0}
              color="muted"
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  accent,
}: {
  icon: typeof Bot;
  label: string;
  value: string | number;
  sub?: string;
  accent: "primary" | "accent" | "success" | "warning";
}) {
  const colors = {
    primary: "text-primary bg-primary/10",
    accent: "text-accent bg-accent/10",
    success: "text-success bg-success/10",
    warning: "text-warning bg-warning/10",
  }[accent];

  return (
    <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }}>
      <Card>
        <CardContent className="p-4">
          <div className={cn("h-10 w-10 rounded-lg flex items-center justify-center mb-3", colors)}>
            <Icon className="h-5 w-5" />
          </div>
          <div className="text-2xl font-bold tracking-tight">{value}</div>
          <div className="text-xs text-muted-foreground mt-0.5">{label}</div>
          {sub && <div className="text-[10px] text-muted-foreground/70 mt-0.5">{sub}</div>}
        </CardContent>
      </Card>
    </motion.div>
  );
}

function RiskRow({
  label,
  count,
  total,
  color,
}: {
  label: string;
  count: number;
  total: number;
  color: "success" | "warning" | "destructive";
}) {
  const pct = total ? (count / total) * 100 : 0;
  const bg = {
    success: "bg-success",
    warning: "bg-warning",
    destructive: "bg-destructive",
  }[color];
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span>{label}</span>
        <Badge variant={color as "success" | "warning" | "destructive"}>{count}</Badge>
      </div>
      <div className="h-2 rounded-full bg-muted overflow-hidden">
        <motion.div
          className={cn("h-full", bg)}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>
    </div>
  );
}

function HealthCell({
  label,
  value,
  total,
  color,
}: {
  label: string;
  value: number;
  total: number;
  color: "success" | "warning" | "muted";
}) {
  const pct = total ? Math.round((value / total) * 100) : 0;
  const ring = {
    success: "text-success",
    warning: "text-warning",
    muted: "text-muted-foreground",
  }[color];
  return (
    <div className="rounded-lg border border-border/60 bg-card/40 p-4 text-center">
      <div className={cn("text-3xl font-bold", ring)}>{value}</div>
      <div className="text-xs text-muted-foreground mt-1">{label}</div>
      <div className="text-[10px] text-muted-foreground/70 mt-0.5">%{pct}</div>
    </div>
  );
}

function EmptyChart({ message }: { message?: string }) {
  return (
    <div className="py-10 text-center text-sm text-muted-foreground">
      {message ?? "Henüz veri yok"}
    </div>
  );
}

function fmtNum(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "k";
  return String(n);
}
