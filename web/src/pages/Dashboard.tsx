import { useMemo } from "react";
import { Link } from "react-router-dom";
import { Bot, Users, MessageSquare, TrendingUp, ArrowRight, Activity, Shield, Zap } from "lucide-react";
import { Card } from "@/components/ui";
import { useStore } from "@/store";
import { cn } from "@/lib/utils";

/* ── Mock analitik veriler ── */
const MOCK_DAILY_QUERIES = [
  { day: "Pzt", count: 42 },
  { day: "Sal", count: 58 },
  { day: "Çar", count: 35 },
  { day: "Per", count: 71 },
  { day: "Cum", count: 63 },
  { day: "Cmt", count: 12 },
  { day: "Paz", count: 8 },
];

const MOCK_AGENT_USAGE = [
  { name: "Müşteri Destek", queries: 234, trend: +12 },
  { name: "Satış Rapor", queries: 187, trend: +8 },
  { name: "HR Asistan", queries: 156, trend: -3 },
  { name: "IT Helpdesk", queries: 142, trend: +22 },
  { name: "Finans Analiz", queries: 98, trend: +5 },
];

const MOCK_DEPT_STATS = [
  { dept: "Satış", agents: 4, users: 12, color: "bg-blue-500" },
  { dept: "IT", agents: 3, users: 8, color: "bg-teal-500" },
  { dept: "İK", agents: 2, users: 6, color: "bg-purple-500" },
  { dept: "Finans", agents: 2, users: 5, color: "bg-orange-500" },
  { dept: "Müşteri Hiz.", agents: 3, users: 15, color: "bg-green-500" },
];

const MOCK_RECENT_ACTIVITY = [
  { action: "Agent oluşturuldu", agent: "Müşteri Şikayet Analizi", user: "Ahmet Y.", time: "2 dk önce", type: "create" },
  { action: "Deploy edildi", agent: "Satış Rapor Asistanı", user: "Mehmet K.", time: "15 dk önce", type: "deploy" },
  { action: "Güncellendi", agent: "IT Helpdesk Bot", user: "Ayşe D.", time: "1 saat önce", type: "update" },
  { action: "Chat başlatıldı", agent: "HR Asistan", user: "Fatma S.", time: "2 saat önce", type: "chat" },
  { action: "Agent silindi", agent: "Test Agent", user: "Admin", time: "3 saat önce", type: "delete" },
];

export function Dashboard() {
  const agents = useStore((s) => s.agents);

  const stats = useMemo(() => {
    const activeAgents = agents.filter((a) => a.status === "active" || !a.status).length;
    return {
      totalAgents: agents.length || 14,
      activeAgents: activeAgents || 11,
      totalUsers: 46,
      dailyQueries: 289,
      avgResponseTime: "1.2s",
      uptime: "99.8%",
    };
  }, [agents]);

  const maxQuery = Math.max(...MOCK_DAILY_QUERIES.map((d) => d.count));
  const maxAgentUsage = Math.max(...MOCK_AGENT_USAGE.map((a) => a.queries));

  return (
    <div className="max-w-6xl mx-auto px-6 md:px-10 py-10 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-[13px] text-muted mt-1">Agent ekosistemi genel bakış</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-green-50 border border-green-200 px-3 py-1 text-[12px] text-green-700 font-medium">
            <span className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
            Sistem Aktif
          </span>
        </div>
      </div>

      {/* KPI Kartları */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <KpiCard icon={Bot} label="Toplam Agent" value={stats.totalAgents} sub="3 yeni bu hafta" color="text-blue-600" bg="bg-blue-50" />
        <KpiCard icon={Zap} label="Aktif Agent" value={stats.activeAgents} sub="Azure Foundry'de" color="text-green-600" bg="bg-green-50" />
        <KpiCard icon={Users} label="Aktif Kullanıcı" value={stats.totalUsers} sub="5 departman" color="text-purple-600" bg="bg-purple-50" />
        <KpiCard icon={MessageSquare} label="Günlük Sorgu" value={stats.dailyQueries} sub="+18% geçen hafta" color="text-teal-600" bg="bg-teal-50" />
        <KpiCard icon={Activity} label="Ort. Yanıt" value={stats.avgResponseTime} sub="streaming" color="text-orange-600" bg="bg-orange-50" />
        <KpiCard icon={Shield} label="Uptime" value={stats.uptime} sub="son 30 gün" color="text-emerald-600" bg="bg-emerald-50" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Haftalık Sorgu Grafiği */}
        <Card className="col-span-2 p-5">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h3 className="text-[14px] font-semibold">Haftalık Sorgu Trendi</h3>
              <p className="text-[12px] text-muted">Son 7 gün</p>
            </div>
            <span className="inline-flex items-center gap-1 text-[12px] text-green-600 font-medium">
              <TrendingUp className="h-3.5 w-3.5" /> +18%
            </span>
          </div>
          <div className="flex items-end gap-3 h-40">
            {MOCK_DAILY_QUERIES.map((d) => (
              <div key={d.day} className="flex-1 flex flex-col items-center gap-1.5">
                <span className="text-[11px] text-muted font-medium">{d.count}</span>
                <div
                  className="w-full rounded-t-md bg-ink/80 hover:bg-ink transition-colors"
                  style={{ height: `${(d.count / maxQuery) * 100}%`, minHeight: 4 }}
                />
                <span className="text-[11px] text-muted">{d.day}</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Departman Dağılımı */}
        <Card className="p-5">
          <h3 className="text-[14px] font-semibold mb-1">Departman Dağılımı</h3>
          <p className="text-[12px] text-muted mb-4">Agent & kullanıcı sayıları</p>
          <div className="space-y-3">
            {MOCK_DEPT_STATS.map((d) => (
              <div key={d.dept} className="flex items-center gap-3">
                <span className={cn("h-2.5 w-2.5 rounded-full shrink-0", d.color)} />
                <span className="text-[13px] font-medium flex-1">{d.dept}</span>
                <span className="text-[12px] text-muted">{d.agents} agent</span>
                <span className="text-[12px] text-muted">{d.users} kişi</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* En Çok Kullanılan Agentlar */}
        <Card className="p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-[14px] font-semibold">En Çok Kullanılan Agent'lar</h3>
              <p className="text-[12px] text-muted">Bu hafta</p>
            </div>
            <Link to="/agents" className="text-[12px] text-muted hover:text-ink flex items-center gap-1">
              Tümü <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="space-y-3">
            {MOCK_AGENT_USAGE.map((a, i) => (
              <div key={a.name} className="flex items-center gap-3">
                <span className="text-[12px] text-muted w-4 text-right font-medium">{i + 1}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[13px] font-medium truncate">{a.name}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[12px] text-muted">{a.queries} sorgu</span>
                      <span className={cn("text-[11px] font-medium", a.trend >= 0 ? "text-green-600" : "text-red-500")}>
                        {a.trend >= 0 ? "+" : ""}{a.trend}%
                      </span>
                    </div>
                  </div>
                  <div className="h-1.5 bg-surface rounded-full overflow-hidden">
                    <div
                      className="h-full bg-ink/70 rounded-full transition-all"
                      style={{ width: `${(a.queries / maxAgentUsage) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Son Aktiviteler */}
        <Card className="p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-[14px] font-semibold">Son Aktiviteler</h3>
              <p className="text-[12px] text-muted">Gerçek zamanlı</p>
            </div>
            <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
          </div>
          <div className="space-y-3">
            {MOCK_RECENT_ACTIVITY.map((a, i) => (
              <div key={i} className="flex items-start gap-3">
                <span className={cn(
                  "mt-0.5 h-2 w-2 rounded-full shrink-0",
                  a.type === "create" ? "bg-green-500" :
                  a.type === "deploy" ? "bg-blue-500" :
                  a.type === "update" ? "bg-orange-500" :
                  a.type === "chat" ? "bg-purple-500" :
                  "bg-red-500"
                )} />
                <div className="flex-1 min-w-0">
                  <div className="text-[13px]">
                    <span className="font-medium">{a.action}</span>
                    <span className="text-muted"> — {a.agent}</span>
                  </div>
                  <div className="text-[11px] text-muted">{a.user} · {a.time}</div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Alt Bilgi */}
      <div className="flex items-center justify-between pt-4 border-t border-border">
        <div className="flex items-center gap-4 text-[11px] text-muted">
          <span>Azure AI Foundry</span>
          <span>·</span>
          <span>Front Door + WAF</span>
          <span>·</span>
          <span>CI/CD Aktif</span>
        </div>
        <span className="text-[11px] text-muted">Son güncelleme: az önce</span>
      </div>
    </div>
  );
}

function KpiCard({ icon: Icon, label, value, sub, color, bg }: {
  icon: typeof Bot;
  label: string;
  value: string | number;
  sub: string;
  color: string;
  bg: string;
}) {
  return (
    <Card className="p-4">
      <div className={cn("inline-flex items-center justify-center h-8 w-8 rounded-lg mb-2.5", bg)}>
        <Icon className={cn("h-4 w-4", color)} />
      </div>
      <div className="text-[22px] font-semibold tracking-tight leading-none">{value}</div>
      <div className="text-[12px] font-medium text-ink mt-1">{label}</div>
      <div className="text-[11px] text-muted mt-0.5">{sub}</div>
    </Card>
  );
}
