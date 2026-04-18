import { useEffect, useState } from "react";
import { Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { MobileNav } from "@/components/layout/MobileNav";
import { CommandPalette } from "@/components/layout/CommandPalette";

import { Dashboard } from "@/pages/Dashboard";
import { BuilderPage } from "@/pages/Builder";
import { AgentsPage } from "@/pages/Agents";
import { TemplatesPage } from "@/pages/Templates";
import { ChatPage } from "@/pages/Chat";
import { AnalyticsPage } from "@/pages/Analytics";
import { SettingsPage } from "@/pages/Settings";

import { useTheme } from "@/hooks/use-theme";
import { api } from "@/lib/api";
import { useAppStore } from "@/store";

export default function App() {
  useTheme();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const { setAgents, setTemplates } = useAppStore();

  useEffect(() => {
    api.agents().then(setAgents).catch(() => {});
    api.templates().then(setTemplates).catch(() => {});
  }, [setAgents, setTemplates]);

  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex h-screen overflow-hidden bg-background">
        <Sidebar />

        <div className="flex-1 flex flex-col min-w-0">
          <Topbar onOpenPalette={() => setPaletteOpen(true)} />

          <main className="flex-1 overflow-y-auto scrollbar-thin pb-16 md:pb-0">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/build" element={<BuilderPage />} />
              <Route path="/agents" element={<AgentsPage />} />
              <Route path="/templates" element={<TemplatesPage />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </main>
        </div>

        <MobileNav />
        <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />

        <Toaster
          position="bottom-right"
          theme="system"
          richColors
          closeButton
          toastOptions={{
            classNames: {
              toast: "border border-border bg-card backdrop-blur-xl",
            },
          }}
        />
      </div>
    </TooltipProvider>
  );
}
