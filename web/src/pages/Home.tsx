import { Link } from "react-router-dom";
import { ArrowRight, Bot, Plus } from "lucide-react";
import { useStore } from "@/store";
import { Button, Card } from "@/components/ui";
import { truncate } from "@/lib/utils";

export function Home() {
  const agents = useStore((s) => s.agents);
  const templates = useStore((s) => s.templates);

  return (
    <div className="max-w-3xl mx-auto px-6 md:px-10 py-14 md:py-20 space-y-16">
      <header className="space-y-4">
        <h1 className="text-4xl md:text-5xl font-semibold tracking-tight leading-tight">
          Doğal dille
          <br />
          AI agent oluşturun.
        </h1>
        <p className="text-muted text-[15px] max-w-lg leading-relaxed">
          Ne yapmasını istediğinizi birkaç cümle anlatın, agent sizin için kurulsun.
        </p>
        <div className="flex gap-3 pt-2">
          <Link to="/build">
            <Button size="lg">
              <Plus className="h-4 w-4" /> Yeni Agent
            </Button>
          </Link>
          <Link to="/templates">
            <Button size="lg" variant="secondary">
              Şablonlar
            </Button>
          </Link>
        </div>
      </header>

      <section>
        <div className="flex items-baseline justify-between mb-4">
          <h2 className="text-[15px] font-semibold">Agent'larınız</h2>
          <span className="text-[13px] text-muted">{agents.length} toplam</span>
        </div>
        {agents.length === 0 ? (
          <Card className="p-8 text-center">
            <Bot className="h-6 w-6 text-subtle mx-auto mb-2" />
            <div className="text-sm text-muted">Henüz agent yok</div>
          </Card>
        ) : (
          <div className="space-y-1.5">
            {agents.slice(0, 5).map((a) => (
              <Link
                key={a.id}
                to={`/chat?agent=${encodeURIComponent(a.id)}`}
                className="flex items-center gap-3 rounded-lg border border-border bg-white px-4 py-3 hover:border-ink transition-colors group"
              >
                <Bot className="h-4 w-4 text-muted shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-[14px] font-medium truncate">{a.name}</div>
                  <div className="text-[12px] text-muted truncate">
                    {truncate(a.instructions.replace(/\n/g, " "), 80) || a.model}
                  </div>
                </div>
                <ArrowRight className="h-4 w-4 text-subtle group-hover:text-ink transition-colors" />
              </Link>
            ))}
          </div>
        )}
      </section>

      {templates.length > 0 && (
        <section>
          <div className="flex items-baseline justify-between mb-4">
            <h2 className="text-[15px] font-semibold">Hazır şablonlar</h2>
            <Link to="/templates" className="text-[13px] text-muted hover:text-ink">
              Tümü
            </Link>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {templates.slice(0, 6).map((t) => (
              <Link
                key={t.id}
                to="/templates"
                className="rounded-lg border border-border bg-white px-3 py-3 hover:border-ink transition-colors"
              >
                <div className="text-lg mb-1">{t.emoji}</div>
                <div className="text-[13px] font-medium truncate">{t.name}</div>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
