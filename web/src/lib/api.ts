const API_BASE = "";

export interface AnalyzeResult {
  name: string;
  purpose: string;
  inferred_tools: string[];
  inferred_data_sources: string[];
  suggested_capabilities: string[];
  domain: string;
  complexity_hints: {
    needs_supervisor?: boolean;
    custom_state_required?: boolean;
    decision_points?: number;
    estimated_complexity?: "simple" | "moderate" | "complex";
  };
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

export interface PipelineStage {
  name: string;
  status: "pass" | "fail" | "pending" | "running";
  data: Record<string, unknown>;
}

export interface BuildResult {
  spec_id: string;
  spec: Record<string, unknown>;
  instructions: string;
  pipeline: {
    stages: PipelineStage[];
    review_summary: string;
    definition: Record<string, unknown>;
  };
  ready_for_approval: boolean;
  integrations: string[];
  graph: Record<string, unknown> | null;
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
}

export interface AnalyticsOverview {
  agents: { total: number; active: number; mock: number; draft: number };
  specs: { total: number; by_risk: Record<string, number> };
  tools: Record<string, number>;
}

async function jsonFetch<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json();
}

export const api = {
  health: () => jsonFetch<{ ok: boolean }>("/api/health"),

  analyze: (description: string) =>
    jsonFetch<AnalyzeResult>("/api/builder/analyze", {
      method: "POST",
      body: JSON.stringify({ description }),
    }),

  build: (payload: BuildPayload) =>
    jsonFetch<BuildResult>("/api/builder/build", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  deploy: (spec_id: string) =>
    jsonFetch<DeployResult>("/api/builder/deploy", {
      method: "POST",
      body: JSON.stringify({ spec_id }),
    }),

  agents: () => jsonFetch<Agent[]>("/api/agents"),
  agent: (id: string) => jsonFetch<Agent>(`/api/agents/${id}`),

  chat: (agent_id: string, session_id: string, message: string) =>
    jsonFetch<{ content: string }>("/api/agents/chat", {
      method: "POST",
      body: JSON.stringify({ agent_id, session_id, message }),
    }),

  templates: () => jsonFetch<Template[]>("/api/templates"),
  template: (id: string) => jsonFetch<Template>(`/api/templates/${id}`),
  buildFromTemplate: (template_id: string, overrides: Record<string, unknown> = {}) =>
    jsonFetch<BuildResult>("/api/templates/build", {
      method: "POST",
      body: JSON.stringify({ template_id, overrides }),
    }),

  analytics: () => jsonFetch<AnalyticsOverview>("/api/analytics/overview"),
  cost: () => jsonFetch<Record<string, unknown>>("/api/analytics/cost"),
  toolCatalog: () => jsonFetch<Record<string, unknown>>("/api/analytics/tool-catalog"),
};

/** Chat streaming via SSE — returns cancel function. */
export function streamChat(
  payload: { agent_id: string; session_id: string; message: string },
  handlers: {
    onChunk: (text: string) => void;
    onDone: (full: string) => void;
    onError: (err: string) => void;
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
      if (!res.ok || !res.body) {
        handlers.onError(`HTTP ${res.status}`);
        return;
      }
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
          const lines = part.split("\n");
          let event = "message";
          let data = "";
          for (const line of lines) {
            if (line.startsWith("event: ")) event = line.slice(7).trim();
            else if (line.startsWith("data: ")) data = line.slice(6);
          }
          if (!data) continue;
          try {
            const obj = JSON.parse(data);
            if (event === "chunk") handlers.onChunk(obj.text || "");
            else if (event === "done") handlers.onDone(obj.full || "");
            else if (event === "error") handlers.onError(obj.message || "hata");
          } catch {
            // ignore
          }
        }
      }
    })
    .catch((e) => {
      if (e.name !== "AbortError") handlers.onError(String(e));
    });

  return () => ctrl.abort();
}

/** Build streaming via SSE. */
export function streamBuild(
  payload: BuildPayload,
  handlers: {
    onStage: (stage: { name: string; status: string; data?: unknown; message?: string }) => void;
    onResult: (result: BuildResult) => void;
    onError: (err: string) => void;
    onDone: () => void;
  }
): () => void {
  const ctrl = new AbortController();

  fetch("/api/builder/build/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: ctrl.signal,
  })
    .then(async (res) => {
      if (!res.ok || !res.body) {
        handlers.onError(`HTTP ${res.status}`);
        return;
      }
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
          const lines = part.split("\n");
          let event = "message";
          let data = "";
          for (const line of lines) {
            if (line.startsWith("event: ")) event = line.slice(7).trim();
            else if (line.startsWith("data: ")) data = line.slice(6);
          }
          if (!data) continue;
          try {
            const obj = JSON.parse(data);
            if (event === "stage") handlers.onStage(obj);
            else if (event === "result") handlers.onResult(obj);
            else if (event === "done") handlers.onDone();
            else if (event === "error") handlers.onError(obj.message || "hata");
          } catch {
            // ignore
          }
        }
      }
    })
    .catch((e) => {
      if (e.name !== "AbortError") handlers.onError(String(e));
    });

  return () => ctrl.abort();
}
