import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bot,
  MessageSquare,
  Plus,
  Search,
  Sparkles,
  Wrench,
  Cpu,
  AlertCircle,
  X,
  ChevronRight,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAppStore } from "@/store";
import { api, type Agent } from "@/lib/api";
import { cn, truncate } from "@/lib/utils";

type StatusFilter = "all" | "active" | "mock" | "draft";

export function AgentsPage() {
  const agents = useAppStore((s) => s.agents);
  const setAgents = useAppStore((s) => s.setAgents);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<StatusFilter>("all");
  const [selected, setSelected] = useState<Agent | null>(null);

  useEffect(() => {
    api.agents().then(setAgents).catch(() => {});
  }, [setAgents]);

  const filtered = useMemo(() => {
    return agents.filter((a) => {
      if (status !== "all" && a.status !== status) return false;
      if (q) {
        const t = q.toLowerCase();
        return (
          a.name.toLowerCase().includes(t) ||
          a.instructions.toLowerCase().includes(t) ||
          a.model.toLowerCase().includes(t)
        );
      }
      return true;
    });
  }, [agents, q, status]);

  const counts = useMemo(() => {
    const c = { all: agents.length, active: 0, mock: 0, draft: 0 };
    for (const a of agents) c[a.status] = (c[a.status] || 0) + 1;
    return c;
  }, [agents]);

  return (
    <div className="max-w-7xl mx-auto p-4 md:p-8">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold">Agent Kataloğu</h1>
          <p className="text-sm text-muted-foreground">
            Oluşturduğun tüm agent'lar — {agents.length} toplam
          </p>
        </div>
        <Button asChild variant="gradient">
          <Link to="/build">
            <Plus className="h-4 w-4" />
            Yeni Agent
          </Link>
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Ara: isim, açıklama, model..."
            className="pl-9"
          />
        </div>
        <div className="flex gap-1.5 rounded-lg border border-border bg-card/40 p-1">
          {(["all", "active", "mock", "draft"] as StatusFilter[]).map((s) => (
            <button
              key={s}
              onClick={() => setStatus(s)}
              className={cn(
                "px-3 py-1.5 rounded-md text-xs font-medium transition-all capitalize",
                status === s
                  ? "bg-primary/15 text-primary"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {s === "all" ? "Tümü" : s}{" "}
              <span className="ml-1 opacity-60">({counts[s]})</span>
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <AnimatePresence>
            {filtered.map((a, i) => (
              <motion.div
                key={a.id}
                layout
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ delay: i * 0.03 }}
              >
                <AgentCard agent={a} onOpen={() => setSelected(a)} />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      <AnimatePresence>
        {selected && <AgentDrawer agent={selected} onClose={() => setSelected(null)} />}
      </AnimatePresence>
    </div>
  );
}

function AgentCard({ agent, onOpen }: { agent: Agent; onOpen: () => void }) {
  const isMock = agent.status === "mock";
  return (
    <Card className="group hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5 transition-all">
      <CardContent className="p-5">
        <div className="flex items-start gap-3 mb-3">
          <div
            className={cn(
              "h-11 w-11 rounded-xl flex items-center justify-center shrink-0",
              isMock
                ? "bg-gradient-to-br from-warning/20 to-warning/5"
                : "bg-gradient-to-br from-primary/20 to-accent/10"
            )}
          >
            <Bot className={cn("h-5 w-5", isMock ? "text-warning" : "text-primary")} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-sm truncate">{agent.name}</h3>
              {agent.status === "mock" && (
                <Badge variant="warning" className="text-[9px] px-1.5 py-0">
                  mock
                </Badge>
              )}
              {agent.status === "active" && (
                <Badge variant="success" className="text-[9px] px-1.5 py-0">
                  aktif
                </Badge>
              )}
            </div>
            <div className="text-[10px] font-mono text-muted-foreground mt-0.5">
              {agent.model}
            </div>
          </div>
        </div>

        <p className="text-xs text-muted-foreground line-clamp-2 min-h-[32px] mb-3">
          {truncate(agent.instructions.replace(/\n/g, " "), 120) || "—"}
        </p>

        <div className="flex flex-wrap gap-1 mb-3 min-h-[22px]">
          {agent.tools.slice(0, 4).map((t, i) => (
            <span
              key={i}
              className="text-[9px] font-mono bg-muted/60 border border-border rounded px-1.5 py-0.5"
            >
              {t.type}
            </span>
          ))}
          {agent.tools.length > 4 && (
            <span className="text-[9px] text-muted-foreground">+{agent.tools.length - 4}</span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button asChild variant="gradient" size="sm" className="flex-1">
            <Link to={`/chat?agent=${encodeURIComponent(agent.id)}`}>
              <MessageSquare className="h-3.5 w-3.5" />
              Sohbet
            </Link>
          </Button>
          <Button variant="outline" size="sm" onClick={onOpen}>
            Detay
            <ChevronRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function AgentDrawer({ agent, onClose }: { agent: Agent; onClose: () => void }) {
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
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-primary/20 to-accent/10 flex items-center justify-center">
              <Bot className="h-5 w-5 text-primary" />
            </div>
            <div>
              <div className="font-semibold">{agent.name}</div>
              <div className="text-[10px] font-mono text-muted-foreground">{agent.id}</div>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="p-5 space-y-5">
          <Section icon={Cpu} title="Model & Kaynak">
            <div className="space-y-1.5 text-sm">
              <Row label="Model" value={agent.model} mono />
              <Row label="Kaynak" value={agent.source} mono />
              <Row label="Durum" value={agent.status} mono />
            </div>
          </Section>

          <Section icon={Wrench} title={`Araçlar (${agent.tools.length})`}>
            <div className="flex flex-wrap gap-1.5">
              {agent.tools.length === 0 ? (
                <span className="text-sm text-muted-foreground">Araç tanımlı değil</span>
              ) : (
                agent.tools.map((t, i) => (
                  <Badge key={i} variant="secondary" className="font-mono text-[10px]">
                    {t.type}
                  </Badge>
                ))
              )}
            </div>
          </Section>

          <Section icon={Sparkles} title="Instructions">
            <pre className="text-xs whitespace-pre-wrap font-mono bg-muted/30 border border-border rounded-lg p-3 max-h-80 overflow-y-auto scrollbar-thin">
              {agent.instructions || "(boş)"}
            </pre>
          </Section>

          <Button asChild variant="gradient" size="lg" className="w-full">
            <Link to={`/chat?agent=${encodeURIComponent(agent.id)}`}>
              <MessageSquare className="h-4 w-4" />
              Sohbet Başlat
            </Link>
          </Button>
        </div>
      </motion.div>
    </motion.div>
  );
}

function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: typeof Cpu;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
        <Icon className="h-3.5 w-3.5" />
        {title}
      </div>
      {children}
    </div>
  );
}

function Row({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className={cn("text-sm text-right", mono && "font-mono text-xs")}>{value}</span>
    </div>
  );
}

function EmptyState() {
  return (
    <Card>
      <CardContent className="p-12 text-center">
        <AlertCircle className="h-12 w-12 text-muted-foreground/40 mx-auto mb-3" />
        <h3 className="font-semibold mb-1">Agent bulunamadı</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Filtreleri temizleyin veya yeni bir agent oluşturun.
        </p>
        <Button asChild variant="gradient">
          <Link to="/build">
            <Plus className="h-4 w-4" />
            Yeni Agent Oluştur
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}

