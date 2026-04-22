import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";

type Department = { id: string; label: string; base_role: string };
type Level = { id: string; label: string; suffix: string; is_manager: boolean };
type Catalog = { departments: Department[]; levels: Level[] };

function previewEmail(name: string): string {
  const map: Record<string, string> = {
    ç: "c", ğ: "g", ı: "i", ö: "o", ş: "s", ü: "u",
    Ç: "c", Ğ: "g", İ: "i", Ö: "o", Ş: "s", Ü: "u",
  };
  const n = name.split("").map((c) => map[c] ?? c).join("")
    .toLowerCase().replace(/[^a-z0-9\s]/g, "").trim().split(/\s+/).filter(Boolean);
  if (n.length === 0) return "—";
  const base = n.length >= 2 ? `${n[0]}.${n[1]}` : n[0];
  return `${base}@fnss.com.tr`;
}

export function RegisterModal({
  open, onClose, onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (email: string) => void;
}) {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [name, setName] = useState("");
  const [deptId, setDeptId] = useState("");
  const [levelId, setLevelId] = useState("specialist");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || catalog) return;
    api.catalog().then(setCatalog).catch(() => {});
  }, [open, catalog]);

  useEffect(() => {
    if (catalog && !deptId && catalog.departments[0]) setDeptId(catalog.departments[0].id);
  }, [catalog, deptId]);

  const dept = useMemo(() => catalog?.departments.find((d) => d.id === deptId) || null, [catalog, deptId]);
  const level = useMemo(() => catalog?.levels.find((l) => l.id === levelId) || null, [catalog, levelId]);

  const derivedTitle = dept && level ? `${dept.label} ${level.suffix}` : "—";
  const derivedRole = level?.is_manager ? "manager (tüm departman yetkisi)" : dept?.base_role ?? "";

  if (!open) return null;

  async function submit() {
    if (!name.trim()) return toast.error("İsim zorunlu");
    if (!dept || !level) return toast.error("Departman ve kademe seçin");
    setLoading(true);
    try {
      const r = await api.registerUser({ name: name.trim(), department: dept.id, level: level.id });
      toast.success(`Oluşturuldu: ${r.user.email}`);
      onCreated(r.user.email);
      setName("");
      onClose();
    } catch (e: any) {
      toast.error(String(e?.message || e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-[420px] rounded-xl bg-white p-5 shadow-xl">
        <div className="mb-1 text-[15px] font-semibold">Yeni Kullanıcı</div>
        <div className="mb-4 text-[11.5px] text-subtle">
          Ünvan ve yetki, departman + kademe'den otomatik belirlenir.
        </div>

        <div className="space-y-2.5">
          <label className="block">
            <div className="mb-1 text-[10.5px] uppercase tracking-widest text-muted">Ad Soyad</div>
            <input
              className="w-full rounded-lg border border-border px-2.5 py-2 text-[13px]"
              placeholder="ör. Oğuzhan Sağlam"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </label>

          <label className="block">
            <div className="mb-1 text-[10.5px] uppercase tracking-widest text-muted">Departman</div>
            <select
              className="w-full rounded-lg border border-border bg-white px-2.5 py-2 text-[13px]"
              value={deptId}
              onChange={(e) => setDeptId(e.target.value)}
            >
              {catalog?.departments.map((d) => (
                <option key={d.id} value={d.id}>{d.label}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <div className="mb-1 text-[10.5px] uppercase tracking-widest text-muted">Kademe</div>
            <select
              className="w-full rounded-lg border border-border bg-white px-2.5 py-2 text-[13px]"
              value={levelId}
              onChange={(e) => setLevelId(e.target.value)}
            >
              {catalog?.levels.map((l) => (
                <option key={l.id} value={l.id}>{l.label}{l.is_manager ? " · yönetici" : ""}</option>
              ))}
            </select>
          </label>

          <div className="rounded-lg border border-dashed border-border bg-bg px-2.5 py-2 text-[11.5px] text-muted space-y-0.5">
            <div>Ünvan: <span className="text-ink">{derivedTitle}</span></div>
            <div>Rol: <span className="text-ink">{derivedRole}</span></div>
            <div>Email: <span className="font-mono text-ink">{previewEmail(name)}</span></div>
          </div>
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-lg px-3 py-1.5 text-[13px] text-muted hover:bg-bg">
            İptal
          </button>
          <button
            onClick={submit}
            disabled={loading || !name.trim() || !catalog}
            className="rounded-lg bg-ink px-3 py-1.5 text-[13px] text-white disabled:opacity-50"
          >
            {loading ? "..." : "Oluştur"}
          </button>
        </div>
      </div>
    </div>
  );
}
