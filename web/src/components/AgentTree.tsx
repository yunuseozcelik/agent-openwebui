import { useStore } from "@/store";
import { type Agent } from "@/lib/api";
import { cn } from "@/lib/utils";

const SEED_CHILDREN = ["HR-Agent","IT-Agent","Finance-Agent","Math-Agent","General-Agent","Chat-Agent"];
const SUPERVISOR    = "Supervisor-Agent";
const SYNTHESIS     = "Synthesis-Agent";
const HIDDEN        = new Set(["FNSS","FNSS-Workflow"]);

function parentOf(agent: Agent): string {
  const p = agent.metadata?.parent_agent_name as string | undefined;
  if (p && p.trim()) return p.trim();
  return SUPERVISOR;
}

function NodeBox({ label, variant }: {
  label: string;
  variant: "supervisor" | "seed" | "custom" | "synthesis";
}) {
  const styles: Record<string, string> = {
    supervisor: "bg-violet-100 border-violet-400 text-violet-800 font-semibold",
    seed:       "bg-slate-50 border-slate-300 text-slate-500",
    custom:     "bg-amber-50 border-amber-300 text-amber-800",
    synthesis:  "bg-blue-50 border-blue-300 text-blue-700 font-semibold",
  };
  const short = label.length > 16 ? label.slice(0, 15) + "…" : label;
  return (
    <div title={label} className={cn(
      "rounded-lg border px-3 py-1.5 text-[11px] whitespace-nowrap",
      styles[variant]
    )}>
      {short}
    </div>
  );
}

function VLine({ h = "h-4" }: { h?: string }) {
  return <div className={cn("w-px bg-slate-200 mx-auto", h)} />;
}

function HBar({ count }: { count: number }) {
  if (count <= 1) return null;
  return <div className="h-px bg-slate-200 w-full" />;
}

export function AgentTree() {
  const agents = useStore((s) => s.agents);
  if (agents.length === 0) return null;

  const visible = agents.filter((a) => !HIDDEN.has(a.name));
  const byName  = Object.fromEntries(visible.map((a) => [a.name, a]));

  const supervisor = byName[SUPERVISOR];
  const synthesis  = byName[SYNTHESIS];

  const seedAgents = visible.filter((a) => SEED_CHILDREN.includes(a.name));

  const customAgents = visible.filter(
    (a) => !SEED_CHILDREN.includes(a.name) && a.name !== SUPERVISOR && a.name !== SYNTHESIS
  );

  // Group custom agents by their parent seed
  const childrenOf: Record<string, Agent[]> = {};
  for (const agent of customAgents) {
    const p = parentOf(agent);
    childrenOf[p] = [...(childrenOf[p] ?? []), agent];
  }

  const hasAnyChildren = seedAgents.some((s) => (childrenOf[s.name] ?? []).length > 0);

  return (
    <div className="overflow-x-auto">
      <p className="text-[10px] uppercase tracking-widest text-muted mb-4 text-center">
        Mevcut Ekosistem
      </p>

      <div className="flex flex-col items-center min-w-max mx-auto">

        {/* Supervisor */}
        {supervisor && (
          <>
            <NodeBox label={SUPERVISOR} variant="supervisor" />
            <VLine />
          </>
        )}

        {/* Seeds row — each column shows seed + its custom children */}
        {seedAgents.length > 0 && (
          <div className="relative flex gap-5 items-start">
            {/* Horizontal connector bar at top (only when multiple seeds) */}
            {seedAgents.length > 1 && (
              <div className="absolute top-0 left-[50%] right-[50%] h-px bg-slate-200"
                   style={{ left: "calc(50% / " + seedAgents.length + ")", right: "calc(50% / " + seedAgents.length + ")" }}
              />
            )}

            {seedAgents.map((seed) => {
              const kids = childrenOf[seed.name] ?? [];
              return (
                <div key={seed.id} className="flex flex-col items-center gap-0">
                  <NodeBox label={seed.name} variant="seed" />
                  {kids.map((child) => (
                    <div key={child.id} className="flex flex-col items-center">
                      <VLine h="h-3" />
                      <NodeBox label={child.name} variant="custom" />
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        )}

        {/* Synthesis */}
        {synthesis && (
          <>
            <VLine h={hasAnyChildren ? "h-6" : "h-4"} />
            <NodeBox label={SYNTHESIS} variant="synthesis" />
          </>
        )}
      </div>

      {/* Legend */}
      <div className="mt-5 flex flex-wrap gap-x-4 gap-y-1 justify-center">
        {[
          { color: "bg-violet-400", label: "Supervisor" },
          { color: "bg-slate-300",  label: "Seed" },
          { color: "bg-amber-300",  label: "Özel" },
          { color: "bg-blue-300",   label: "Synthesis" },
        ].map(({ color, label }) => (
          <div key={label} className="flex items-center gap-1.5 text-[10px] text-muted">
            <span className={cn("w-2.5 h-2.5 rounded-sm", color)} />
            {label}
          </div>
        ))}
      </div>
    </div>
  );
}
