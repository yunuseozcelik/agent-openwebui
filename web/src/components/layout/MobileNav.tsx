import { NavLink, useLocation } from "react-router-dom";
import { Bot, LayoutDashboard, LayoutTemplate, MessageSquare, Plus } from "lucide-react";
import { cn } from "@/lib/utils";

const items = [
  { to: "/", label: "Panel", icon: LayoutDashboard },
  { to: "/agents", label: "Agent", icon: Bot },
  { to: "/build", label: "Oluştur", icon: Plus, highlight: true },
  { to: "/templates", label: "Şablon", icon: LayoutTemplate },
  { to: "/chat", label: "Sohbet", icon: MessageSquare },
];

export function MobileNav() {
  const { pathname } = useLocation();

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 flex border-t border-border/60 bg-card/90 backdrop-blur-xl">
      {items.map((item) => {
        const Icon = item.icon;
        const active = pathname === item.to || (item.to !== "/" && pathname.startsWith(item.to));
        return (
          <NavLink
            key={item.to}
            to={item.to}
            className={cn(
              "flex-1 flex flex-col items-center justify-center gap-1 py-2.5 text-[10px] font-medium transition-colors",
              active ? "text-primary" : "text-muted-foreground",
              item.highlight && "relative"
            )}
          >
            {item.highlight ? (
              <div
                className={cn(
                  "flex items-center justify-center h-10 w-10 rounded-full",
                  "bg-gradient-to-br from-primary to-accent shadow-lg shadow-primary/30",
                  active && "ring-2 ring-primary/40"
                )}
              >
                <Icon className="h-5 w-5 text-white" />
              </div>
            ) : (
              <Icon className={cn("h-5 w-5", active && "scale-110")} />
            )}
            <span>{item.label}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}
