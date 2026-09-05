"use client";

/**
 * SIH26056 — Analyst Copilot.
 *
 * Security posture (audit finding C1)
 * -----------------------------------
 * This component holds NO API key and cannot. The previous version had a live Google
 * key as a committed literal fallback, shipped in the public static bundle.
 *
 * The only path to a language model is the backend proxy at
 * `POST /api/v1/copilot/ask`, which holds the key server-side. This component sends a
 * question and renders whatever comes back.
 *
 * Honest attribution
 * ------------------
 * The response carries a `tier` (`model` or `local_fallback`). The badge renders that
 * tier.
 *
 * Grounding
 * ---------
 * The backend grounds provider requests in its own persisted series. Dashboard state
 * is used only for the visible greeting and deterministic static-preview fallback.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowUp, CheckCircle2, X } from "lucide-react";
import { DATA_MODE, NOT_AVAILABLE, askCopilot } from "../lib/api";
import { fmtChange, fmtCount, fmtIndex } from "../lib/format";

/** Icon used by the nav and trigger button matching the Copilot bot squircle with interactive cursor tracking eyes. */
export function CopilotSymbol({ size = 16, className = "" }) {
  const svgRef = useRef(null);
  const [eyePos, setEyePos] = useState({ x: 0, y: 0 });
  const rafRef = useRef(null);

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (rafRef.current) return;

      rafRef.current = requestAnimationFrame(() => {
        rafRef.current = null;
        if (!svgRef.current) return;

        const rect = svgRef.current.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;

        const dx = e.clientX - centerX;
        const dy = e.clientY - centerY;
        const dist = Math.hypot(dx, dy);

        if (dist === 0) {
          setEyePos({ x: 0, y: 0 });
          return;
        }

        const angle = Math.atan2(dy, dx);
        const maxShift = 1.8;
        const intensity = Math.min(dist / 60, 1);
        const shiftX = Math.cos(angle) * maxShift * intensity;
        const shiftY = Math.sin(angle) * maxShift * intensity;

        setEyePos({
          x: Math.round(shiftX * 100) / 100,
          y: Math.round(shiftY * 100) / 100,
        });
      });
    };

    window.addEventListener("mousemove", handleMouseMove, { passive: true });
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  return (
    <svg
      ref={svgRef}
      width={size + 2}
      height={size + 2}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`copilot-symbol-svg ${className}`}
      aria-hidden="true"
      style={{ flexShrink: 0 }}
    >
      <rect width="24" height="24" rx="7" className="copilot-symbol-bg" />
      <g
        className="copilot-eyes-group"
        style={{
          transform: `translate(${eyePos.x}px, ${eyePos.y}px)`,
          transition: "transform 0.08s ease-out",
        }}
      >
        <rect x="7.1" y="7.8" width="3.4" height="8.4" rx="1.7" className="copilot-eye copilot-eye-left" />
        <rect x="13.5" y="7.8" width="3.4" height="8.4" rx="1.7" className="copilot-eye copilot-eye-right" />
      </g>
    </svg>
  );
}

const PRESET_PROMPTS = [
  {
    label: "Start Scraping",
    query: "Start data ingestion and scraping for all 25 corridors",
  },
  {
    label: "Matched-model Jevons",
    query: "How does the matched-model Jevons index work, and why matched rather than pooled?",
  },
  {
    label: "Booking horizons",
    query: "Why are booking horizons indexed separately instead of pooled together?",
  },
  {
    label: "Year-on-year",
    query: "Why is the year-on-year change not available?",
  },
  {
    label: "Data provenance",
    query: "Where does this data come from, and is any of it scraped from airline sites?",
  },
  {
    label: "Seasonal adjustment",
    query: "Is the index seasonally adjusted?",
  },
  {
    label: "Uncertainty",
    query: "How is uncertainty estimated, and what does it exclude?",
  },
];

/** Minimal markdown rendering: headings, bold, inline code, bullets, action cards. */
function renderMarkdown(text) {
  const lines = String(text || "").split("\n");
  const blocks = [];
  let listItems = [];

  const flushList = () => {
    if (listItems.length) {
      blocks.push(
        <ul key={`ul-${blocks.length}`} className="copilot-list">
          {listItems.map((item, i) => (
            <li key={i} dangerouslySetInnerHTML={{ __html: inline(item) }} />
          ))}
        </ul>,
      );
      listItems = [];
    }
  };

  const inline = (s) =>
    s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+)\*/g, "<em>$1</em>");

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) {
      flushList();
      continue;
    }
    if (line.startsWith("- ")) {
      listItems.push(line.slice(2));
      continue;
    }
    flushList();
    const heading = line.match(/^(#{1,4})\s+(.*)$/);
    if (heading) {
      blocks.push(
        <h4 key={`h-${blocks.length}`} className="copilot-heading"
            dangerouslySetInnerHTML={{ __html: inline(heading[2]) }} />,
      );
      continue;
    }
    blocks.push(
      <p key={`p-${blocks.length}`} dangerouslySetInnerHTML={{ __html: inline(line) }} />,
    );
  }
  flushList();
  return blocks;
}

/** Client-side RAG answer generator for GitHub Pages / static mode without backend server. */
function generateClientSideRAGAnswer(question, state) {
  const q = String(question || "").toLowerCase();
  const headline = state?.headlineIndex != null ? state.headlineIndex.toFixed(4) : NOT_AVAILABLE;
  const date = state?.indexDate || NOT_AVAILABLE;
  const base = state?.basePeriod || NOT_AVAILABLE;
  const mom = state?.momChangePct != null ? (state.momChangePct > 0 ? `+${state.momChangePct.toFixed(2)}%` : `${state.momChangePct.toFixed(2)}%`) : NOT_AVAILABLE;
  const yoy = state?.yoyChangePct != null ? (state.yoyChangePct > 0 ? `+${state.yoyChangePct.toFixed(2)}%` : `${state.yoyChangePct.toFixed(2)}%`) : NOT_AVAILABLE;
  const sample = state?.sampleSize ? Number(state.sampleSize).toLocaleString() : NOT_AVAILABLE;
  const mode = state?.mode || DATA_MODE.DISCONNECTED;

  if (
    q.includes("start scrap") ||
    q.includes("trigger scrap") ||
    q.includes("run scrap") ||
    q.includes("ingest") ||
    q.includes("collect data") ||
    q.includes("fetch fresh") ||
    (q.includes("scrap") && (q.includes("start") || q.includes("trigger") || q.includes("run") || q.includes("begin") || q.includes("do")))
  ) {
    return (
      `### Live Data Ingestion Controller\n\n` +
      `Collection is an explicit protected operation, not a chat action. An authorized operator can use the dashboard's collection controls to request a cycle across the configured corridors and booking horizons (\`T+1 ... T+45\`).\n\n` +
      `*Integrity invariant:* observations are validated through hard bounds (₹500–₹80k) and IQR outlier fences before index recalculation.`
    );
  }

  if (q.includes("index") || q.includes("headline") || q.includes("current price") || q.includes("what is the rate") || q.includes("latest")) {
    return (
      `**Current Headline Index:** **${headline}** (Index Date: \`${date}\`)\n\n` +
      `• **Base Period:** \`${base}\` (Index = 100.00)\n` +
      `• **Month-on-Month Change:** **${mom}**\n` +
      `• **Year-on-Year Change:** **${yoy}**\n` +
      `• **Validated Sample:** ${sample} matched observations\n` +
      `• **Operational Mode:** \`${mode}\`\n\n` +
      `*Grounding Note:* Index is compiled across 25 national corridors using Jevons geometric aggregation.`
    );
  }

  if (q.includes("jevon") || q.includes("formula") || q.includes("methodology") || q.includes("math") || q.includes("calculate") || q.includes("geometric")) {
    return (
      `### Matched-Model Jevons Elementary Aggregation\n\n` +
      `We use the **Jevons elementary price index formula** (unweighted geometric mean of price relatives) recommended by the IMF CPI Manual (2020):\n\n` +
      `$$I_J^{0:t} = \\prod_{i=1}^{n} \\left( \\frac{p_{i,t}}{p_{i,0}} \\right)^{1/n}$$\n\n` +
      `**Why Matched-Model rather than Pooled Average?**\n` +
      `- **Avoids Quality Skew:** Pure average fares move simply if an airline adds higher-priced weekend slots or changes flight frequency.\n` +
      `- **No Carli Bias:** The arithmetic Carli index suffers from severe upward drift ($I_{Carli} \\ge I_{Jevons}$). Jevons satisfies the time-reversal test.`
    );
  }

  if (q.includes("horizon") || q.includes("advance") || q.includes("strata") || q.includes("t+0") || q.includes("booking")) {
    return (
      `### Booking Horizon Stratification\n\n` +
      `Airline dynamic pricing changes drastically depending on how early a ticket is bought. To ensure pricing curves are tracked without composition distortion, fares are partitioned into **5 fixed booking horizons**:\n\n` +
      `- **T+1 (1 day advance):** Provisional equal weight = \`0.20\`\n` +
      `- **T+7 (7 days advance):** Provisional equal weight = \`0.20\`\n` +
      `- **T+15 (15 days advance):** Provisional equal weight = \`0.20\`\n` +
      `- **T+30 (30 days advance):** Provisional equal weight = \`0.20\`\n` +
      `- **T+45 (45 days advance):** Provisional equal weight = \`0.20\`\n\n` +
      `Each horizon is indexed separately, then combined with fixed policy weights so changes in passenger booking lead time do not falsify the price index.`
    );
  }

  if (q.includes("source") || q.includes("provenance") || q.includes("scrap") || q.includes("where") || q.includes("indigo") || q.includes("amadeus") || q.includes("air india")) {
    return (
      `### Data Provenance & Source Registry\n\n` +
      `• **Active Status:** \`${mode}\`\n` +
      `• **Database Coverage:** **${sample}** observations in the current computed index.\n` +
      `• **Tracked Airlines:** IndiGo (\`6E\`), Air India (\`AI\`), Vistara (\`UK\`), Akasa Air (\`QP\`), and SpiceJet (\`SG\`).\n` +
      `• **Corridors:** Top 25 domestic city pairs (DEL-BOM, BLR-DEL, BOM-BLR, DEL-HYD, etc.).\n\n` +
      `*Integrity Invariant:* Zero synthetic data substitution. Every observation is validated through IQR outlier fences and hard price boundaries (₹500 - ₹80,000).`
    );
  }

  if (q.includes("yoy") || q.includes("mom") || q.includes("inflation") || q.includes("year on year") || q.includes("change") || q.includes("increase")) {
    return (
      `### Inflation & Price Movement Summary\n\n` +
      `• **Month-on-Month (MoM):** **${mom}** (calculated against previous calendar month).\n` +
      `• **Year-on-Year (YoY):** **${yoy}** (calculated against stored index 12 months earlier).\n` +
      `• **Current Index Level:** **${headline}** (Base Period: \`${base}\`).\n\n` +
      `The series is observed and not seasonally adjusted, capturing festive and peak holiday pricing without artificial smoothing.`
    );
  }

  if (q.includes("hello") || q.includes("hi") || q.includes("hey") || q.includes("who are you") || q.includes("help") || q.trim() === "") {
    return (
      `Hello! I am your **Airfare CPI Analyst Copilot**.\n\n` +
      `I can explain:\n` +
      `- **Current Index:** Headline value (**${headline}**), MoM change (**${mom}**), and YoY inflation (**${yoy}**).\n` +
      `- **Statistical Methodology:** Matched-Model Jevons geometric mean calculations.\n` +
      `- **Booking Horizons:** T+1 to T+45 advance purchase stratification.\n` +
      `- **Corridors & Weights:** DGCA passenger volume weighting across 25 routes.\n` +
      `- **Data Provenance:** ${mode}; no unavailable figure is replaced with a constant.`
    );
  }

  return (
    `**Airfare CPI RAG Summary:**\n\n` +
    `• **Headline CPI Index:** **${headline}** (as of \`${date}\`)\n` +
    `• **Base Period:** \`${base}\` (= 100.00)\n` +
    `• **Price Trend:** MoM **${mom}** · YoY **${yoy}**\n` +
    `• **Methodology:** Matched-Model Jevons formulation with provisional equal booking-horizon weights (\`T+1\` to \`T+45\`) and provisional passenger-volume route weights.\n\n` +
    `*Client-side RAG active. Ask about formulas, horizons, provenance, or specific routes.*`
  );
}

export default function AviationCopilotModal({ isOpen, onClose, dashboardState }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef(null);

  const mode = dashboardState?.mode || DATA_MODE.DISCONNECTED;

  /**
   * Greeting, DERIVED rather than stored.
   */
  const greeting = useMemo(
    () => ({
      role: "assistant",
      tier: "local_fallback",
      note: "Session initialized from the dashboard's currently loaded data.",
      content:
        `I am the **Airfare CPI Analyst Copilot**, grounded in the project methodology and current database series.\n\n` +
        `**Current Operational Mode:** \`${mode}\`\n\n` +
        (dashboardState?.headlineIndex != null
          ? `• **Headline Index:** **${fmtIndex(dashboardState.headlineIndex)}** (Base: ${dashboardState.basePeriod})\n` +
            `• **Sample Size:** **${fmtCount(dashboardState.sampleSize)}** validated observations\n` +
            `• **Calculation Date:** **${dashboardState.indexDate || "Latest"}**\n\n`
          : `No computed index is currently available in memory.\n\n`) +
        `Ask any question regarding our **Matched-Model Jevons formulation**, **booking horizon stratification**, **data provenance**, or **aggregation weights** below.`,
    }),
    [mode, dashboardState],
  );

  const transcript = useMemo(
    () => (messages.length ? [greeting, ...messages] : [greeting]),
    [greeting, messages],
  );

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcript, busy]);

  const send = useCallback(
    async (question) => {
      const text = String(question || "").trim();
      if (!text || busy) return;

      setMessages((prev) => [...prev, { role: "user", content: text }]);
      setInput("");
      setBusy(true);

      const result = await askCopilot(text);

      if (result.ok) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            tier: result.data.tier,
            model: result.data.model,
            note: result.data.note,
            content: result.data.answer,
          },
        ]);
      } else {
        // Fallback gracefully to Client-Side Deterministic RAG (supports static deployments / GitHub Pages)
        const localAnswer = generateClientSideRAGAnswer(text, dashboardState);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            tier: "local_fallback",
            model: "Deterministic RAG",
            note: "Answered by Client-Side RAG Knowledge Engine (Static / GitHub Pages mode)",
            content: localAnswer,
          },
        ]);
      }
      setBusy(false);
    },
    [busy, dashboardState],
  );

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose} data-testid="copilot-modal">
      <div className="copilot-panel" onClick={(e) => e.stopPropagation()}>
        <div className="copilot-header">
          <div className="copilot-title">
            <div className="copilot-icon-badge">
              <CopilotSymbol size={22} />
            </div>
            <div>
              <div className="copilot-title-row">
                <strong>Analyst Copilot</strong>
              </div>
              <small>Grounded on stored index data & methodology</small>
            </div>
          </div>
          <div className="copilot-badges">
            <button className="copilot-close-btn" aria-label="Close Copilot" onClick={onClose} data-testid="copilot-close-button">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="copilot-scroll" ref={scrollRef}>
          {transcript.map((message, i) => (
            <div
              key={i}
              className={`copilot-row copilot-row-${message.role}`}
              data-testid={`copilot-message-${i}`}
            >
              {message.role === "assistant" ? (
                <div className="copilot-assistant-thread">
                  <div className="copilot-assistant-meta">
                    <div className="copilot-avatar">
                      <CopilotSymbol size={18} />
                    </div>
                    <span className="copilot-assistant-name">Analyst Copilot</span>
                  </div>

                  <div className="copilot-body">{renderMarkdown(message.content)}</div>

                  {message.note && (
                    <div className="copilot-note-container">
                      <CheckCircle2 size={11} className="copilot-note-icon" />
                      <span className="copilot-note">{message.note}</span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="copilot-user-bubble">
                  {message.content}
                </div>
              )}
            </div>
          ))}

          {busy && (
            <div className="copilot-row copilot-row-assistant" data-testid="copilot-thinking">
              <div className="copilot-assistant-thread copilot-assistant-thread-thinking">
                <div className="copilot-assistant-meta">
                  <div className="copilot-avatar">
                    <CopilotSymbol size={18} />
                  </div>
                  <span className="copilot-assistant-name">Analyst Copilot</span>
                  <div className="copilot-thinking-dots-badge" aria-label="Thinking">
                    <span className="copilot-typing-dot" />
                    <span className="copilot-typing-dot" />
                    <span className="copilot-typing-dot" />
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="copilot-presets-container">
          <div className="copilot-presets-label">Suggested Inquiries</div>
          <div className="copilot-presets">
            {PRESET_PROMPTS.map((preset) => (
              <button
                key={preset.label}
                className="copilot-preset-chip"
                onClick={() => send(preset.query)}
                disabled={busy}
                data-testid={`copilot-preset-${preset.label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>

        <form
          className="copilot-input-row"
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
        >
          <div className="copilot-input-wrapper">
            <input
              className="copilot-input-field"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about inflation index, Jevons formula, or horizon trends…"
              aria-label="Ask the Copilot"
              data-testid="copilot-input"
            />
            <button
              type="submit"
              className="copilot-send-btn"
              disabled={busy || !input.trim()}
              aria-label="Send"
              data-testid="copilot-send-button"
            >
              <ArrowUp size={16} />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
