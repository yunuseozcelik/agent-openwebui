import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { Home, Plus, Bot, MessageSquare, LayoutTemplate, User as UserIcon, Shield, UserPlus, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { useStore } from "@/store";
import { RegisterModal } from "@/components/RegisterModal";

const baseItems = [
  { to: "/", label: "Panel", icon: Home, end: true },
  { to: "/build", label: "Yeni Agent", icon: Plus },
  { to: "/agents", label: "Agent'lar", icon: Bot },
  { to: "/templates", label: "Şablonlar", icon: LayoutTemplate },
  { to: "/chat", label: "Sohbet", icon: MessageSquare },
  { to: "/dashboard", label: "Dashboard", icon: BarChart3 },
];

export function Sidebar() {
  const users = useStore((s) => s.users);
  const setUsers = useStore((s) => s.setUsers);
  const currentUserEmail = useStore((s) => s.currentUserEmail);
  const setCurrentUser = useStore((s) => s.setCurrentUser);
  const me = useStore((s) => s.me);
  const setMe = useStore((s) => s.setMe);
  const setAgents = useStore((s) => s.setAgents);
  const [registerOpen, setRegisterOpen] = useState(false);

  const isAdmin = !!me?.roles?.includes("admin");
  const items = isAdmin
    ? [...baseItems, { to: "/admin", label: "Admin", icon: Shield }]
    : baseItems;

  // Kullanici listesini bir kez yukle
  useEffect(() => {
    api.users().then(setUsers).catch(() => {});
  }, [setUsers]);

  // Default kullanici
  useEffect(() => {
    if (!currentUserEmail && users.length > 0) {
      setCurrentUser(users[0].email);
    }
  }, [users, currentUserEmail, setCurrentUser]);

  // me + agents + users'i kullanici degistiginde tekrar cek
  useEffect(() => {
    if (!currentUserEmail) return;
    api.me().then(setMe).catch(() => setMe(null));
    api.agents().then(setAgents).catch(() => {});
    api.users().then(setUsers).catch(() => {});
  }, [currentUserEmail, setMe, setAgents, setUsers]);

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

      {/* Kullanici secici */}
      <div className="px-3 py-3 border-t border-border bg-white/40">
        <div className="flex items-center gap-1.5 mb-1.5">
          <UserIcon className="h-3 w-3 text-muted" />
          <span className="text-[10px] uppercase tracking-widest text-muted">Rol</span>
        </div>
        <div className="flex items-center gap-1 w-full">
          <select
            value={currentUserEmail ?? ""}
            onChange={(e) => setCurrentUser(e.target.value || null)}
            className="min-w-0 flex-1 rounded-lg border border-border bg-white px-2 py-1.5 text-[12px]"
          >
            {users.map((u) => {
              const r = u.roles?.[0] || "employee";
              return (
                <option key={u.email} value={u.email}>
                  [{r}] {u.name}
                </option>
              );
            })}
          </select>
          <button
            onClick={() => setRegisterOpen(true)}
            title="Yeni kullanıcı"
            className="shrink-0 rounded-lg border border-border bg-white p-1.5 text-muted hover:text-ink"
          >
            <UserPlus className="h-3.5 w-3.5" />
          </button>
        </div>
        {me && (
          <div className="mt-1.5 text-[10px] text-subtle leading-tight">
            <div>{me.title}</div>
            <div>Yetki: {me.roles.join(", ")}</div>
          </div>
        )}
      </div>

      <div className="px-5 py-3 text-[11px] text-subtle border-t border-border">
        Azure AI Foundry
      </div>

      <RegisterModal
        open={registerOpen}
        onClose={() => setRegisterOpen(false)}
        onCreated={(email) => {
          api.users().then(setUsers).catch(() => {});
          setCurrentUser(email);
        }}
      />
    </aside>
  );
}
