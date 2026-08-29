"use client";

import { useState, useRef, useEffect } from "react";
import {
  STATISTICAL_CONSTANTS,
  AIRPORTS_LIST,
  HOMEPAGE_FEATURED_CORRIDORS,
  AIRLINES_LIST,
} from "../data/mockData";

const PRESET_PROMPTS = [
  {
    label: "Delhi → Mumbai Fare Analysis",
    query: "Is ₹4,850 a good fare from Delhi to Mumbai right now?",
  },
  {
    label: "Fastest Surging Corridors",
    query: "Which domestic routes are heating up fastest this week?",
  },
  {
    label: "Optimal Advance Window",
    query: "When is the optimal advance-purchase booking window for Bengaluru flights?",
  },
  {
    label: "Jevons Formula Explained",
    query: "How does the Jevons Geometric Mean formula prevent surge pricing distortion in CPI?",
  },
  {
    label: "IndiGo vs Air India Spread",
    query: "Compare IndiGo and Air India pricing spread across high-density metro corridors.",
  },
];

function generateAviationResponse(query) {
  const q = query.toLowerCase();

  if (q.includes("delhi") && q.includes("mumbai") || q.includes("del-bom") || q.includes("4,850") || q.includes("4850")) {
    return `### ✈️ Route Analysis: Delhi (DEL) → Mumbai (BOM)

**Verdict: Excellent Value (Buy Recommendation)**

- **Current Quote**: ₹4,850
- **30-Day Route Median**: ₹5,320
- **Price Delta**: **-8.8% below trailing median** (₹470 savings)
- **Current Jevons Corridor Index**: **105.8** (Base 2024 = 100)

**Aviation Intelligence Summary:**
1. **Advance Window Benefit**: Fares on this route typically decay between $T+15$ and $T+30$ down to ₹4,600–₹4,900. At ₹4,850, you are capturing pricing in the lowest 20th percentile.
2. **Carrier Spread**: IndiGo currently operates 24 daily frequencies with baseline fares at ₹4,850, while Air India is quoting ₹5,240 (with complimentary baggage and meal inclusion).
3. **Recommendation**: Lock in this fare within 24 hours. Fares typically spike by +35% once the booking horizon crosses within $T+7$.`;
  }

  if (q.includes("heating") || q.includes("surging") || q.includes("expensive") || q.includes("fastest")) {
    return `### 🔥 Market Velocity Radar: Surging Domestic Corridors

Based on real-time crawling across 25 DGCA monitored city-pairs, here are the top 3 routes heating up:

1. **Delhi (DEL) → Goa (GOI)**
   - **Current Index**: **109.1** (+4.8% 7-Day Surge)
   - **Avg Fare**: ₹7,450 (up from ₹6,200 last week)
   - **Driver**: High seasonal leisure demand + compressed weekend inventory.

2. **Mumbai (BOM) → Kolkata (CCU)**
   - **Current Index**: **108.2** (+3.6% 7-Day Surge)
   - **Avg Fare**: ₹6,890
   - **Driver**: Load factors exceeding 88% across morning departure banks.

3. **Bengaluru (BLR) → Delhi (DEL)**
   - **Current Index**: **107.5** (+3.1% 7-Day Surge)
   - **Avg Fare**: ₹6,420
   - **Driver**: Business travel volume rebound and evening slot congestion.

💡 *Tip: You can set an automated Price Watch on any of these corridors to receive instant alerts when fare drops occur.*`;
  }

  if (q.includes("advance") || q.includes("booking window") || q.includes("bengaluru") || q.includes("when to book")) {
    return `### ⏱️ Booking Horizon Curve: Bengaluru (BLR) Sectors

Statistical decay analysis across 8,400+ sampled observations reveals the following advance purchase profile:

| Booking Horizon | Relative Price Index | Avg Fare Spread | Recommended Action |
| :--- | :---: | :---: | :--- |
| **$T+30$ Days** | **94.2** | ₹4,200 – ₹4,600 | 🟢 **Optimal Booking Window** |
| **$T+15$ Days** | **99.5** | ₹4,800 – ₹5,200 | 🟡 Fair Rate (Standard) |
| **$T+7$ Days** | **112.4** | ₹6,100 – ₹6,800 | 🟠 Urgency Surcharge (+22%) |
| **$T+3$ Days** | **138.6** | ₹7,900 – ₹9,200 | 🔴 Dynamic Yield Premium (+48%) |
| **$T+0$ (Same Day)** | **184.0** | ₹11,500 – ₹14,200 | ⚠️ Peak Scarcity (+95%) |

**Core Takeaway:** To avoid inflation-distorted yield management pricing, book Bengaluru flights at least **18 to 24 days prior to departure**.`;
  }

  if (q.includes("jevons") || q.includes("formula") || q.includes("cpi") || q.includes("geometric") || q.includes("mospi")) {
    return `### 🏛️ MoSPI CPI Methodology: Jevons Geometric Mean

**Why MoSPI uses the Jevons Index for Airfare CPI:**

$$\\mathcal{I}_{\\text{Jevons}} = \\prod_{i=1}^{n} \\left( \\frac{p_{i,t}}{p_{i,0}} \\right)^{\\frac{1}{n}} = \\frac{\\left( \\prod p_{i,t} \\right)^{1/n}}{\\left( \\prod p_{i,0} \\right)^{1/n}}$$

1. **Elimination of Extreme Surge Bias**: Traditional arithmetic means (Carli Index) suffer from upward bias when airlines apply 300% last-minute surge pricing. The Geometric Mean is scale-invariant and satisfies the **Time Reversal Test**.
2. **Axiomatic Defensibility**: As established by ILO and MoSPI's 2024 Base Year guidelines, the Jevons formula accurately measures underlying pure price change rather than consumer panic or extreme scarcity premiums.
3. **DGCA Passenger Weighting**: Elementary Jevons relatives are subsequently aggregated across corridors using Directorate General of Civil Aviation passenger traffic weights ($w_i = \\text{Pax}_i / \\sum \\text{Pax}$).`;
  }

  if (q.includes("indigo") || q.includes("air india") || q.includes("spread") || q.includes("airline") || q.includes("market share")) {
    return `### 🛫 Carrier Spread & Market Intelligence

**Domestic Carrier Pricing Overview (Metro Trunk Corridors):**

- **IndiGo (6E)**: 
  - *Market Share*: **62.8%**
  - *Price Positioning*: Lowest median base fare (₹4,950 average across 25 corridors). Highest operational punctuality and density.
- **Air India (AI)**:
  - *Market Share*: **14.2%**
  - *Price Positioning*: +6% to +12% above LCC baseline, bundled with 25kg standard check-in luggage and hot meals.
- **Vistara (UK)**:
  - *Market Share*: **9.6%**
  - *Price Positioning*: Premium tier (+14% spread); high corporate loyalty retention.
- **Akasa Air (QP)**:
  - *Market Share*: **4.8%**
  - *Price Positioning*: Highly aggressive promotional pricing on tier-1 to tier-2 routes (-5% below IndiGo).

**Herfindahl-Hirschman Index (HHI)**: **4,280** *(Indicates high market concentration with IndiGo as the dominant price-setter).*`;
  }

  return `### ✈️ Airfare CPI Intelligence Response

**Query**: *"${query}"*

- **Headline National Airfare CPI**: **107.42** (Base 2024 = 100)
- **Monitored DGCA Corridors**: **25 High-Density City Pairs**
- **Advance Horizons Sampled**: $T+0, T+3, T+7, T+15, T+30$
- **Daily Ingested Quotes**: **48,200+ observations**

**Key Insight:** Domestic airfare inflation in India has stabilized at **+2.84% MoM**, largely driven by moderate jet fuel (ATF) adjustments and robust post-monsoon capacity additions. 

*Try asking about specific routes (e.g. "Delhi to Mumbai"), booking horizons ("when should I book?"), or statistical formulas ("how does Jevons work?").*`;
}

export default function AviationCopilotModal({ isOpen, onClose, initialQuery = "" }) {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello! I am your **Airfare CPI AI Copilot**. I analyze live airline pricing, MoSPI 2024=100 index movements, booking horizon decay curves, and DGCA corridor statistics. How can I assist your aviation analysis today?",
      timestamp: "Just now",
    },
  ]);
  const [inputQuery, setInputQuery] = useState(initialQuery);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (initialQuery) {
      handleSend(initialQuery);
    }
  }, [initialQuery]);

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isOpen]);

  if (!isOpen) return null;

  const handleSend = (textToSend) => {
    const queryText = (textToSend || inputQuery).trim();
    if (!queryText) return;

    const userMsg = {
      role: "user",
      content: queryText,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery("");
    setIsTyping(true);

    setTimeout(() => {
      const botResponse = generateAviationResponse(queryText);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: botResponse,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
      setIsTyping(false);
    }, 600);
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        backgroundColor: "rgba(0, 0, 0, 0.65)",
        backdropFilter: "blur(8px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 16,
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 780,
          maxHeight: "90vh",
          display: "flex",
          flexDirection: "column",
          borderRadius: 24,
          overflow: "hidden",
          backgroundColor: "#0d121f",
          border: "1px solid rgba(56, 189, 248, 0.3)",
          boxShadow: "0 25px 60px rgba(0, 0, 0, 0.8), 0 0 40px rgba(56, 189, 248, 0.15)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: "18px 24px",
            borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "linear-gradient(90deg, rgba(15, 23, 42, 0.95), rgba(13, 18, 31, 0.95))",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div
              style={{
                width: 38,
                height: 38,
                borderRadius: 12,
                background: "linear-gradient(135deg, #006591, #38bdf8)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#ffffff",
                boxShadow: "0 0 16px rgba(56, 189, 248, 0.5)",
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 22 }}>
                smart_toy
              </span>
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 16, fontWeight: 800, color: "#ffffff", letterSpacing: "-0.01em" }}>
                  Airfare CPI AI Copilot
                </span>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 800,
                    padding: "2px 7px",
                    borderRadius: 6,
                    backgroundColor: "rgba(34, 197, 94, 0.18)",
                    color: "#22c55e",
                    border: "1px solid rgba(34, 197, 94, 0.3)",
                  }}
                >
                  LIVE RAG
                </span>
              </div>
              <div style={{ fontSize: 11, color: "#94a3b8" }}>
                Real-Time Aviation Intelligence & MoSPI Methodology Explainer
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: "rgba(255, 255, 255, 0.06)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              borderRadius: "50%",
              width: 32,
              height: 32,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#94a3b8",
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
              close
            </span>
          </button>
        </div>

        {/* Message Thread */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "20px 24px",
            display: "flex",
            flexDirection: "column",
            gap: 16,
            minHeight: 340,
            maxHeight: 480,
          }}
        >
          {messages.map((m, idx) => {
            const isUser = m.role === "user";
            return (
              <div
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
                      width: 28,
                      height: 28,
                      borderRadius: 8,
                      background: "rgba(56, 189, 248, 0.15)",
                      border: "1px solid rgba(56, 189, 248, 0.3)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "#38bdf8",
                      flexShrink: 0,
                      marginTop: 2,
                    }}
                  >
                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
                      auto_awesome
                    </span>
                  </div>
                )}

                <div
                  style={{
                    maxWidth: "84%",
                    padding: "12px 16px",
                    borderRadius: isUser ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
                    backgroundColor: isUser ? "#0284c7" : "rgba(30, 41, 59, 0.8)",
                    border: `1px solid ${isUser ? "rgba(56, 189, 248, 0.4)" : "rgba(255, 255, 255, 0.08)"}`,
                    color: "#ffffff",
                    fontSize: 13.5,
                    lineHeight: 1.6,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                  }}
                >
                  {m.content}
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
                  width: 28,
                  height: 28,
                  borderRadius: 8,
                  background: "rgba(56, 189, 248, 0.15)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#38bdf8",
                }}
              >
                <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
                  auto_awesome
                </span>
              </div>
              <div
                style={{
                  padding: "10px 16px",
                  borderRadius: 14,
                  backgroundColor: "rgba(30, 41, 59, 0.8)",
                  color: "#94a3b8",
                  fontSize: 12,
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <span className="typing-dot">●</span>
                <span className="typing-dot" style={{ animationDelay: "0.2s" }}>●</span>
                <span className="typing-dot" style={{ animationDelay: "0.4s" }}>●</span>
                <span style={{ marginLeft: 6 }}>Analyzing live flight observations...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Quick Prompt Chips */}
        <div
          style={{
            padding: "10px 24px",
            background: "rgba(15, 23, 42, 0.6)",
            borderTop: "1px solid rgba(255, 255, 255, 0.05)",
            display: "flex",
            gap: 8,
            overflowX: "auto",
          }}
        >
          {PRESET_PROMPTS.map((p, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(p.query)}
              style={{
                padding: "6px 12px",
                borderRadius: 20,
                fontSize: 11.5,
                fontWeight: 600,
                color: "#93c5fd",
                backgroundColor: "rgba(56, 189, 248, 0.08)",
                border: "1px solid rgba(56, 189, 248, 0.25)",
                whiteSpace: "nowrap",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div
          style={{
            padding: "16px 24px",
            borderTop: "1px solid rgba(255, 255, 255, 0.08)",
            display: "flex",
            gap: 12,
            alignItems: "center",
            backgroundColor: "#080d1a",
          }}
        >
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask about route fares, MoSPI methodology, advance windows, or carrier pricing..."
            style={{
              flex: 1,
              padding: "12px 18px",
              borderRadius: 12,
              backgroundColor: "rgba(30, 41, 59, 0.7)",
              border: "1px solid rgba(56, 189, 248, 0.2)",
              color: "#ffffff",
              fontSize: 13.5,
              outline: "none",
            }}
          />
          <button
            onClick={() => handleSend()}
            disabled={!inputQuery.trim() || isTyping}
            style={{
              padding: "12px 20px",
              borderRadius: 12,
              backgroundColor: inputQuery.trim() && !isTyping ? "#0284c7" : "rgba(255, 255, 255, 0.08)",
              color: inputQuery.trim() && !isTyping ? "#ffffff" : "#64748b",
              border: "none",
              fontWeight: 700,
              fontSize: 13.5,
              cursor: inputQuery.trim() && !isTyping ? "pointer" : "not-allowed",
              display: "flex",
              alignItems: "center",
              gap: 6,
              transition: "all 0.15s ease",
            }}
          >
            <span>Ask</span>
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
              send
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}
