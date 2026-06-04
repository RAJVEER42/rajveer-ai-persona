"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Source = { title?: string; repo?: string; source?: string; score?: number };
type Message = { role: "user" | "assistant"; content: string; sources?: Source[]; cached?: number };

const PROJECTS = [
  ["DocBlock", "How does DocBlock work and how does it stay grounded?"],
  ["Samay Sarathi", "Tell me about Samay Sarathi"],
  ["Agent CLI", "How does his agent CLI work?"],
  ["clearpath chatbot", "Walk me through the clearpath HR chatbot"],
  ["CCPA engine", "What is the CCPA compliance engine?"],
];
const QUICK = [
  ["Why hire Rajveer?", "Why is Rajveer a strong fit for an AI engineer role?"],
  ["His weaknesses", "What are Rajveer's honest weaknesses?"],
  ["His skills", "What's his tech stack and strongest skills?"],
];
const FOLLOWUPS = [
  "What would he improve in DocBlock?",
  "What did he build for the Meta Hackathon?",
  "What's his experience with RAG and retrieval?",
  "Tell me about Samay Sarathi",
  "What are his honest weaknesses?",
];

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [dark, setDark] = useState(false);
  const feedRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  // theme: init from saved pref, apply to <html data-theme>
  useEffect(() => {
    const saved = localStorage.getItem("theme") === "dark";
    setDark(saved);
  }, []);
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);

  // custom cursor: precise dot + trailing ring (desktop / fine-pointer only)
  useEffect(() => {
    if (!window.matchMedia?.("(pointer: fine)").matches) return;
    const dot = document.createElement("div"); dot.className = "cursor-dot";
    const ring = document.createElement("div"); ring.className = "cursor-ring";
    document.body.append(dot, ring);
    document.body.classList.add("cc");
    const move = (e: MouseEvent) => {
      const x = e.clientX + "px", y = e.clientY + "px";
      dot.style.left = x; dot.style.top = y;
      ring.style.left = x; ring.style.top = y;
      const t = e.target as HTMLElement;
      ring.classList.toggle("hot", !!t.closest?.("button, a, .chip, .pill, input, .toggle"));
    };
    const down = () => ring.classList.add("down");
    const up = () => ring.classList.remove("down");
    window.addEventListener("mousemove", move);
    window.addEventListener("mousedown", down);
    window.addEventListener("mouseup", up);
    return () => {
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mousedown", down);
      window.removeEventListener("mouseup", up);
      dot.remove(); ring.remove();
      document.body.classList.remove("cc");
    };
  }, []);

  const asked = useMemo(
    () => new Set(messages.filter((m) => m.role === "user").map((m) => m.content)),
    [messages]
  );
  const followups = useMemo(() => FOLLOWUPS.filter((f) => !asked.has(f)).slice(0, 3), [asked]);

  async function send(text: string) {
    const q = text.trim();
    if (!q || busy) return;
    setInput("");
    const history = [...messages, { role: "user" as const, content: q }];
    setMessages([...history, { role: "assistant", content: "" }]);
    setBusy(true);
    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: history.map(({ role, content }) => ({ role, content })) }),
      });
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";
        for (const evt of events) {
          const ev = evt.match(/event: (.*)/)?.[1];
          const data = evt.match(/data: ([\s\S]*)/)?.[1] ?? "";
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            try {
              if (ev === "token") last.content += JSON.parse(data);
              else if (ev === "sources") last.sources = JSON.parse(data || "[]");
              else if (ev === "cached") last.cached = JSON.parse(data).similarity;
            } catch { /* ignore malformed chunk */ }
            return next;
          });
        }
      }
    } catch {
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1].content = "Sorry, I couldn't reach the server. Please try again.";
        return next;
      });
    } finally {
      setBusy(false);
    }
  }

  const lastEmpty =
    messages.length > 0 &&
    messages[messages.length - 1].role === "assistant" &&
    messages[messages.length - 1].content === "";

  return (
    <div className="wrap">
      <div className="header">
        <div>
          <h1>RAJVEER BISHNOI — AI REP</h1>
          <p>Grounded in his real resume &amp; GitHub. Ask anything, or book a call.</p>
        </div>
        <a className="callnum" href="tel:+16506982516" title="Call the AI rep">
          <span className="ic">📞</span> +1 650 698 2516
        </a>
        <div className="hgroup">
          <span className="live"><span className="dot" /> LIVE</span>
          <button className="toggle" onClick={() => setDark((d) => !d)} aria-label="Toggle dark mode" title="Toggle theme">
            {dark ? (
              <svg className="ic" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M18.4 5.6l1.4-1.4M4.2 19.8l1.4-1.4" /></svg>
            ) : (
              <svg className="ic" width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z" /></svg>
            )}
            {dark ? "Light" : "Dark"}
          </button>
        </div>
      </div>

      <div className="body">
        <div className="main">
          <div className="feed" ref={feedRef}>
            {messages.length === 0 && (
              <div className="msg assistant">
                <span className="who">AI Rep</span>
                <div className="bubble">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {"Hey, I'm Rajveer's **AI representative**. Ask me about his work, his projects, why he's a fit for the role, or say **book a call** and I'll check his calendar. Use the panel on the right for quick jumps."}
                  </ReactMarkdown>
                </div>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.role}`}>
                <span className="who">{m.role === "user" ? "You" : "AI Rep"}</span>
                <div className="bubble">
                  {m.content ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                  ) : busy && i === messages.length - 1 ? (
                    <div className="typing"><span /><span /><span /></div>
                  ) : null}
                </div>
                {m.cached !== undefined && <span className="cached">⚡ instant (cache {m.cached})</span>}
                {m.sources && m.sources.length > 0 && (
                  <div className="sources">
                    {m.sources.map((s, j) => (
                      <span key={j} className="badge">{s.repo || s.source}{s.score ? ` · ${s.score}` : ""}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          {!busy && !lastEmpty && messages.length > 0 && followups.length > 0 && (
            <div className="chips">
              <span className="label">Follow up</span>
              {followups.map((s) => (
                <span key={s} className="chip" onClick={() => send(s)}>{s}</span>
              ))}
            </div>
          )}

          <form className="composer" onSubmit={(e) => { e.preventDefault(); send(input); }}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything about Rajveer…"
              disabled={busy}
              autoFocus
            />
            <button type="submit" disabled={busy || !input.trim()}>Send</button>
          </form>
        </div>

        <aside className="side">
          <div className="card pink">
            <h3>📅 Book a call</h3>
            <button className="pill go" onClick={() => send("I'd like to book a call with Rajveer")}>
              Check his calendar →
            </button>
          </div>
          <div className="card">
            <h3>Explore his projects</h3>
            <div className="stack">
              {PROJECTS.map(([label, q]) => (
                <button key={label} className="pill" onClick={() => send(q)}>{label}</button>
              ))}
            </div>
          </div>
          <div className="card">
            <h3>Quick questions</h3>
            <div className="stack">
              {QUICK.map(([label, q]) => (
                <button key={label} className="pill" onClick={() => send(q)}>{label}</button>
              ))}
            </div>
          </div>
          <div className="card lilac">
            <h3>Links</h3>
            <div className="stack">
              <a className="pill link" href="https://github.com/RAJVEER42" target="_blank" rel="noreferrer">↗ GitHub</a>
              <a className="pill link" href="https://samaysarathi.in" target="_blank" rel="noreferrer">↗ Samay Sarathi</a>
              <a className="pill link" href={`${API}/resume`} target="_blank" rel="noreferrer">↗ Résumé</a>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
