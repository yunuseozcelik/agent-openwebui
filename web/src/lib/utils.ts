import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatRelative(iso: string | number | Date): string {
  const d = new Date(iso);
  const diff = Date.now() - d.getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return "az önce";
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}dk önce`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}sa önce`;
  const days = Math.floor(h / 24);
  if (days < 30) return `${days}g önce`;
  return d.toLocaleDateString("tr-TR");
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
