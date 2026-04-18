import { create } from "zustand";
import type { Agent, AnalyticsOverview, Template } from "@/lib/api";

interface AppState {
  agents: Agent[];
  templates: Template[];
  analytics: AnalyticsOverview | null;
  loading: {
    agents: boolean;
    templates: boolean;
    analytics: boolean;
  };
  setAgents: (a: Agent[]) => void;
  setTemplates: (t: Template[]) => void;
  setAnalytics: (a: AnalyticsOverview) => void;
  setLoading: (key: keyof AppState["loading"], v: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  agents: [],
  templates: [],
  analytics: null,
  loading: { agents: false, templates: false, analytics: false },
  setAgents: (agents) => set({ agents }),
  setTemplates: (templates) => set({ templates }),
  setAnalytics: (analytics) => set({ analytics }),
  setLoading: (key, v) =>
    set((s) => ({ loading: { ...s.loading, [key]: v } })),
}));
