"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Icon } from "@/components/Icon";
import { TracePanel } from "@/components/ToolTraceChip";
import { postChat, type ChatMessage, type ToolHop } from "@/lib/api";
import { usePlot } from "@/lib/PlotContext";
import { actionVerb, classLabelId, fmtLevel } from "@/lib/format";

function displayReply(raw: string): string {
  return raw
    .replace(/\[(?:Source|Sumber):[^\]]*\]/gi, "")
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/__(.+?)__/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/^\s*[-*•]\s+/gm, "")
    .replace(/\*\*/g, "")
    .replace(/\b(?:the\s+)?ONNX\s+triage\b/gi, "the photo check")
    .replace(/\bONNX\b/gi, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function BubbleText({ text }: { text: string }) {
  const parts = displayReply(text)
    .split(/\n{2,}/)
    .map((p) => p.replace(/\n/g, " ").trim())
    .filter(Boolean);
  if (parts.length <= 1) {
    return <>{parts[0] ?? ""}</>;
  }
  return (
    <>
      {parts.map((p, i) => (
        <p key={i} className="chat-msg__p">{p}</p>
      ))}
    </>
  );
}

interface DisplayMessage {
  role: "user" | "assistant";
  content: string;
  imagePreviewUrl?: string;
  toolTrace?: ToolHop[];
  mode?: "live" | "offline";
}

export function AssistantClient() {
  const searchParams = useSearchParams();
  const { today } = usePlot();
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingImage, setPendingImage] = useState<{ dataUri: string; previewUrl: string; name: string } | null>(null);
  const sessionRef = useRef<string>("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const lastWireRef = useRef<ChatMessage[] | null>(null);
  const sentQ = useRef<string | null>(null);
  const messagesRef = useRef<DisplayMessage[]>([]);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  const ensureSession = () => {
    if (sessionRef.current) return sessionRef.current;
    let sid = sessionStorage.getItem("iris_chat_session");
    if (!sid) {
      sid =
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `s-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      sessionStorage.setItem("iris_chat_session", sid);
    }
    sessionRef.current = sid;
    return sid;
  };

  useEffect(() => {
    ensureSession();
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  const attachFile = (f: File | null | undefined) => {
    if (!f) return;
    if (pendingImage) URL.revokeObjectURL(pendingImage.previewUrl);
    const reader = new FileReader();
    reader.onload = () => {
      setPendingImage({
        dataUri: String(reader.result),
        previewUrl: URL.createObjectURL(f),
        name: f.name,
      });
    };
    reader.readAsDataURL(f);
  };

  const send = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if ((!trimmed && !pendingImage) || busy) return;

    const userMsg: DisplayMessage = {
      role: "user",
      content: trimmed || "(leaf photo attached)",
      imagePreviewUrl: pendingImage?.previewUrl,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setBusy(true);
    setError(null);

    const wire: ChatMessage[] = messagesRef.current.map((m) => ({ role: m.role, content: m.content }));
    wire.push({
      role: "user",
      content: userMsg.content,
      ...(pendingImage ? { image_ref: pendingImage.dataUri } : {}),
    });

    try {
      lastWireRef.current = wire;
      const res = await postChat({ session_id: ensureSession(), messages: wire });
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.reply, toolTrace: res.tool_trace, mode: res.mode },
      ]);
      if (pendingImage) {
        URL.revokeObjectURL(pendingImage.previewUrl);
        setPendingImage(null);
      }
      composerRef.current?.focus();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cannot reach the assistant server.");
    } finally {
      setBusy(false);
    }
  }, [busy, pendingImage]);

  const q = searchParams.get("q");
  useEffect(() => {
    if (!q || sentQ.current === q || busy) return;
    sentQ.current = q;
    void send(q);
  }, [q, send, busy]);

  const retry = useCallback(() => {
    const wire = lastWireRef.current;
    if (!wire || busy) return;
    setError(null);
    setBusy(true);
    postChat({ session_id: ensureSession(), messages: wire })
      .then((res) => {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: res.reply, toolTrace: res.tool_trace, mode: res.mode },
        ]);
      })
      .catch(() => setError("Still cannot connect. Check the network, then retry."))
      .finally(() => setBusy(false));
  }, [busy]);

  const onComposerKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  };

  const suggested = useMemo(() => {
    return [
      "Why is irrigation on hold?",
      "What does the latest leaf status mean?",
      "Why does methane drop?",
    ];
  }, []);

  return (
    <div className="chat-shell">
      {/* Live plot context: the same records Water/Today read, so the leaf
          screened on the Leaf page shows up here too. */}
      {today && (
        <div className="assistant-context" aria-label="Plot context">
          <strong>{today.plot.name}</strong>
          <span>
            {today.recommendation
              ? `${actionVerb(today.recommendation.action)} · water ${fmtLevel(today.water.level_cm)}`
              : "No recommendation yet"}
          </span>
          <span>
            Leaf: {today.latest_leaf ? classLabelId(today.latest_leaf.class ?? "none") : "no photo yet"}
          </span>
        </div>
      )}
      <div className="chat-scroll" role="log" aria-live="polite" aria-busy={busy} ref={scrollRef}>
          {messages.length === 0 && (
            <div className="chat-welcome">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/mascot.png" alt="" className="chat-mascot" />
              <p className="muted">
                Hi! I&apos;m IRIS — ask me about this plot&apos;s water, leaf, or weather.
              </p>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`chat-msg chat-msg--${m.role}`}>
              {m.role === "assistant" && (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img src="/mascot.png" alt="" className="chat-mascot chat-mascot--avatar" />
              )}
              <div className="chat-msg__body">
                {m.imagePreviewUrl && (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img className="chat-msg__thumb" src={m.imagePreviewUrl} alt="Attached photo" />
                )}
                <div className="chat-msg__bubble"><BubbleText text={m.content} /></div>
                {m.role === "assistant" && ((m.toolTrace && m.toolTrace.length > 0) || m.mode) && (
                  <div className="chat-msg__meta">
                    {m.toolTrace && m.toolTrace.length > 0 && <TracePanel hops={m.toolTrace} />}
                    {m.mode === "offline" && (
                      <span className="mode-badge">
                        <Icon name="alert-triangle" size={20} /> offline mode
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          {busy && (
            <div className="chat-msg chat-msg--assistant">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/mascot.png" alt="" className="chat-mascot chat-mascot--avatar" />
              <div className="chat-msg__body">
                <div className="chat-msg__bubble typing" aria-label="Assistant is typing">
                  <span /><span /><span />
                </div>
              </div>
            </div>
          )}
          {error && (
            <div className="callout callout--danger" style={{ display: "flex", gap: 12, alignItems: "center", justifyContent: "space-between" }}>
              <span>{error}</span>
              <button type="button" className="button button--secondary button--compact" onClick={retry} disabled={busy}>
                Retry
              </button>
            </div>
          )}
        </div>

        <div className="chat-composer">
          <div className="chat-prompts">
            {suggested.map((p) => (
              <button key={p} type="button" disabled={busy} onClick={() => send(p)}>
                {p}
              </button>
            ))}
          </div>
          {pendingImage && (
            <div className="pending-image">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={pendingImage.previewUrl} alt="Attached photo" />
              <span>{pendingImage.name}</span>
              <button
                type="button"
                onClick={() => {
                  URL.revokeObjectURL(pendingImage.previewUrl);
                  setPendingImage(null);
                }}
              >
                Remove attachment
              </button>
            </div>
          )}
          <div className="chat-inputrow">
            <button
              type="button"
              className="button button--secondary button--compact attach-btn"
              aria-label="Attach leaf photo"
              title="Attach leaf photo"
              onClick={() => fileInputRef.current?.click()}
            >
              <Icon name="paperclip" size={20} />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              style={{ display: "none" }}
              onChange={(e) => attachFile(e.target.files?.[0])}
            />
            <label htmlFor="chat-input" className="sr-only">Ask IRIS</label>
            <textarea
              id="chat-input"
              ref={composerRef}
              className="textarea"
              rows={2}
              placeholder="Ask a question about this plot…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onComposerKeyDown}
            />
            <button type="button" className="button button--primary button--compact" disabled={busy || (!input.trim() && !pendingImage)} onClick={() => send(input)}>
              Send
            </button>
          </div>
          <div className="chat-disclaimer">
            Answers come from IRIS tools and the knowledge base.
            No pesticide doses. Photo check is screening, not a diagnosis.
            Consult an extension officer. Irrigation actions are
            recommendations; IRIS does not start a pump.
          </div>
        </div>
    </div>
  );
}
