import { useState } from "react";
import { motion } from "framer-motion";
import {
  Moon,
  Sun,
  Palette,
  Key,
  Globe,
  Info,
  ExternalLink,
  Trash2,
  Check,
} from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useTheme } from "@/hooks/use-theme";
import { cn, getSessionId } from "@/lib/utils";

export function SettingsPage() {
  const { theme, toggle } = useTheme();
  const [sessionId] = useState(() => getSessionId());

  function clearSession() {
    localStorage.removeItem("af_session_id");
    toast.success("Oturum temizlendi. Sayfayı yenileyin.");
  }

  function copyId() {
    navigator.clipboard.writeText(sessionId);
    toast.success("Kopyalandı");
  }

  return (
    <div className="max-w-3xl mx-auto p-4 md:p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Ayarlar</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Tercih, oturum ve sistem bilgileri
        </p>
      </div>

      {/* Appearance */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Palette className="h-4 w-4 text-primary" />
            <CardTitle className="text-base">Görünüm</CardTitle>
          </div>
          <CardDescription>Tema ve arayüz tercihleri</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">Tema</div>
              <div className="text-xs text-muted-foreground">Açık / koyu mod seçimi</div>
            </div>
            <div className="flex gap-2">
              <ThemeButton active={theme === "light"} onClick={() => theme !== "light" && toggle()}>
                <Sun className="h-4 w-4" /> Açık
              </ThemeButton>
              <ThemeButton active={theme === "dark"} onClick={() => theme !== "dark" && toggle()}>
                <Moon className="h-4 w-4" /> Koyu
              </ThemeButton>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Session */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Key className="h-4 w-4 text-primary" />
            <CardTitle className="text-base">Oturum</CardTitle>
          </div>
          <CardDescription>Agent'larla konuşma durumunu tutar</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="text-xs text-muted-foreground">Mevcut Oturum ID</div>
              <code className="text-xs font-mono text-foreground/80 truncate block">
                {sessionId}
              </code>
            </div>
            <div className="flex gap-2 shrink-0">
              <Button variant="outline" size="sm" onClick={copyId}>
                Kopyala
              </Button>
              <Button variant="destructive" size="sm" onClick={clearSession}>
                <Trash2 className="h-3.5 w-3.5" />
                Sıfırla
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Backend */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Globe className="h-4 w-4 text-primary" />
            <CardTitle className="text-base">Backend</CardTitle>
          </div>
          <CardDescription>Azure Foundry ve Portkey entegrasyonu</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <InfoRow label="API Base" value="same-origin (/api)" />
          <InfoRow label="SSE Streaming" value="Aktif" ok />
          <InfoRow
            label="Azure Foundry"
            value="Env'den otomatik — AZURE_AI_PROJECT_CONNECTION_STRING"
            mono
          />
          <InfoRow
            label="Portkey"
            value="utils/portkey.py üzerinden proxy"
            mono
          />
        </CardContent>
      </Card>

      {/* About */}
      <Card className="border-primary/20 bg-gradient-to-br from-card to-primary/5">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Info className="h-4 w-4 text-primary" />
            <CardTitle className="text-base">Hakkında</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-2">
            <Badge variant="default">v2.0</Badge>
            <Badge variant="accent">Microsoft Agent Framework</Badge>
            <Badge variant="secondary">Azure AI Foundry</Badge>
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Agent Factory — doğal dille AI agent oluşturma platformu. Chainlit yerine
            React + Vite + TailwindCSS tabanlı modern UI, SSE streaming, komut paleti ve
            animasyonlu pipeline görselleştirmesiyle.
          </p>
          <div className="flex items-center gap-2 text-xs">
            <a
              href="https://learn.microsoft.com/azure/ai-studio/"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-primary hover:underline"
            >
              Azure AI Studio
              <ExternalLink className="h-3 w-3" />
            </a>
            <span className="text-muted-foreground">•</span>
            <a
              href="https://github.com/microsoft/agent-framework"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-primary hover:underline"
            >
              Agent Framework
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function ThemeButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "relative flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-medium transition-all",
        active
          ? "border-primary bg-primary/10 text-primary"
          : "border-border bg-card/40 text-muted-foreground hover:text-foreground"
      )}
    >
      {children}
      {active && (
        <motion.span layoutId="theme-active" className="absolute -right-1 -top-1">
          <Check className="h-3 w-3 text-primary-foreground bg-primary rounded-full p-0.5" />
        </motion.span>
      )}
    </button>
  );
}

function InfoRow({
  label,
  value,
  ok,
  mono,
}: {
  label: string;
  value: string;
  ok?: boolean;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span
        className={cn(
          "text-xs text-right",
          mono && "font-mono",
          ok && "text-success font-medium"
        )}
      >
        {ok && "● "}
        {value}
      </span>
    </div>
  );
}
