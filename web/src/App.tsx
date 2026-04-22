import { useEffect } from "react";
import { Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";
import { Sidebar } from "@/components/Sidebar";
import { Home } from "@/pages/Home";
import { Builder } from "@/pages/Builder";
import { Agents } from "@/pages/Agents";
import { Templates } from "@/pages/Templates";
import { Chat } from "@/pages/Chat";
import { AgentEdit } from "@/pages/AgentEdit";
import { Admin } from "@/pages/Admin";
import { api } from "@/lib/api";
import { useStore } from "@/store";

export default function App() {
  const setAgents = useStore((s) => s.setAgents);
  const setTemplates = useStore((s) => s.setTemplates);

  useEffect(() => {
    api.agents().then(setAgents).catch(() => {});
    api.templates().then(setTemplates).catch(() => {});
  }, [setAgents, setTemplates]);

  return (
    <div className="flex h-screen bg-bg">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/build" element={<Builder />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/templates" element={<Templates />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/agents/:agentId/edit" element={<AgentEdit />} />
          <Route path="/admin" element={<Admin />} />
        </Routes>
      </main>
      <Toaster
        position="bottom-center"
        toastOptions={{
          style: {
            background: "#111",
            color: "#fff",
            border: "none",
            borderRadius: "10px",
          },
        }}
      />
    </div>
  );
}
