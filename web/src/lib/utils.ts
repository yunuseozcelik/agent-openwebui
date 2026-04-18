import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function truncate(s: string, n = 120): string {
  if (!s) return "";
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

export function getSessionId(): string {
  const k = "af_session_id";
  let id = localStorage.getItem(k);
  if (!id) {
    id = `sess_${Math.random().toString(36).slice(2, 14)}`;
    localStorage.setItem(k, id);
  }
  return id;
}
