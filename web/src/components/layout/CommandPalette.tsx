import { useEffect } from "react";
import { Command } from "cmdk";
import { useNavigate } from "react-router-dom";
import {
  Bot,
  LayoutDashboard,
  LayoutTemplate,
  MessageSquare,
  Plus,
  Settings,
  Activity,
  Moon,
  Sun,
} from "lucide-react";
import { useTheme } from "@/hooks/use-theme";
import { useAppStore } from "@/store";
import "./command.css";

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}

export function CommandPalette({ open, onOpenChange }: Props) {
  const navigate = useNavigate();
  const { theme, toggle } = useTheme();
  const agents = useAppStore((s) => s.agents);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        onOpenChange(!open);
      }
      if (e.key === "Escape" && open) {
        onOpenChange(false);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onOpenChange]);

  const go = (path: string) => {
    navigate(path);
    onOpenChange(false);
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] bg-background/70 backdrop-blur-sm animate-fade-in"
      onClick={() => onOpenChange(false)}
    >
      <div
        className="cmdk-root w-full max-w-xl rounded-xl border border-border/60 bg-popover/95 backdrop-blur-xl shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <Command label="komutlar" loop>
          <div className="flex items-center gap-2 border-b border-border px-4 py-3">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="h-4 w-4 text-muted-foreground"
            >
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.3-4.3" />
            </svg>
            <Command.Input
              placeholder="Komut ara veya agent seç..."
              className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
            <kbd className="ml-auto text-[10px] text-muted-foreground border border-border rounded px-1.5 py-0.5">ESC</kbd>
          </div>

          <Command.List className="max-h-[60vh] overflow-y-auto scrollbar-thin p-2">
            <Command.Empty className="py-8 text-center text-sm text-muted-foreground">
              Sonuç yok
            </Command.Empty>

            <Command.Group heading="Sayfalar" className="cmdk-group">
              <Command.Item onSelect={() => go("/")} className="cmdk-item">
                <LayoutDashboard className="h-4 w-4" />
                Panel
              </Command.Item>
              <Command.Item onSelect={() => go("/build")} className="cmdk-item">
                <Plus className="h-4 w-4 text-primary" />
                Yeni Agent Oluştur
              </Command.Item>
              <Command.Item onSelect={() => go("/agents")} className="cmdk-item">
                <Bot className="h-4 w-4" />
                Agent Kataloğu
              </Command.Item>
              <Command.Item onSelect={() => go("/templates")} className="cmdk-item">
                <LayoutTemplate className="h-4 w-4" />
                Şablonlar
              </Command.Item>
              <Command.Item onSelect={() => go("/chat")} className="cmdk-item">
                <MessageSquare className="h-4 w-4" />
                Sohbet
              </Command.Item>
              <Command.Item onSelect={() => go("/analytics")} className="cmdk-item">
                <Activity className="h-4 w-4" />
                Analitik
              </Command.Item>
              <Command.Item onSelect={() => go("/settings")} className="cmdk-item">
                <Settings className="h-4 w-4" />
                Ayarlar
              </Command.Item>
            </Command.Group>

            {agents.length > 0 && (
              <Command.Group heading="Agent'lar" className="cmdk-group">
                {agents.slice(0, 8).map((a) => (
                  <Command.Item
                    key={a.id}
                    onSelect={() => go(`/chat?agent=${encodeURIComponent(a.id)}`)}
                    className="cmdk-item"
                  >
                    <Bot className="h-4 w-4 text-primary" />
                    <span className="flex-1">{a.name}</span>
                    <span className="text-[10px] text-muted-foreground">{a.status}</span>
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            <Command.Group heading="Aksiyonlar" className="cmdk-group">
              <Command.Item
                onSelect={() => {
                  toggle();
                  onOpenChange(false);
                }}
                className="cmdk-item"
              >
                {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                Temayı Değiştir
              </Command.Item>
            </Command.Group>
          </Command.List>
        </Command>
      </div>
    </div>
  );
}
