import { Link } from "react-router-dom";
import { ArrowRight, Bot, Pencil, Plus } from "lucide-react";
import { useStore } from "@/store";
import { Button, Card } from "@/components/ui";
import { truncate } from "@/lib/utils";

const SEED_NAMES = new Set([
  "Supervisor-Agent", "Synthesis-Agent",
  "HR-Agent", "IT-Agent", "Finance-Agent",
  "Math-Agent", "General-Agent", "Chat-Agent",
]);

export function Agents() {
  const agents = useStore((s) => s.agents);
  const me = useStore((s) => s.me);

  return (
    <div className="max-w-3xl mx-auto px-6 md:px-10 py-14 md:py-20">
      <div className="flex items-end justify-between mb-2">
        <h1 className="text-3xl font-semibold tracking-tight">Agent'lar</h1>
        <Link to="/build">
          <Button size="sm">
            <Plus className="h-4 w-4" /> Yeni
          </Button>
        </Link>
      </div>
      {me && (
        <div className="mb-6 text-[12px] text-subtle">
          <span className="inline-flex items-center rounded-full border border-border bg-white px-2 py-0.5 font-medium text-ink">
            {me.roles.join(" · ")}
          </span>{" "}
          · {agents.length} agent görünür (rolünüze göre filtrelendi)
        </div>
      )}

      {agents.length === 0 ? (
        <Card className="p-12 text-center">
          <Bot className="h-6 w-6 text-subtle mx-auto mb-3" />
          <div className="text-sm text-muted mb-4">Bu rol için erişilebilir agent yok</div>
          <Link to="/build">
            <Button size="sm">Oluştur</Button>
          </Link>
        </Card>
      ) : (
        <div className="space-y-1.5">
          {agents.map((a) => (
            <div key={a.id} className="flex items-center gap-1">
              <Link
                to={`/chat?agent=${encodeURIComponent(a.id)}`}
                className="flex-1 flex items-center gap-3 rounded-lg border border-border bg-white px-4 py-3.5 hover:border-ink transition-colors group"
              >
                <Bot className="h-4 w-4 text-muted shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-[14px] font-medium truncate flex items-center gap-2">
                    {a.name}
                    {a.status === "mock" && (
                      <span className="text-[10px] font-normal text-subtle">mock</span>
                    )}
                    {!!a.metadata?.parent_agent_name && (
                      <span className="text-[10px] font-normal text-amber-600">
                        ↳ {String(a.metadata.parent_agent_name)}
                      </span>
                    )}
                  </div>
                  <div className="text-[12px] text-muted truncate">
                    {truncate(a.instructions.replace(/\n/g, " "), 100) || a.model}
                  </div>
                </div>
                <ArrowRight className="h-4 w-4 text-subtle group-hover:text-ink transition-colors" />
              </Link>
              <Link
                to={`/agents/${encodeURIComponent(a.id)}/edit`}
                title="Düzenle"
                className="p-2 rounded-lg border border-border bg-white hover:border-ink transition-colors text-muted hover:text-ink"
              >
                <Pencil className="h-3.5 w-3.5" />
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
