import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useStore } from "@/store";
import { Button, Card } from "@/components/ui";
import { api, type Template } from "@/lib/api";

export function Templates() {
  const templates = useStore((s) => s.templates);
  const [selected, setSelected] = useState<Template | null>(null);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  async function deploy(t: Template) {
    setBusy(true);
    try {
      const build = await api.buildFromTemplate(t.id);
      const res = await api.deploy(build.spec_id);
      if (res.success) {
        toast.success("Hazır");
        const agents = await api.agents();
        useStore.getState().setAgents(agents);
        navigate(`/chat?agent=${encodeURIComponent(res.foundry_agent_id || "")}`);
      } else {
        toast.error(res.error || "Başarısız");
      }
    } catch (e) {
      toast.error(String(e));
    } finally {
      setBusy(false);
      setSelected(null);
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-6 md:px-10 py-14 md:py-20">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight mb-2">Şablonlar</h1>
        <p className="text-muted text-[14px]">Hazır senaryolar — tek tıkla başla.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {templates.map((t) => (
          <button
            key={t.id}
            onClick={() => setSelected(t)}
            className="text-left rounded-lg border border-border bg-white p-4 hover:border-ink transition-colors"
          >
            <div className="text-2xl mb-2">{t.emoji}</div>
            <div className="text-[14px] font-medium mb-1">{t.name}</div>
            <div className="text-[12px] text-muted line-clamp-2">{t.description}</div>
          </button>
        ))}
      </div>

      {selected && (
        <div
          className="fixed inset-0 z-40 bg-ink/20 flex items-center justify-center p-4 animate-in fade-in duration-200"
          onClick={() => !busy && setSelected(null)}
        >
          <Card
            className="max-w-md w-full p-6 space-y-4 animate-in slide-in-from-bottom-2 duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            <div>
              <div className="text-3xl mb-3">{selected.emoji}</div>
              <h3 className="text-xl font-semibold mb-1">{selected.name}</h3>
              <p className="text-[13px] text-muted">{selected.description}</p>
            </div>

            <div className="text-[13px] text-muted leading-relaxed border-t border-border pt-4">
              {selected.purpose}
            </div>

            <div className="flex gap-2 pt-2">
              <Button
                variant="secondary"
                onClick={() => setSelected(null)}
                disabled={busy}
              >
                İptal
              </Button>
              <Button
                className="flex-1"
                onClick={() => deploy(selected)}
                disabled={busy}
              >
                {busy ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" /> Oluşturuluyor
                  </>
                ) : (
                  "Oluştur"
                )}
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
