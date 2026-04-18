import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowUp, Bot, Plus, Square, User } from "lucide-react";
import { Button, Card, Textarea } from "@/components/ui";
import { useStore } from "@/store";
import { streamChat } from "@/lib/api";
import { cn, getSessionId } from "@/lib/utils";

interface Msg {
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
}

export function Chat() {
  const [params, setParams] = useSearchParams();
  const agents = useStore((s) => s.agents);
  const agentId = params.get("agent") ?? agents[0]?.id ?? "";
  const agent = agents.find((a) => a.id === agentId) ?? null;

  const [sessionId] = useState(() => getSessionId());
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const cancelRef = useRef<(() => void) | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => setMsgs([]), [agentId]);
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [msgs]);

  function stop() {
    cancelRef.current?.();
    cancelRef.current = null;
    setBusy(false);
    setMsgs((m) => m.map((x) => ({ ...x, streaming: false })));
  }

  function send() {
    if (!agent || !input.trim() || busy) return;
    const user: Msg = { role: "user", content: input.trim() };
    const asst: Msg = { role: "assistant", content: "", streaming: true };
    setMsgs((m) => [...m, user, asst]);
    setInput("");
    setBusy(true);

    cancelRef.current = streamChat(
      { agent_id: agent.id, session_id: sessionId, message: user.content },
      {
        onChunk: (t) =>
          setMsgs((m) => {
            const c = [...m];
            const last = c[c.length - 1];
            if (last?.role === "assistant") last.content += t;
            return c;
          }),
        onDone: (full) => {
          setMsgs((m) => {
            const c = [...m];
            const last = c[c.length - 1];
            if (last?.role === "assistant") {
              last.content = full || last.content;
              last.streaming = false;
            }
            return c;
          });
          setBusy(false);
        },
        onError: () => {
          setBusy(false);
          setMsgs((m) => m.map((x) => ({ ...x, streaming: false })));
        },
      }
    );
  }

  if (agents.length === 0) {
    return (
      <div className="max-w-md mx-auto px-6 py-20 text-center">
        <Card className="p-10">
          <Bot className="h-6 w-6 text-subtle mx-auto mb-3" />
          <div className="text-sm text-muted mb-4">Henüz agent yok</div>
          <Link to="/build">
            <Button>
              <Plus className="h-4 w-4" /> Oluştur
            </Button>
          </Link>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-border bg-white px-6 py-3.5 flex items-center gap-3">
        <select
          value={agentId}
          onChange={(e) => setParams({ agent: e.target.value })}
          className="bg-transparent text-[14px] font-medium focus:outline-none cursor-pointer"
        >
          {agents.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
        {agent?.status === "mock" && (
          <span className="text-[11px] text-subtle">mock</span>
        )}
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto"
      >
        {msgs.length === 0 ? (
          <div className="flex items-center justify-center h-full text-center px-6">
            <div>
              <div className="text-[15px] font-medium mb-1">{agent?.name}</div>
              <div className="text-[13px] text-muted max-w-sm">
                Mesaj yazarak sohbete başlayın
              </div>
            </div>
          </div>
        ) : (
          <div className="max-w-2xl mx-auto px-6 py-8 space-y-6">
            {msgs.map((m, i) => (
              <Message key={i} msg={m} />
            ))}
          </div>
        )}
      </div>

      <div className="border-t border-border bg-white p-4">
        <div className="max-w-2xl mx-auto relative">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            placeholder="Mesaj yazın..."
            disabled={busy}
            rows={1}
            className="pr-12 py-3"
          />
          <button
            onClick={busy ? stop : send}
            disabled={!busy && !input.trim()}
            className={cn(
              "absolute right-2 bottom-2 h-8 w-8 rounded-full flex items-center justify-center transition-colors",
              !busy && !input.trim()
                ? "bg-border text-subtle cursor-not-allowed"
                : "bg-ink text-white hover:bg-black"
            )}
          >
            {busy ? (
              <Square className="h-3 w-3" fill="currentColor" />
            ) : (
              <ArrowUp className="h-4 w-4" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

function Message({ msg }: { msg: Msg }) {
  const isUser = msg.role === "user";
  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "h-7 w-7 rounded-full flex items-center justify-center shrink-0 border border-border",
          isUser ? "bg-white" : "bg-surface"
        )}
      >
        {isUser ? (
          <User className="h-3.5 w-3.5 text-muted" />
        ) : (
          <Bot className="h-3.5 w-3.5 text-muted" />
        )}
      </div>
      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-2.5",
          isUser ? "bg-ink text-white" : "bg-surface"
        )}
      >
        <div className="text-[14px] whitespace-pre-wrap leading-relaxed break-words">
          {msg.content}
          {msg.streaming && (
            <span className="inline-block w-1.5 h-4 ml-0.5 bg-current opacity-60 animate-pulse align-middle" />
          )}
        </div>
      </div>
    </div>
  );
}
