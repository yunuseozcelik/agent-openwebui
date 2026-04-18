import { create } from "zustand";
import type { Agent, Template } from "@/lib/api";

interface State {
  agents: Agent[];
  templates: Template[];
  setAgents: (a: Agent[]) => void;
  setTemplates: (t: Template[]) => void;
}

export const useStore = create<State>((set) => ({
  agents: [],
  templates: [],
  setAgents: (agents) => set({ agents }),
  setTemplates: (templates) => set({ templates }),
}));
