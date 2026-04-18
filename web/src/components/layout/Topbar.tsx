import { useNavigate, useLocation } from "react-router-dom";
import { Moon, Search, Sun, Github } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/hooks/use-theme";
import { cn } from "@/lib/utils";

interface Props {
  onOpenPalette: () => void;
}

const pageTitles: Record<string, string> = {
  "/": "Panel",
  "/build": "Yeni Agent Oluştur",
  "/agents": "Agent Kataloğu",
  "/templates": "Şablon Galerisi",
  "/chat": "Agent Sohbet",
  "/analytics": "Analitik",
  "/settings": "Ayarlar",
};

export function Topbar({ onOpenPalette }: Props) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { theme, toggle } = useTheme();

  const title = Object.entries(pageTitles).find(
    ([p]) => pathname === p || (p !== "/" && pathname.startsWith(p))
  )?.[1] ?? "Agent Factory";

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border/50 bg-background/80 backdrop-blur-xl px-4 md:px-6">
      <h1 className="text-sm font-semibold text-foreground/90">
        {title}
      </h1>

      <div className="flex-1" />

      {/* Command palette trigger */}
      <button
        onClick={onOpenPalette}
        className={cn(
          "flex items-center gap-2 rounded-lg border border-border bg-card/50 px-3 py-1.5",
          "text-xs text-muted-foreground hover:border-primary/40 hover:text-foreground transition-all",
          "min-w-[200px]"
        )}
      >
        <Search className="h-3.5 w-3.5" />
        <span className="flex-1 text-left">Ara veya komut...</span>
        <kbd className="inline-flex items-center rounded border border-border bg-muted/60 px-1.5 py-0.5 text-[10px] font-mono">
          ⌘K
        </kbd>
      </button>

      <Button
        size="icon"
        variant="ghost"
        onClick={toggle}
        aria-label="tema değiştir"
      >
        {theme === "dark" ? (
          <Sun className="h-4 w-4" />
        ) : (
          <Moon className="h-4 w-4" />
        )}
      </Button>

      <Button
        size="sm"
        variant="gradient"
        className="hidden md:inline-flex"
        onClick={() => navigate("/build")}
      >
        Yeni Agent
      </Button>
    </header>
  );
}
