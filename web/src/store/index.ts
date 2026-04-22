import { create } from "zustand";
import type { Agent, Template } from "@/lib/api";

export interface UserProfile {
  email: string;
  name: string;
  department: string;
  title: string;
  roles: string[];
}

export interface MeResponse extends UserProfile {
  allowed_parents: string[];
  extra_agents: string[];
}

const USER_KEY = "currentUserEmail";

function loadInitialUser(): string | null {
  try {
    return localStorage.getItem(USER_KEY);
  } catch {
    return null;
  }
}

interface State {
  agents: Agent[];
  templates: Template[];
  users: UserProfile[];
  currentUserEmail: string | null;
  me: MeResponse | null;
  setAgents: (a: Agent[]) => void;
  setTemplates: (t: Template[]) => void;
  setUsers: (u: UserProfile[]) => void;
  setCurrentUser: (email: string | null) => void;
  setMe: (m: MeResponse | null) => void;
}

export const useStore = create<State>((set) => ({
  agents: [],
  templates: [],
  users: [],
  currentUserEmail: loadInitialUser(),
  me: null,
  setAgents: (agents) => set({ agents }),
  setTemplates: (templates) => set({ templates }),
  setUsers: (users) => set({ users }),
  setCurrentUser: (email) => {
    try {
      if (email) localStorage.setItem(USER_KEY, email);
      else localStorage.removeItem(USER_KEY);
    } catch {}
    set({ currentUserEmail: email });
  },
  setMe: (me) => set({ me }),
}));

export function getCurrentUserEmail(): string | null {
  return useStore.getState().currentUserEmail;
}
