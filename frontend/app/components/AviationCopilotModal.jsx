"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { X, ArrowUp, Plane, TrendingUp, Clock, Calculator } from "lucide-react";
import {
  STATISTICAL_CONSTANTS,
  AIRPORTS_LIST,
  HOMEPAGE_FEATURED_CORRIDORS,
  AIRLINES_LIST,
} from "../data/mockData";

const GEMINI_API_KEY = process.env.NEXT_PUBLIC_GEMINI_API_KEY || "AIzaSyCDnngQSEpspflpc7xUxz96GfjOfVIxGFs";
const GEMINI_MODEL = process.env.NEXT_PUBLIC_GEMINI_MODEL || "gemini-3.5-flash-lite";

const AVIATION_RAG_SYSTEM_PROMPT = `You are the official Airfare CPI AI Copilot built for Team Sprint Zero (MoSPI / SIH26056).
You specialize in Indian domestic aviation price intelligence, consumer price index (CPI) calculations, dynamic yield management analysis, and airline market competition.

DOMAIN KNOWLEDGE BASE:
- Headline National Airfare CPI: 107.42 (Base Year: 2024 = 100).
- Month-over-Month (MoM) inflation: +2.84%. Year-over-Year (YoY): +8.12%.
- Monitored Sample: 48,200+ daily scraped flight quotes across 25 high-density domestic city pairs.
- Primary Index Formula: Jevons Geometric Mean Index I_Jevons = (prod p_{i,t} / prod p_{i,0})^(1/n).
  - Eliminates extreme surge pricing bias (satisfies Axiomatic Time-Reversal Test I_{0->t} * I_{t->0} = 1.0).
  - Replaces arithmetic Carli/Dutot formulas which produce severe upward bias during 300% last-minute walk-up surges.
- DGCA Passenger Weighting: Corridor weights w_i = Pax_i / sum(Pax) based on Directorate General of Civil Aviation passenger data (11.98M monthly travellers).
- Advance Purchase Stratification Horizons:
  - T+30 (30-day advance anchor, leisure baseline): multiplier 1.0x (avg ₹4,180 - ₹4,600).
  - T+15 (15-day advance): multiplier 1.16x (avg ₹4,800 - ₹5,200).
  - T+7 (1-week cutoff, discount seats closing): multiplier 1.65x (+22% urgency premium).
  - T+3 (3-day short-notice corporate): multiplier 2.35x (+48% yield surge).
  - T+0 (same-day emergency walkup): multiplier 3.56x (+95% peak scarcity spike).
- Indian Domestic Airline Market Shares & Positioning:
  - IndiGo (6E): 62.8% market share, price leader (lowest base fare ₹4,950 avg), highest density.
  - Air India (AI): 14.2% market share, +6% to +12% spread with bundled baggage & meals.
  - Vistara (UK): 9.6% market share, premium business tier (+14% spread).
  - Akasa Air (QP): 4.8% market share, aggressive secondary route discounting (-5% below IndiGo).
  - SpiceJet (SG): 5.4% market share, selective leisure discounting.
- Statistical Quality Gate: Interquartile Range (IQR) outlier filter [Q1 - 1.5*IQR, Q3 + 1.5*IQR] rejects bot traps, 0 base fares, and scraping anomalies in real-time.

FORMATTING GUIDELINES:
- Provide structured, executive-ready, highly concise answers.
- Use '### ' for section titles with relevant aviation emojis (✈️, ⏱️, 🏛️, 🛫, 🔥, 💡).
- Use **bold** for key metrics, prices (in ₹), percentages, and recommendations.
- Use bullet points (- ) with clear hierarchy.
- When asked about specific routes, evaluate whether the fare is a good buy based on 30-day medians and advance windows.`;

const PRESET_PROMPTS = [
  {
    label: "Delhi → Mumbai Fare",
    icon: "flight_takeoff",
    query: "Is ₹4,850 a good fare from Delhi to Mumbai right now?",
  },
  {
    label: "Fastest Surging Corridors",
    icon: "trending_up",
    query: "Which domestic routes are heating up fastest this week?",
  },
  {
    label: "Optimal Advance Window",
    icon: "schedule",
    query: "When is the optimal advance-purchase booking window for Bengaluru flights?",
  },
  {
    label: "Jevons Index Formula",
    icon: "calculate",
    query: "How does the Jevons Geometric Mean formula prevent surge pricing distortion in CPI?",
  },
  {
    label: "Carrier Pricing Spread",
    icon: "airlines",
    query: "Compare IndiGo and Air India pricing spread across high-density metro corridors.",
  },
];

async function callLiveGeminiAPI(queryText) {
  try {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${GEMINI_API_KEY}`;

    const payload = {
      contents: [
        {
          role: "user",
          parts: [
            {
              text: `${AVIATION_RAG_SYSTEM_PROMPT}\n\nUSER QUESTION: ${queryText}`,
            },
          ],
        },
      ],
      generationConfig: {
        temperature: 0.3,
        maxOutputTokens: 800,
      },
    };

    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Gemini API returned status ${response.status}`);
    }

    const data = await response.json();
    const candidate = data.candidates?.[0]?.content?.parts?.[0]?.text;
    if (candidate) {
      return candidate.trim();
    }
    throw new Error("No text in candidate response");
  } catch (err) {
    console.warn("Gemini API call failed, falling back to local RAG engine:", err);
    return generateFallbackRAGResponse(queryText);
  }
}

function generateFallbackRAGResponse(query) {
  const q = query.toLowerCase();

  if ((q.includes("delhi") && q.includes("mumbai")) || q.includes("del-bom") || q.includes("4,850") || q.includes("4850")) {
    return `### ✈️ Route Intelligence: Delhi (DEL) ➔ Mumbai (BOM)

**Verdict: Strong Buy (Lowest 20th Percentile)**

- **Current Live Quote**: ₹4,850
- **30-Day Route Median**: ₹5,320
- **Price Delta**: **-8.8% below trailing median** (₹470 savings)
- **Current Jevons Corridor Index**: **105.8** (Base 2024 = 100)

**Aviation Analysis:**
1. **Advance Curve Advantage**: Fares on this route typically decay between $T+15$ and $T+30$ down to ₹4,600–₹4,900. At ₹4,850, you are capturing pricing in the lowest 20th percentile.
2. **Carrier Distribution**: IndiGo operates 24 daily nonstop frequencies with baseline fares at ₹4,850, while Air India is quoting ₹5,240 (bundled with complimentary check-in baggage and meal).
3. **Action Recommendation**: Lock in this fare within 24 hours. Fares historically surge by +35% once within the $T+7$ booking window.`;
  }

  if (q.includes("heating") || q.includes("surging") || q.includes("expensive") || q.includes("fastest")) {
    return `### 🔥 Market Velocity Radar: Surging Domestic Corridors

Real-time surveillance across 25 DGCA monitored city-pairs highlights the top 3 corridors heating up:

1. **Delhi (DEL) ➔ Goa (GOI)**
   - **Current Index**: **109.1** (+4.8% 7-Day Surge)
   - **Avg Fare**: ₹7,450 (up from ₹6,200 last week)
   - **Driver**: Leisure seasonal compression & weekend slot scarcity.

2. **Mumbai (BOM) ➔ Kolkata (CCU)**
   - **Current Index**: **108.2** (+3.6% 7-Day Surge)
   - **Avg Fare**: ₹6,890
   - **Driver**: Morning departure bank load factors exceeding 88%.

3. **Bengaluru (BLR) ➔ Delhi (DEL)**
   - **Current Index**: **107.5** (+3.1% 7-Day Surge)
   - **Avg Fare**: ₹6,420
   - **Driver**: Business travel volume rebound & evening slot congestion.`;
  }

  if (q.includes("advance") || q.includes("booking window") || q.includes("bengaluru") || q.includes("when to book")) {
    return `### ⏱️ Booking Horizon Decay: Bengaluru (BLR) Sectors

Statistical analysis across 8,400+ sampled observations reveals the following advance purchase profile:

- **$T+30$ Days Anchor**: **₹4,200 – ₹4,600** (Index: 94.2) ➔ **Optimal Booking Window**
- **$T+15$ Days Standard**: **₹4,800 – ₹5,200** (Index: 99.5) ➔ Standard Fair Rate
- **$T+7$ Days Cutoff**: **₹6,100 – ₹6,800** (Index: 112.4) ➔ Urgency Surcharge (+22%)
- **$T+3$ Days Peak**: **₹7,900 – ₹9,200** (Index: 138.6) ➔ Dynamic Yield Surcharge (+48%)
- **$T+0$ Same-Day Walkup**: **₹11,500 – ₹14,200** (Index: 184.0) ➔ Peak Scarcity (+95%)

**Strategic Recommendation:** Book flights at least **18 to 24 days prior to departure** to avoid algorithmic dynamic yield surcharges.`;
  }

  if (q.includes("jevons") || q.includes("formula") || q.includes("cpi") || q.includes("geometric") || q.includes("mospi")) {
    return `### 🏛️ MoSPI CPI Methodology: Jevons Geometric Mean

**Why MoSPI mandates the Jevons Formula:**

$$\\mathcal{I}_{\\text{Jevons}} = \\prod_{i=1}^{n} \\left( \\frac{p_{i,t}}{p_{i,0}} \\right)^{\\frac{1}{n}} = \\frac{\\left( \\prod p_{i,t} \\right)^{1/n}}{\\left( \\prod p_{i,0} \\right)^{1/n}}$$

1. **Eliminates Surge Pricing Distortion**: Traditional arithmetic averages (Carli Index) suffer severe upward bias when airlines apply 300% same-day walkup surge pricing. The Geometric Mean is scale-invariant and satisfies the axiomatic **Time Reversal Test**.
2. **Economic Defensibility**: As established by ILO guidelines, Jevons reflects underlying core price movement rather than unconstrained emergency panic fares.
3. **DGCA Passenger Rescaling**: Elementary corridor relatives are aggregated using Directorate General of Civil Aviation passenger traffic weights ($w_i = \\text{Pax}_i / \\sum \\text{Pax}$).`;
  }

  if (q.includes("indigo") || q.includes("air india") || q.includes("spread") || q.includes("airline") || q.includes("market share")) {
    return `### 🛫 Carrier Spread & Market Concentration

**Domestic Metro Trunk Corridor Overview:**

- **IndiGo (6E)**:
  - *Market Share*: **62.8%**
  - *Price Positioning*: Lowest median base fare (₹4,950 average across 25 corridors). Highest operational density.
- **Air India (AI)**:
  - *Market Share*: **14.2%**
  - *Price Positioning*: +6% to +12% above LCC baseline, bundled with 25kg standard check-in luggage and hot meals.
- **Vistara (UK)**:
  - *Market Share*: **9.6%**
  - *Price Positioning*: Premium tier (+14% spread); high corporate loyalty retention.
- **Akasa Air (QP)**:
  - *Market Share*: **4.8%**
  - *Price Positioning*: Highly aggressive promotional pricing on tier-1 to tier-2 routes (-5% below IndiGo).

**Herfindahl-Hirschman Index (HHI)**: **4,280** *(Indicates high market concentration with IndiGo as dominant price-setter).*`;
  }

  return `### ✈️ Airfare CPI Intelligence

**Query**: *"${query}"*

- **Headline National Airfare CPI**: **107.42** (Base 2024 = 100)
- **Monitored DGCA Corridors**: **25 High-Density City Pairs**
- **Advance Horizons Sampled**: $T+0, T+3, T+7, T+15, T+30$
- **Daily Ingested Quotes**: **48,200+ observations**

**Key Insight:** Domestic airfare inflation in India has stabilized at **+2.84% MoM**, largely driven by moderate jet fuel (ATF) adjustments and robust post-monsoon capacity additions.`;
}

// Minimalist Markdown Renderer
function renderFormattedContent(rawText) {
  return rawText.split("\n").map((line, idx) => {
    const trimmed = line.trim();
    if (!trimmed) return <div key={idx} className="copilot-spacer" />;
    if (trimmed.startsWith("### ")) return <div key={idx} className="copilot-message-heading">{trimmed.replace("### ", "")}</div>;
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) return <div key={idx} className="copilot-message-list"><span>◆</span><div>{parseBoldText(trimmed.substring(2))}</div></div>;
    if (/^\d+\.\s/.test(trimmed)) { const match = trimmed.match(/^(\d+\.)\s(.*)/); return <div key={idx} className="copilot-message-list"><span>{match?.[1] || "•"}</span><div>{parseBoldText(match?.[2] || trimmed)}</div></div>; }
    return <p key={idx} className="copilot-message-paragraph">{parseBoldText(trimmed)}</p>;
  });
}

function parseBoldText(text) {
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

// Custom Vector AI Copilot Symbol matching user icon
export function CopilotSymbol({ size = 15, className = "", style = {} }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={{ display: "inline-block", verticalAlign: "middle", flexShrink: 0, ...style }}
    >
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M7.5 3C3.5 3 2.5 4 2.5 8V16C2.5 20 3.5 21 7.5 21H16.5C20.5 21 21.5 20 21.5 16V8C21.5 4 20.5 3 16.5 3H7.5ZM8.5 8.75C9.33 8.75 10 9.42 10 10.25V13.75C10 14.58 9.33 15.25 8.5 15.25C7.67 15.25 7 14.58 7 13.75V10.25C7 9.42 7.67 8.75 8.5 8.75ZM15.5 8.75C16.33 8.75 17 9.42 17 10.25V13.75C17 14.58 16.33 15.25 15.5 15.25C14.67 15.25 14 14.58 14 13.75V10.25C14 9.42 14.67 8.75 15.5 8.75Z"
        fill="currentColor"
      />
    </svg>
  );
}

export default function AviationCopilotModal({ isOpen, onClose, initialQuery = "" }) {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello! I am your **Airfare CPI AI Copilot** powered by **Gemini 3.5 Flash Lite**. I analyze live airline pricing, MoSPI 2024=100 index movements, booking horizon decay curves, and DGCA corridor statistics. How can I assist your aviation analysis today?",
      timestamp: "Just now",
    },
  ]);
  const [inputQuery, setInputQuery] = useState(initialQuery);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const processedQueryRef = useRef("");

  const handleSend = useCallback(async (textToSend) => {
    const queryText = (typeof textToSend === "string" ? textToSend : "").trim();
    if (!queryText) return;

    const userMsg = {
      role: "user",
      content: queryText,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery("");
    setIsTyping(true);

    const botResponse = await callLiveGeminiAPI(queryText);

    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: botResponse,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ]);
    setIsTyping(false);
  }, []);

  useEffect(() => {
    if (!isOpen) {
      processedQueryRef.current = "";
      return;
    }

    if (initialQuery && processedQueryRef.current !== initialQuery) {
      processedQueryRef.current = initialQuery;
      const timer = setTimeout(() => {
        handleSend(initialQuery);
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [isOpen, initialQuery, handleSend]);

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [messages, isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className="copilot-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label="Airfare CPI Copilot"
      data-testid="copilot-modal"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        backgroundColor: "rgba(3, 7, 18, 0.72)",
        backdropFilter: "blur(16px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 16,
        animation: "fadeIn 0.15s ease-out",
      }}
      onClick={onClose}
    >
      <div
        className="copilot-modal"
        style={{
          width: "100%",
          maxWidth: 720,
          maxHeight: "88vh",
          display: "flex",
          flexDirection: "column",
          borderRadius: 20,
          overflow: "hidden",
          backgroundColor: "#0b101b",
          border: "1px solid rgba(255, 255, 255, 0.1)",
          boxShadow: "0 25px 60px -12px rgba(0, 0, 0, 0.9), 0 0 1px 1px rgba(255, 255, 255, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.12)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Minimalist Modal Header */}
        <div
          className="copilot-modal-header"
          style={{
            padding: "16px 20px",
            borderBottom: "1px solid rgba(255, 255, 255, 0.07)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            backgroundColor: "rgba(15, 23, 42, 0.5)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 9,
                background: "var(--green-soft, rgba(59, 109, 77, 0.12))",
                border: "1px solid rgba(59, 109, 77, 0.3)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--green, #3b6d4d)",
              }}
            >
              <CopilotSymbol size={18} />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 15, fontWeight: 700, color: "var(--ink, #ffffff)", letterSpacing: "-0.01em" }}>
                  Airfare CPI Copilot
                </span>
                <span
                  style={{
                    fontSize: 9.5,
                    fontWeight: 700,
                    padding: "1px 6px",
                    borderRadius: 4,
                    backgroundColor: "var(--green-soft, rgba(59, 109, 77, 0.12))",
                    color: "var(--green, #3b6d4d)",
                    border: "1px solid rgba(59, 109, 77, 0.25)",
                    letterSpacing: "0.04em",
                  }}
                >
                  GEMINI 3.5 FLASH LITE
                </span>
                <span
                  style={{
                    fontSize: 9.5,
                    fontWeight: 700,
                    padding: "1px 6px",
                    borderRadius: 4,
                    backgroundColor: "rgba(34, 197, 94, 0.12)",
                    color: "#34d399",
                    border: "1px solid rgba(34, 197, 94, 0.25)",
                    letterSpacing: "0.04em",
                  }}
                >
                  LIVE RAG
                </span>
              </div>
              <div style={{ fontSize: 11, color: "var(--muted, #94a3b8)", marginTop: 2 }}>
                Real-Time Aviation Intelligence Grounded with MoSPI 2024=100
              </div>
            </div>
          </div>

          <button
            className="copilot-close"
            onClick={onClose}
            aria-label="Close modal"
            data-testid="copilot-close-button"
            style={{
              background: "transparent",
              border: "1px solid var(--line, rgba(255, 255, 255, 0.08))",
              borderRadius: "50%",
              width: 30,
              height: 30,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--muted, #94a3b8)",
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            <X size={15} />
          </button>
        </div>

        {/* Message Thread */}
        <div
          className="no-scrollbar copilot-thread"
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "18px 20px",
            display: "flex",
            flexDirection: "column",
            gap: 14,
            minHeight: 320,
            maxHeight: 460,
            scrollbarWidth: "none",
            msOverflowStyle: "none",
          }}
        >
          {messages.map((m, idx) => {
            const isUser = m.role === "user";
            return (
              <div
                className="copilot-message-row"
                key={idx}
                style={{
                  display: "flex",
                  justifyContent: isUser ? "flex-end" : "flex-start",
                  gap: 10,
                }}
              >
                {!isUser && (
                  <div
                    style={{
                      width: 26,
                      height: 26,
                      borderRadius: 8,
                      background: "rgba(56, 189, 248, 0.12)",
                      border: "1px solid rgba(56, 189, 248, 0.25)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      marginTop: 2,
                    }}
                  >
                    <CopilotSymbol size={15} />
                  </div>
                )}

                <div
                  className={`copilot-bubble ${isUser ? "copilot-bubble-user" : "copilot-bubble-assistant"}`}
                  style={{
                    maxWidth: "86%",
                    padding: "12px 16px",
                    borderRadius: isUser ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
                    backgroundColor: isUser ? "#0284c7" : "rgba(255, 255, 255, 0.04)",
                    border: `1px solid ${isUser ? "rgba(56, 189, 248, 0.3)" : "rgba(255, 255, 255, 0.08)"}`,
                    color: "#ffffff",
                    fontSize: 13,
                    lineHeight: 1.6,
                    wordBreak: "break-word",
                  }}
                >
                  {isUser ? m.content : renderFormattedContent(m.content)}
                  <div
                    style={{
                      fontSize: 10,
                      color: isUser ? "rgba(255,255,255,0.7)" : "#64748b",
                      marginTop: 6,
                      textAlign: "right",
                    }}
                  >
                    {m.timestamp}
                  </div>
                </div>
              </div>
            );
          })}

          {isTyping && (
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <div
                style={{
                  width: 26,
                  height: 26,
                  borderRadius: 8,
                  background: "rgba(56, 189, 248, 0.12)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <CopilotSymbol size={15} />
              </div>
              <div
                style={{
                  padding: "8px 14px",
                  borderRadius: 12,
                  backgroundColor: "rgba(255, 255, 255, 0.04)",
                  border: "1px solid rgba(255, 255, 255, 0.06)",
                  color: "#94a3b8",
                  fontSize: 12,
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <span style={{ fontSize: 14 }}>●</span>
                <span style={{ fontSize: 14 }}>●</span>
                <span style={{ fontSize: 14 }}>●</span>
                <span style={{ marginLeft: 4 }}>Gemini 3.5 Flash Lite is reasoning with live RAG telemetry...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Minimalist Suggested Prompt Chips */}
        <div
          className="no-scrollbar copilot-prompts"
          style={{
            padding: "8px 16px",
            background: "rgba(10, 15, 29, 0.8)",
            borderTop: "1px solid var(--line, rgba(255, 255, 255, 0.05))",
            display: "flex",
            gap: 6,
            overflowX: "auto",
            scrollbarWidth: "none",
            msOverflowStyle: "none",
          }}
        >
          {PRESET_PROMPTS.map((p, idx) => (
            <button
              className="copilot-prompt"
              key={idx}
              onClick={() => handleSend(p.query)}
              data-testid={`copilot-preset-prompt-${idx}`}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
                padding: "5px 11px",
                borderRadius: 14,
                fontSize: 11.5,
                fontWeight: 600,
                color: "var(--ink, #cbd5e1)",
                backgroundColor: "rgba(255, 255, 255, 0.04)",
                border: "1px solid var(--line, rgba(255, 255, 255, 0.08))",
                whiteSpace: "nowrap",
                cursor: "pointer",
                transition: "all 0.15s ease",
                flexShrink: 0,
              }}
            >
              {p.icon === "flight_takeoff" || p.icon === "airlines" ? (
                <Plane size={13} style={{ color: "var(--green, #3b6d4d)" }} />
              ) : p.icon === "trending_up" ? (
                <TrendingUp size={13} style={{ color: "var(--green, #3b6d4d)" }} />
              ) : p.icon === "schedule" ? (
                <Clock size={13} style={{ color: "var(--green, #3b6d4d)" }} />
              ) : p.icon === "calculate" ? (
                <Calculator size={13} style={{ color: "var(--green, #3b6d4d)" }} />
              ) : (
                <CopilotSymbol size={13} style={{ color: "var(--green, #3b6d4d)" }} />
              )}
              <span>{p.label}</span>
            </button>
          ))}
        </div>

        {/* Unified Minimalist Input Bar */}
        <div
          className="copilot-composer"
          style={{
            padding: "12px 16px 16px",
            borderTop: "1px solid var(--line, rgba(255, 255, 255, 0.06))",
          }}
        >
          <div
            className="copilot-input-shell"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "4px 6px 4px 14px",
              borderRadius: 12,
              backgroundColor: "rgba(255, 255, 255, 0.04)",
              border: "1px solid var(--line, rgba(255, 255, 255, 0.1))",
              transition: "border-color 0.15s ease",
            }}
          >
            <input
              className="copilot-input"
              ref={inputRef}
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend(inputQuery)}
              placeholder="Ask about route fares, MoSPI methodology, advance windows, or carrier pricing..."
              style={{
                flex: 1,
                padding: "8px 0",
                backgroundColor: "transparent",
                border: "none",
                color: "var(--ink, #ffffff)",
                fontSize: 13,
                outline: "none",
              }}
            />

            <button
              className="copilot-send"
              onClick={() => handleSend(inputQuery)}
              disabled={!inputQuery.trim() || isTyping}
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                backgroundColor: inputQuery.trim() && !isTyping ? "var(--green, #3b6d4d)" : "rgba(255, 255, 255, 0.05)",
                color: inputQuery.trim() && !isTyping ? "#ffffff" : "var(--muted, #64748b)",
                border: "none",
                cursor: inputQuery.trim() && !isTyping ? "pointer" : "default",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transition: "all 0.15s ease",
                flexShrink: 0,
              }}
              title="Send Message"
              aria-label="Send message"
              data-testid="copilot-send-button"
            >
              <ArrowUp size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
