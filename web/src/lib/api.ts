export interface AnalyzeResult {
  name: string;
  purpose: string;
  inferred_tools: string[];
  inferred_data_sources: string[];
  suggested_capabilities: string[];
  domain: string;
  complexity_hints: Record<string, unknown>;
}

export interface BuildPayload {
  description: string;
  name: string;
  purpose: string;
  audience: string;
  tone: string;
  output_format: string;
  scope: string;
  pii: string;
  approval: string;
  example_scenario: string;
  inferred_tools: string[];
  inferred_data_sources: string[];
  suggested_capabilities: string[];
  complexity_hints: Record<string, unknown>;
}

export interface BuildResult {
  spec_id: string;
  spec: Record<string, unknown>;
  instructions: string;
  pipeline: {
    stages: Array<{ name: string; status: string; data: Record<string, unknown> }>;
    review_summary: string;
    definition: Record<string, unknown>;
  };
  ready_for_approval: boolean;
  integrations: string[];
}

export interface Agent {
  id: string;
  name: string;
  model: string;
  instructions: string;
  tools: Array<{ type: string }>;
  metadata: Record<string, unknown>;
  source: string;
  status: "active" | "mock" | "draft";
}

export interface Template {
  id: string;
  name: string;
  emoji: string;
  category: string;
  description: string;
  purpose: string;
  audience: string;
  tone: string;
  output_format: string;
  scope: string;
  pii: string;
  approval: string;
  tools: string[];
  data_sources: string[];
  capabilities: string[];
  example_scenario: string;
}

export interface DeployResult {
  success: boolean;
  foundry_agent_id: string | null;
  name: string | null;
  mock: boolean;
  error: string | null;
  application_updated?: boolean;
  application_update_error?: string | null;
  workflow_update?: Record<string, unknown> | null;
}

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text().catch(() => "")}`);
  return res.json();
}

export const api = {
  analyze: (description: string) =>
    j<AnalyzeResult>("/api/builder/analyze", {
      method: "POST",
      body: JSON.stringify({ description }),
    }),
  build: (payload: BuildPayload) =>
    j<BuildResult>("/api/builder/build", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deploy: (spec_id: string) =>
    j<DeployResult>("/api/builder/deploy", {
      method: "POST",
      body: JSON.stringify({ spec_id }),
    }),
  agents: () => j<Agent[]>("/api/agents"),
  templates: () => j<Template[]>("/api/templates"),
  buildFromTemplate: (template_id: string) =>
    j<BuildResult>("/api/templates/build", {
      method: "POST",
      body: JSON.stringify({ template_id, overrides: {} }),
    }),
};

export interface OrchestrationStep {
  type: "routing" | "agent_start" | "agent_done" | "synthesis" | "chunk" | "done" | "error";
  agent?: string;
  selected?: string[];
  text?: string;
  full?: string;
  message?: string;
}

export function streamOrchestrate(
  payload: { agent_id: string; session_id: string; message: string },
  handlers: {
    onStep: (step: OrchestrationStep) => void;
    onChunk: (t: string) => void;
    onDone: (full: string) => void;
    onError: (e: string) => void;
  }
): () => void {
  const ctrl = new AbortController();

  fetch("/api/agents/chat/orchestrate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: ctrl.signal,
  })
    .then(async (res) => {
      if (!res.ok || !res.body) return handlers.onError(`HTTP ${res.status}`);
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop() || "";
        for (const part of parts) {
          let event = "message";
          let data = "";
          for (const line of part.split("\n")) {
            if (line.startsWith("event: ")) event = line.slice(7).trim();
            else if (line.startsWith("data: ")) data = line.slice(6);
          }
          if (!data) continue;
          try {
            const o = JSON.parse(data);
            if (event === "chunk") handlers.onChunk(o.text || "");
            else if (event === "done") handlers.onDone(o.full || "");
            else if (event === "error") handlers.onError(o.message || "hata");
            else handlers.onStep({ type: event as OrchestrationStep["type"], ...o });
          } catch {}
        }
      }
    })
    .catch((e) => e.name !== "AbortError" && handlers.onError(String(e)));

  return () => ctrl.abort();
}

export function streamChat(
  payload: { agent_id: string; session_id: string; message: string },
  handlers: {
    onChunk: (t: string) => void;
    onDone: (full: string) => void;
    onError: (e: string) => void;
  }
): () => void {
  const ctrl = new AbortController();

  fetch("/api/agents/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: ctrl.signal,
  })
    .then(async (res) => {
      if (!res.ok || !res.body) return handlers.onError(`HTTP ${res.status}`);
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop() || "";
        for (const part of parts) {
          let event = "message";
          let data = "";
          for (const line of part.split("\n")) {
            if (line.startsWith("event: ")) event = line.slice(7).trim();
            else if (line.startsWith("data: ")) data = line.slice(6);
          }
          if (!data) continue;
          try {
            const o = JSON.parse(data);
            if (event === "chunk") handlers.onChunk(o.text || "");
            else if (event === "done") handlers.onDone(o.full || "");
            else if (event === "error") handlers.onError(o.message || "hata");
          } catch {}
        }
      }
    })
    .catch((e) => e.name !== "AbortError" && handlers.onError(String(e)));

  return () => ctrl.abort();
}
