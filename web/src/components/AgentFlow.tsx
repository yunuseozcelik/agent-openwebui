import { useCallback, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  type Node,
  type Edge,
  Position,
  Handle,
  useNodesState,
  useEdgesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useNavigate } from "react-router-dom";
import { useStore } from "@/store";
import { type Agent } from "@/lib/api";

const SEED_NAMES = new Set([
  "HR-Agent", "IT-Agent", "Finance-Agent",
  "Math-Agent", "General-Agent", "Chat-Agent",
]);
const SUPERVISOR = "Supervisor-Agent";
const SYNTHESIS  = "Synthesis-Agent";
const HIDDEN     = new Set(["FNSS", "FNSS-Workflow"]);

function parentOf(agent: Agent): string {
  const p = agent.metadata?.parent_agent_name as string | undefined;
  if (p && p.trim()) return p.trim();
  return SUPERVISOR;
}

// ── Custom node components ──────────────────────────────────────────────────

function SupervisorNode({ data }: { data: { label: string } }) {
  return (
    <div className="rounded-xl border-2 border-violet-400 bg-violet-50 px-4 py-2 text-[12px] font-semibold text-violet-800 shadow-sm min-w-[130px] text-center">
      <Handle type="source" position={Position.Bottom} style={{ background: "#a78bfa" }} />
      {data.label}
    </div>
  );
}

function SeedNode({ data }: { data: { label: string } }) {
  return (
    <div className="rounded-xl border border-slate-300 bg-slate-50 px-3 py-1.5 text-[11px] text-slate-500 shadow-sm min-w-[110px] text-center cursor-pointer hover:border-slate-400 transition-colors">
      <Handle type="target" position={Position.Top} style={{ background: "#94a3b8" }} />
      <Handle type="source" position={Position.Bottom} style={{ background: "#94a3b8" }} />
      {data.label}
    </div>
  );
}

function CustomNode({ data }: { data: { label: string; onClick?: () => void } }) {
  return (
    <div
      onClick={data.onClick}
      className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-1.5 text-[11px] text-amber-800 shadow-sm min-w-[110px] text-center cursor-pointer hover:border-amber-500 hover:shadow-md transition-all"
    >
      <Handle type="target" position={Position.Top} style={{ background: "#fbbf24" }} />
      {data.label}
    </div>
  );
}

function SynthesisNode({ data }: { data: { label: string } }) {
  return (
    <div className="rounded-xl border-2 border-blue-300 bg-blue-50 px-4 py-2 text-[12px] font-semibold text-blue-700 shadow-sm min-w-[130px] text-center">
      <Handle type="target" position={Position.Top} style={{ background: "#60a5fa" }} />
      {data.label}
    </div>
  );
}

function PreviewNode({ data }: { data: { label: string } }) {
  return (
    <div className="rounded-xl border-2 border-dashed border-emerald-500 bg-emerald-100 px-4 py-2 text-[12px] font-semibold text-emerald-800 shadow-lg min-w-[130px] text-center ring-4 ring-emerald-200 animate-pulse">
      <Handle type="target" position={Position.Top} style={{ background: "#10b981" }} />
      ✦ {data.label}
      <div className="text-[9px] font-normal text-emerald-700 mt-0.5">yeni eklenecek</div>
    </div>
  );
}

const nodeTypes = {
  supervisor: SupervisorNode,
  seed: SeedNode,
  custom: CustomNode,
  synthesis: SynthesisNode,
  preview: PreviewNode,
};

// ── Layout constants ────────────────────────────────────────────────────────

const X_GAP   = 160;
const Y_SEED  = 120;
const Y_CHILD = 220;
const Y_SYNTH = 340;

// ── Main component ──────────────────────────────────────────────────────────

interface AgentFlowProps {
  /** Optional: show a ghost "preview" node for a new agent being configured */
  previewAgent?: { name: string; parentName?: string };
  /** Height of the flow canvas */
  height?: number;
}

export function AgentFlow({ previewAgent, height = 400 }: AgentFlowProps) {
  const agents  = useStore((s) => s.agents);
  const navigate = useNavigate();

  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    const visible = agents.filter((a) => !HIDDEN.has(a.name));
    const byName  = Object.fromEntries(visible.map((a) => [a.name, a]));

    const supervisor = byName[SUPERVISOR];
    const synthesis  = byName[SYNTHESIS];
    const seeds = visible.filter((a) => SEED_NAMES.has(a.name));

    const customAgents = visible.filter(
      (a) => !SEED_NAMES.has(a.name) && a.name !== SUPERVISOR && a.name !== SYNTHESIS
    );

    const childrenOf: Record<string, Agent[]> = {};
    for (const agent of customAgents) {
      const p = parentOf(agent);
      childrenOf[p] = [...(childrenOf[p] ?? []), agent];
    }

    // Add preview node as virtual child
    const previewParent = previewAgent?.parentName ?? SUPERVISOR;
    if (previewAgent) {
      childrenOf[previewParent] = [
        ...(childrenOf[previewParent] ?? []),
        {
          id: "__preview__",
          name: previewAgent.name,
          model: "",
          instructions: "",
          tools: [],
          metadata: {},
          source: "preview",
          status: "draft",
        } as Agent,
      ];
    }

    const nodes: Node[] = [];
    const edges: Edge[] = [];

    // Total width for centering
    const totalWidth = Math.max(seeds.length, 1) * X_GAP;
    const centerX = totalWidth / 2;

    // Supervisor node
    if (supervisor) {
      nodes.push({
        id: SUPERVISOR,
        type: "supervisor",
        position: { x: centerX - 65, y: 0 },
        data: { label: SUPERVISOR },
      });
    }

    // Seed nodes + edges from supervisor
    seeds.forEach((seed, i) => {
      const x = i * X_GAP;
      nodes.push({
        id: seed.name,
        type: "seed",
        position: { x, y: Y_SEED },
        data: { label: seed.name },
      });
      if (supervisor) {
        edges.push({
          id: `sup-${seed.name}`,
          source: SUPERVISOR,
          target: seed.name,
          style: { stroke: "#c4b5fd", strokeWidth: 1.5 },
          animated: false,
        });
      }

      // Custom children of this seed
      const kids = childrenOf[seed.name] ?? [];
      kids.forEach((child, j) => {
        const childX = x + (j - (kids.length - 1) / 2) * 130;
        const isPreview = child.id === "__preview__";
        nodes.push({
          id: child.id,
          type: isPreview ? "preview" : "custom",
          position: { x: childX, y: Y_CHILD + j * 60 },
          data: {
            label: child.name.length > 16 ? child.name.slice(0, 15) + "…" : child.name,
            onClick: isPreview ? undefined : () => navigate(`/agents/${encodeURIComponent(child.id)}/edit`),
          },
        });
        edges.push({
          id: `${seed.name}-${child.id}`,
          source: seed.name,
          target: child.id,
          style: { stroke: "#fcd34d", strokeWidth: 1.5 },
        });
      });
    });

    // Synthesis node
    if (synthesis) {
      const maxChildY = Object.values(childrenOf).flat().length > 0 ? Y_SYNTH + 40 : Y_SYNTH;
      nodes.push({
        id: SYNTHESIS,
        type: "synthesis",
        position: { x: centerX - 65, y: maxChildY },
        data: { label: SYNTHESIS },
      });
      // Edge from last seed row to synthesis (visual only — from center)
      if (seeds.length > 0) {
        edges.push({
          id: `synth-in`,
          source: seeds[Math.floor(seeds.length / 2)]?.name ?? SUPERVISOR,
          target: SYNTHESIS,
          style: { stroke: "#93c5fd", strokeWidth: 1.5, strokeDasharray: "4 2" },
        });
      }
    }

    return { nodes, edges };
  }, [agents, previewAgent, navigate]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  // Refresh nodes when agents change
  const memoNodes = useMemo(() => initialNodes, [initialNodes]);
  const memoEdges = useMemo(() => initialEdges, [initialEdges]);

  return (
    <div style={{ height }} className="rounded-xl border border-border overflow-hidden bg-surface">
      <ReactFlow
        nodes={memoNodes}
        edges={memoEdges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnScroll
        zoomOnScroll={false}
        minZoom={0.4}
        maxZoom={1.5}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#e2e8f0" gap={20} size={1} />
        <Controls showInteractive={false} />
      </ReactFlow>

      {/* Legend */}
      <div className="absolute bottom-2 left-2 flex flex-wrap gap-x-3 gap-y-0.5 text-[9px] text-muted bg-white/80 px-2 py-1 rounded-lg border border-border">
        {[
          { color: "bg-violet-300", label: "Supervisor" },
          { color: "bg-slate-300",  label: "Seed" },
          { color: "bg-amber-300",  label: "Özel" },
          { color: "bg-blue-300",   label: "Synthesis" },
          ...(previewAgent ? [{ color: "bg-green-400 animate-pulse", label: "Yeni ✦" }] : []),
        ].map(({ color, label }) => (
          <span key={label} className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-full ${color}`} />
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}
