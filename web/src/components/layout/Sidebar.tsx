import { NavLink, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Bot,
  LayoutDashboard,
  LayoutTemplate,
  MessageSquare,
  Plus,
  Settings,
  Sparkles,
  Activity,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", label: "Panel", icon: LayoutDashboard },
  { to: "/build", label: "Yeni Agent", icon: Plus, highlight: true },
  { to: "/agents", label: "Agent'lar", icon: Bot },
  { to: "/templates", label: "Şablonlar", icon: LayoutTemplate },
  { to: "/chat", label: "Sohbet", icon: MessageSquare },
  { to: "/analytics", label: "Analitik", icon: Activity },
  { to: "/settings", label: "Ayarlar", icon: Settings },
];

export function Sidebar() {
  const { pathname } = useLocation();

  return (
    <aside className="hidden md:flex h-screen w-64 shrink-0 flex-col border-r border-border/50 bg-card/30 backdrop-blur-xl">
      {/* Brand */}
      <div className="px-5 pt-6 pb-4">
        <div className="flex items-center gap-2.5">
          <div className="relative h-9 w-9 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center shadow-lg shadow-primary/25">
            <Sparkles className="h-5 w-5 text-white" strokeWidth={2.5} />
            <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-primary to-accent opacity-40 blur-md -z-10" />
          </div>
          <div className="leading-tight">
            <div className="font-bold text-sm gradient-text animate-gradient-shift">
              Agent Factory
            </div>
            <div className="text-[10px] text-muted-foreground tracking-wide uppercase">
              v2.0 • Azure Foundry
            </div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto scrollbar-thin px-3 py-2 space-y-0.5">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.to || (item.to !== "/" && pathname.startsWith(item.to));
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={cn(
                "relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all group",
                active
                  ? "text-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent/5",
                item.highlight && !active && "text-primary"
              )}
            >
              {active && (
                <motion.div
                  layoutId="sidebar-active"
                  className={cn(
                    "absolute inset-0 rounded-lg",
                    item.highlight
                      ? "bg-gradient-to-r from-primary/20 via-primary/10 to-accent/20 border border-primary/30"
                      : "bg-accent/10 border border-border/60"
                  )}
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}
              <Icon
                className={cn(
                  "h-4 w-4 relative z-10 transition-transform",
                  item.highlight && "text-primary",
                  "group-hover:scale-110"
                )}
              />
              <span className="relative z-10">{item.label}</span>
              {item.highlight && !active && (
                <span className="ml-auto relative z-10">
                  <span className="inline-flex h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-border/50">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <kbd className="inline-flex items-center rounded border border-border bg-muted/60 px-1.5 py-0.5 text-[10px] font-mono">
            ⌘K
          </kbd>
          <span>komut paleti</span>
        </div>
      </div>
    </aside>
  );
}
