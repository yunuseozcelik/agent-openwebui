import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Shield, Save } from "lucide-react";
import { api } from "@/lib/api";
import { useStore } from "@/store";

type UserRow = {
  email: string;
  name: string;
  department: string;
  title: string;
  roles: string[];
  extra_agents?: string[];
};

export function Admin() {
  const me = useStore((s) => s.me);
  const agents = useStore((s) => s.agents);
  const [users, setUsers] = useState<UserRow[]>([]);
  const [drafts, setDrafts] = useState<Record<string, Set<string>>>({});
  const [saving, setSaving] = useState<string | null>(null);

  useEffect(() => {
    api.users().then((list) => {
      setUsers(list as UserRow[]);
      const d: Record<string, Set<string>> = {};
      for (const u of list as UserRow[]) {
        d[u.email] = new Set(u.extra_agents || []);
      }
      setDrafts(d);
    }).catch(() => {});
  }, []);

  const grantable = useMemo(
    () => agents.filter((a) => {
      const name = a.name;
      const sys = new Set(["Supervisor-Agent", "Synthesis-Agent"]);
      return !sys.has(name);
    }),
    [agents]
  );

  if (!me || !me.roles.includes("admin")) {
    return (
      <div className="p-8 text-muted text-[13px]">
        Bu sayfa yalnızca admin rolü için görünür.
      </div>
    );
  }

  function toggle(email: string, agentName: string) {
    setDrafts((d) => {
      const s = new Set(d[email] || []);
      if (s.has(agentName)) s.delete(agentName);
      else s.add(agentName);
      return { ...d, [email]: s };
    });
  }

  async function save(email: string) {
    setSaving(email);
    try {
      const agents = Array.from(drafts[email] || []);
      await api.grantAgents(email, agents);
      toast.success(`${email} yetkileri güncellendi`);
      setUsers((us) => us.map((u) => u.email === email ? { ...u, extra_agents: agents } : u));
    } catch (e: any) {
      toast.error(String(e?.message || e));
    } finally {
      setSaving(null);
    }
  }

  return (
    <div className="p-8 max-w-5xl">
      <div className="flex items-center gap-2 mb-6">
        <Shield className="h-5 w-5 text-ink" />
        <h1 className="text-[20px] font-semibold tracking-tight">Admin Paneli</h1>
      </div>
      <p className="text-[13px] text-muted mb-6">
        Kullanıcılara rollerinin verdiği varsayılan erişime ek olarak <b>bireysel agent erişimi</b> tanımlayabilirsiniz.
      </p>

      <div className="space-y-3">
        {users.map((u) => {
          const isAdmin = u.roles.includes("admin");
          const selected = drafts[u.email] || new Set();
          const dirty = JSON.stringify([...selected].sort()) !==
                        JSON.stringify([...(u.extra_agents || [])].sort());
          return (
            <div key={u.email} className="rounded-xl border border-border bg-white p-4">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <div className="text-[14px] font-medium">{u.name}</div>
                  <div className="text-[11.5px] text-subtle">
                    {u.email} · {u.department} · {u.title} · roller: {u.roles.join(", ")}
                  </div>
                </div>
                {isAdmin ? (
                  <span className="text-[11px] text-subtle">admin — tümünü görür</span>
                ) : (
                  <button
                    disabled={!dirty || saving === u.email}
                    onClick={() => save(u.email)}
                    className="flex items-center gap-1.5 rounded-lg bg-ink px-3 py-1.5 text-[12px] text-white disabled:opacity-40"
                  >
                    <Save className="h-3.5 w-3.5" />
                    {saving === u.email ? "..." : "Kaydet"}
                  </button>
                )}
              </div>
              {!isAdmin && (
                <div className="flex flex-wrap gap-1.5">
                  {grantable.map((a) => {
                    const on = selected.has(a.name);
                    return (
                      <button
                        key={a.id}
                        onClick={() => toggle(u.email, a.name)}
                        className={
                          "rounded-full border px-2.5 py-1 text-[11.5px] transition-colors " +
                          (on
                            ? "border-emerald-400 bg-emerald-50 text-emerald-800"
                            : "border-border bg-white text-muted hover:bg-bg")
                        }
                      >
                        {on ? "✓ " : ""}{a.name}
                      </button>
                    );
                  })}
                  {grantable.length === 0 && (
                    <div className="text-[11.5px] text-subtle">Atanabilir agent yok.</div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
