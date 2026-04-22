import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button, Card, Textarea } from "@/components/ui";
import { api, type Agent } from "@/lib/api";
import { useStore } from "@/store";

const PROTECTED = new Set([
  "Supervisor-Agent", "Synthesis-Agent",
  "HR-Agent", "IT-Agent", "Finance-Agent",
  "Math-Agent", "General-Agent", "Chat-Agent",
]);

export function AgentEdit() {
  const { agentId } = useParams<{ agentId: string }>();
  const navigate = useNavigate();
  const setAgents = useStore((s) => s.setAgents);

  const [agent, setAgent] = useState<Agent | null>(null);
  const [instructions, setInstructions] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    if (!agentId) return;
    fetch(`/api/agents/${encodeURIComponent(agentId)}`)
      .then((r) => r.json())
      .then((a: Agent) => {
        setAgent(a);
        setInstructions(a.instructions || "");
      })
      .catch(() => toast.error("Agent yüklenemedi"))
      .finally(() => setLoading(false));
  }, [agentId]);

  async function handleSave() {
    if (!agentId || !agent) return;
    setSaving(true);
    try {
      await api.updateAgent(agentId, { instructions });
      toast.success("Kaydedildi — Azure sync arka planda çalışıyor");
      const updated = await api.agents();
      setAgents(updated);
      navigate("/agents");
    } catch (e) {
      toast.error("Kayıt başarısız: " + String(e));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!agentId) return;
    setDeleting(true);
    try {
      await api.deleteAgent(agentId);
      toast.success("Agent silindi (local + Azure)");
      const updated = await api.agents();
      setAgents(updated);
      navigate("/agents");
    } catch (e) {
      toast.error("Silme başarısız: " + String(e));
    } finally {
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-5 w-5 animate-spin text-muted" />
      </div>
    );
  }

  if (!agent || !agent.name) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-14">
        <p className="text-muted">Agent bulunamadı veya silinmiş.</p>
        <Button variant="ghost" size="sm" onClick={() => navigate("/agents")} className="mt-4">
          <ArrowLeft className="h-4 w-4 mr-1" /> Agentlara Dön
        </Button>
      </div>
    );
  }

  const isProtected = PROTECTED.has(agent.name);

  return (
    <div className="max-w-2xl mx-auto px-6 py-14 space-y-6">
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1.5 text-[13px] text-muted hover:text-ink transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Geri
        </button>
        {!isProtected && (
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="flex items-center gap-1.5 text-[12px] text-red-500 hover:text-red-700 transition-colors"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Sil
          </button>
        )}
      </div>

      <div>
        <div className="text-[11px] text-muted uppercase tracking-widest mb-1">
          {agent.metadata?.parent_agent_name as string || "—"}
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">{agent.name}</h1>
        <p className="text-[13px] text-muted mt-1">
          {String(agent.metadata?.purpose ?? "")}
        </p>
      </div>

      {/* Metadata badges */}
      <div className="flex flex-wrap gap-2">
        {agent.status !== "active" && (
          <span className="rounded-full border border-border px-2.5 py-0.5 text-[11px] text-muted">
            {agent.status}
          </span>
        )}
        {!!agent.metadata?.parent_agent_name && (
          <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-[11px] text-amber-700">
            ↳ {String(agent.metadata.parent_agent_name)}
          </span>
        )}
      </div>

      {/* Instructions editor */}
      <div className="space-y-2">
        <label className="text-[12px] text-muted uppercase tracking-widest">
          Sistem Talimatları
        </label>
        <Textarea
          value={instructions}
          onChange={(e) => setInstructions(e.target.value)}
          disabled={isProtected}
          className="min-h-[300px] font-mono text-[12px] leading-relaxed"
          placeholder={isProtected ? "Sistem agentları düzenlenemez." : "Agent talimatları..."}
        />
        {isProtected && (
          <p className="text-[11px] text-muted">
            Bu bir sistem agentıdır ve düzenlenemez.
          </p>
        )}
      </div>

      {!isProtected && (
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setInstructions(agent.instructions || "")}>
            Sıfırla
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            Kaydet
          </Button>
        </div>
      )}

      {/* Delete confirmation */}
      {showDeleteConfirm && (
        <Card className="p-4 border-red-200 bg-red-50 space-y-3">
          <p className="text-[13px] font-medium text-red-800">
            <strong>{agent.name}</strong> silinsin mi? Bu işlem geri alınamaz.
          </p>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowDeleteConfirm(false)}
            >
              İptal
            </Button>
            <Button
              size="sm"
              onClick={handleDelete}
              disabled={deleting}
              className="bg-red-600 hover:bg-red-700 text-white border-red-600"
            >
              {deleting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Evet, sil
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
