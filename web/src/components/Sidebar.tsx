import { NavLink } from "react-router-dom";
import { Home, Plus, Bot, MessageSquare, LayoutTemplate } from "lucide-react";
import { cn } from "@/lib/utils";

const items = [
  { to: "/", label: "Panel", icon: Home, end: true },
  { to: "/build", label: "Yeni Agent", icon: Plus },
  { to: "/agents", label: "Agent'lar", icon: Bot },
  { to: "/templates", label: "Şablonlar", icon: LayoutTemplate },
  { to: "/chat", label: "Sohbet", icon: MessageSquare },
];

export function Sidebar() {
  return (
    <aside className="hidden md:flex w-56 shrink-0 flex-col border-r border-border bg-surface">
      <div className="px-5 pt-6 pb-8">
        <div className="text-[15px] font-semibold tracking-tight">
          Agent Factory
        </div>
      </div>

      <nav className="px-2 flex-1 space-y-0.5">
        {items.map((it) => {
          const Icon = it.icon;
          return (
            <NavLink
              key={it.to}
              to={it.to}
              end={it.end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2.5 rounded-lg px-3 h-9 text-[13.5px] font-medium transition-colors",
                  isActive
                    ? "bg-white text-ink border border-border"
                    : "text-muted hover:text-ink hover:bg-white/60"
                )
              }
            >
              <Icon className="h-[15px] w-[15px]" strokeWidth={2} />
              {it.label}
            </NavLink>
          );
        })}
      </nav>

      <div className="px-5 py-4 text-[11px] text-subtle">
        Azure AI Foundry
      </div>
    </aside>
  );
}
