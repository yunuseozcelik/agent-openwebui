import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bot,
  Send,
  Sparkles,
  Square,
  RefreshCw,
  User,
  Plus,
  ChevronDown,
  Zap,
  Copy,
  Check,
} from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { api, streamChat, type Agent } from "@/lib/api";
import { useAppStore } from "@/store";
import { cn, getSessionId } from "@/lib/utils";

interface Msg {
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
  ts: number;
}

export function ChatPage() {
  const [params, setParams] = useSearchParams();
  const agents = useAppStore((s) => s.agents);
  const setAgents = useAppStore((s) => s.setAgents);
  const [agentPicker, setAgentPicker] = useState(false);

  const agentId = params.get("agent") ?? agents[0]?.id ?? "";
  const agent = agents.find((a) => a.id === agentId) ?? null;

  const [sessionId, setSessionId] = useState(() => getSessionId());
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const cancelRef = useRef<(() => void) | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (agents.length === 0) api.agents().then(setAgents).catch(() => {});
  }, [agents.length, setAgents]);

  useEffect(() => {
    setMsgs([]);
  }, [agentId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [msgs]);

  function selectAgent(id: string) {
    setParams({ agent: id });
    setAgentPicker(false);
  }

  function newSession() {
    const id = `sess_${Math.random().toString(36).slice(2, 14)}`;
    localStorage.setItem("af_session_id", id);
    setSessionId(id);
    setMsgs([]);
    toast.success("Yeni oturum başlatıldı");
  }

  function stop() {
    cancelRef.current?.();
    cancelRef.current = null;
    setBusy(false);
    setMsgs((m) => m.map((x) => (x.streaming ? { ...x, streaming: false } : x)));
  }

  function send() {
    if (!agent || !input.trim() || busy) return;
    const userMsg: Msg = { role: "user", content: input.trim(), ts: Date.now() };
    const asstMsg: Msg = { role: "assistant", content: "", streaming: true, ts: Date.now() + 1 };
    setMsgs((m) => [...m, userMsg, asstMsg]);
    setInput("");
    setBusy(true);

    cancelRef.current = streamChat(
      { agent_id: agent.id, session_id: sessionId, message: userMsg.content },
      {
        onChunk: (t) => {
          setMsgs((m) => {
            const copy = [...m];
            const last = copy[copy.length - 1];
            if (last && last.role === "assistant") last.content += t;
            return copy;
          });
        },
        onDone: (full) => {
          setMsgs((m) => {
            const copy = [...m];
            const last = copy[copy.length - 1];
            if (last && last.role === "assistant") {
              last.content = full || last.content;
              last.streaming = false;
            }
            return copy;
          });
          setBusy(false);
          cancelRef.current = null;
        },
        onError: (e) => {
          toast.error("Hata: " + e);
          setBusy(false);
          setMsgs((m) => m.map((x) => (x.streaming ? { ...x, streaming: false } : x)));
        },
      }
    );
  }

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  if (agents.length === 0) {
    return (
      <div className="max-w-2xl mx-auto p-8 text-center">
        <Card>
          <CardContent className="p-12">
            <Bot className="h-12 w-12 text-muted-foreground/40 mx-auto mb-3" />
            <h2 className="font-semibold text-lg mb-1">Henüz agent yok</h2>
            <p className="text-sm text-muted-foreground mb-4">
              Sohbet etmek için önce bir agent oluşturmalısın.
            </p>
            <Button asChild variant="gradient">
              <Link to="/build">
                <Plus className="h-4 w-4" />
                Yeni Agent Oluştur
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)] overflow-hidden">
      {/* Sidebar — Agents list */}
      <aside className="hidden md:flex flex-col w-64 border-r border-border/50 bg-card/30 backdrop-blur-xl">
        <div className="p-3 border-b border-border/50">
          <Button variant="gradient" size="sm" className="w-full" onClick={newSession}>
            <RefreshCw className="h-3.5 w-3.5" />
            Yeni Oturum
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto scrollbar-thin p-2 space-y-1">
          {agents.map((a) => (
            <button
              key={a.id}
              onClick={() => selectAgent(a.id)}
              className={cn(
                "w-full text-left rounded-lg p-2.5 flex items-start gap-2.5 transition-all",
                a.id === agentId
                  ? "bg-primary/10 border border-primary/30"
                  : "hover:bg-accent/5 border border-transparent"
              )}
            >
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-primary/20 to-accent/10 flex items-center justify-center shrink-0">
                <Bot className="h-4 w-4 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{a.name}</div>
                <div className="text-[10px] text-muted-foreground truncate">
                  {a.status === "mock" ? "mock • " : ""}
                  {a.model}
                </div>
              </div>
            </button>
          ))}
        </div>
      </aside>

      {/* Main chat */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Agent header */}
        <div className="flex items-center justify-between px-4 md:px-6 py-3 border-b border-border/50 bg-background/70 backdrop-blur-xl">
          <div className="flex items-center gap-3 min-w-0">
            <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-primary/20 to-accent/10 flex items-center justify-center shrink-0">
              <Bot className="h-4 w-4 text-primary" />
            </div>
            <div className="min-w-0">
              <div className="font-semibold text-sm flex items-center gap-2">
                <span className="truncate">{agent?.name ?? "Agent seç"}</span>
                {agent?.status === "mock" && (
                  <Badge variant="warning" className="text-[9px]">
                    mock
                  </Badge>
                )}
              </div>
              <div className="text-[10px] text-muted-foreground font-mono truncate">
                {sessionId}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Mobile agent picker */}
            <button
              className="md:hidden flex items-center gap-1 rounded-lg border border-border bg-card/60 px-2 py-1 text-xs"
              onClick={() => setAgentPicker((v) => !v)}
            >
              Değiştir
              <ChevronDown className="h-3 w-3" />
            </button>
            <Button variant="ghost" size="sm" onClick={newSession}>
              <RefreshCw className="h-3.5 w-3.5" />
              <span className="hidden md:inline">Yeni</span>
            </Button>
          </div>
        </div>

        {/* Mobile agent picker dropdown */}
        <AnimatePresence>
          {agentPicker && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="md:hidden border-b border-border/50 overflow-hidden"
            >
              <div className="p-2 space-y-1 max-h-60 overflow-y-auto scrollbar-thin">
                {agents.map((a) => (
                  <button
                    key={a.id}
                    onClick={() => selectAgent(a.id)}
                    className={cn(
                      "w-full text-left p-2 rounded-md text-sm",
                      a.id === agentId ? "bg-primary/10 text-primary" : "hover:bg-accent/5"
                    )}
                  >
                    {a.name}
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin">
          {msgs.length === 0 ? (
            <ChatEmpty agent={agent} onQuickSend={(t) => setInput(t)} />
          ) : (
            <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
              {msgs.map((m, i) => (
                <MessageBubble key={i} msg={m} />
              ))}
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-border/50 bg-background/70 backdrop-blur-xl p-3 md:p-4">
          <div className="max-w-3xl mx-auto">
            <div className="relative rounded-xl border border-border bg-card/60 backdrop-blur focus-within:border-primary/40 focus-within:shadow-lg focus-within:shadow-primary/5 transition-all">
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder={agent ? `${agent.name}'a mesaj yaz...` : "Agent seç..."}
                disabled={!agent || busy}
                className="border-0 bg-transparent resize-none min-h-[60px] max-h-40 pr-14 py-3"
              />
              <div className="absolute right-2 bottom-2">
                {busy ? (
                  <Button size="icon" variant="destructive" onClick={stop}>
                    <Square className="h-3.5 w-3.5" />
                  </Button>
                ) : (
                  <Button
                    size="icon"
                    variant="gradient"
                    onClick={send}
                    disabled={!agent || !input.trim()}
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>
            <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground">
              <span>Enter: gönder • Shift+Enter: satır</span>
              {msgs.length > 0 && (
                <span>
                  {msgs.filter((m) => m.role === "user").length} mesaj
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ChatEmpty({
  agent,
  onQuickSend,
}: {
  agent: Agent | null;
  onQuickSend: (t: string) => void;
}) {
  const suggestions = useMemo(
    () =>
      agent
        ? [
            "Merhaba! Neler yapabilirsin?",
            `${agent.name} olarak beni nasıl destekleyebilirsin?`,
            "Bir örnek senaryo göster",
          ]
        : [],
    [agent]
  );

  return (
    <div className="h-full flex flex-col items-center justify-center p-8 text-center">
      <div className="relative h-16 w-16 mb-4">
        <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-primary to-accent opacity-80 blur-xl" />
        <div className="relative h-full w-full rounded-2xl bg-gradient-to-br from-primary to-accent flex items-center justify-center">
          <Sparkles className="h-7 w-7 text-white" />
        </div>
      </div>
      <h2 className="text-xl font-bold">{agent?.name ?? "Agent"}</h2>
      <p className="text-sm text-muted-foreground mt-1 max-w-md">
        {agent?.instructions.slice(0, 140) || "Bu agent ile sohbet etmeye başlayın."}
      </p>

      {suggestions.length > 0 && (
        <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-2 max-w-2xl w-full">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => onQuickSend(s)}
              className="rounded-lg border border-border/60 bg-card/40 p-3 text-left text-xs hover:border-primary/40 hover:bg-card/80 transition-all"
            >
              <Zap className="h-3 w-3 text-primary mb-1.5" />
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function MessageBubble({ msg }: { msg: Msg }) {
  const [copied, setCopied] = useState(false);
  const isUser = msg.role === "user";

  function copy() {
    navigator.clipboard.writeText(msg.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn("group flex gap-3", isUser && "flex-row-reverse")}
    >
      <div
        className={cn(
          "h-8 w-8 rounded-lg flex items-center justify-center shrink-0",
          isUser
            ? "bg-secondary"
            : "bg-gradient-to-br from-primary/20 to-accent/10"
        )}
      >
        {isUser ? (
          <User className="h-4 w-4 text-muted-foreground" />
        ) : (
          <Bot className="h-4 w-4 text-primary" />
        )}
      </div>

      <div className={cn("flex-1 min-w-0", isUser && "flex flex-col items-end")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-2.5 max-w-[85%] inline-block",
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-card border border-border/60"
          )}
        >
          <div className="text-sm whitespace-pre-wrap leading-relaxed break-words">
            {msg.content || (msg.streaming && <Cursor />)}
            {msg.content && msg.streaming && <Cursor />}
          </div>
        </div>
        {!isUser && msg.content && !msg.streaming && (
          <button
            onClick={copy}
            className="mt-1 flex items-center gap-1 text-[10px] text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity hover:text-foreground"
          >
            {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
            {copied ? "Kopyalandı" : "Kopyala"}
          </button>
        )}
      </div>
    </motion.div>
  );
}

function Cursor() {
  return (
    <span className="inline-block w-1.5 h-4 ml-0.5 bg-primary animate-pulse align-middle" />
  );
}

