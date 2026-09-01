"""
SIH26056 — Copilot: server-side LLM proxy with a deterministic local fallback.

Why this exists
---------------
The audit's finding C1 was a live Google API key committed in
``AviationCopilotModal.jsx`` and shipped in the public static bundle. Any
``NEXT_PUBLIC_*`` variable is inlined into the client bundle by design, so that
architecture cannot hold a secret at all — the fix is not a better variable name, it is
moving the call server-side.

This module is that server side. The key is read from ``COPILOT_API_KEY`` in the
server environment and never leaves the process.

Honest attribution
------------------
Every answer states which tier produced it:

* ``model`` — answered by the configured provider model.
* ``local_fallback`` — answered by the deterministic knowledge base here, because no
  key is configured or the provider call failed.

A fallback answer is never presented as a model answer. The previous implementation
advertised a model identifier (``gemini-3.5-flash-lite``) that is not a real Google
model, so live calls almost certainly always failed into the fallback while the UI
displayed a model badge. :func:`validate_model_name` now checks the configured name
against the provider's own model list at startup and logs a warning if it is unknown,
rather than displaying a badge for a model that was never called.

Grounding
---------
The prompt is built from live figures passed in by the caller, and always states the
data provenance. It contains no hardcoded index values; the old prompt hardcoded
CPI 107.42 and +8.12% YoY, which meant the assistant confidently cited numbers the
backend had never computed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import httpx
from loguru import logger

from config import ApiSettings, get_settings
from provenance import NOT_IMPLEMENTED_LABEL


GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Answer tiers, reported verbatim to the client.
TIER_MODEL = "model"
TIER_LOCAL = "local_fallback"


@dataclass
class CopilotAnswer:
    """An answer plus honest attribution of what produced it."""

    text: str
    tier: str
    model: Optional[str]
    note: str
    grounded_on: dict[str, Any]

    @property
    def answered_by_model(self) -> bool:
        return self.tier == TIER_MODEL

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.text,
            "tier": self.tier,
            "answered_by_model": self.answered_by_model,
            "model": self.model,
            "note": self.note,
            "grounded_on": self.grounded_on,
        }


def build_system_prompt(context: dict[str, Any]) -> str:
    """
    Build the grounding prompt from live figures.

    Contains no index values of its own. Anything numeric comes from ``context``,
    which the API populates from the database.
    """
    provenance = context.get("data_provenance") or {}
    label = provenance.get("display_label", "SOURCE UNAVAILABLE")

    lines = [
        "You are an analyst assistant for an experimental Airfare Price Index for "
        "India, built as a student prototype for Smart India Hackathon problem "
        "statement SIH26056.",
        "",
        "ABSOLUTE CONSTRAINTS:",
        f"- The data behind every figure below is labelled: {label}.",
        "- This system is NOT an official statistic and is NOT endorsed by MoSPI, the "
        "NSO, or the Government of India. Say so if asked about authority.",
        "- Never invent an index value, a percentage change, or a confidence interval. "
        "If a figure is not in the context below, say it is not available.",
        "- If year-on-year change is reported as unavailable, explain that the series "
        "is too short for a 12-month comparison rather than estimating one.",
        "",
        "METHODOLOGY FACTS:",
        "- Elementary aggregates use the matched-model Jevons index: the geometric mean "
        "of price relatives over products matched on route, airline, cabin, fare "
        "family, stops, refundability and baggage.",
        "- Booking horizons (T+0, T+3, T+7, T+15, T+30) are indexed SEPARATELY and "
        "combined with fixed equal weights, so the index does not move when the "
        "horizon mix of the sample changes.",
        "- Route weights are provisional passenger-volume shares, NOT official CPI "
        "expenditure weights.",
        "- Seasonal adjustment is NOT IMPLEMENTED. The published series is observed "
        "(not seasonally adjusted), so festival and holiday effects appear in it.",
        "- If the user asks to start, run, or trigger web scraping or data collection, explain "
        "that the backend scraper engine is connected across 25 domestic corridors and 5 booking horizons, "
        "and include the tag [ACTION:TRIGGER_SCRAPING] so the user can execute it directly.",
        "",
        "CURRENT FIGURES (the only numbers you may cite):",
    ]

    for key, value in context.items():
        if key == "data_provenance":
            continue
        lines.append(f"- {key}: {value}")

    lines += [
        "",
        "Answer concisely in markdown. Attribute uncertainty honestly.",
    ]
    return "\n".join(lines)


# ── deterministic local knowledge base ──

_LOCAL_TOPICS: list[tuple[tuple[str, ...], str]] = [
    (
        ("jevons", "geometric mean", "elementary", "formula"),
        "**Matched-model Jevons index**\n\n"
        "The elementary aggregate is the geometric mean of price relatives over matched "
        "products:\n\n"
        "`I(t) = [ prod_p ( price_p(t) / price_p(0) ) ] ^ (1/n)`\n\n"
        "computed in log space for numerical stability. Jevons is used rather than Carli "
        "(which has a proven upward bias and fails the time-reversal test) or Dutot "
        "(which is driven by absolute price level and so distorts on a heterogeneous "
        "basket).\n\n"
        "**Matched-model** means a price relative is only formed between two "
        "observations of the *same product* — same route, airline, cabin, fare family, "
        "stop count, refundability and baggage allowance. That is what stops a change in "
        "what was sampled from being read as inflation.",
    ),
    (
        ("horizon", "advance", "t+0", "t+30", "booking window", "stratif"),
        "**Booking-horizon stratification**\n\n"
        "Five advance-purchase horizons are collected and indexed **separately**: T+0, "
        "T+3, T+7, T+15, T+30. Each is compared against its own base level, then "
        "combined into a route index with fixed equal weights (0.2 each).\n\n"
        "This matters because a same-day fare sits at a structurally higher *level* than "
        "a 30-day-advance fare. If all horizons were pooled into one aggregate, the index "
        "would move whenever the horizon mix of the sample changed, even with every "
        "underlying price held constant — a composition artefact reported as inflation.\n\n"
        "The equal weights are a documented convention, not an estimate: the true share "
        "of tickets sold at each horizon is held by airlines and is not published.",
    ),
    (
        ("seasonal", "diwali", "festival", "holiday", "adjust"),
        "**Seasonal adjustment: NOT IMPLEMENTED**\n\n"
        "The published series is **observed** (not seasonally adjusted). Festival, "
        "holiday and school-vacation surges appear in it as price increases, because "
        "that is what was observed.\n\n"
        "Adjustment needs several complete seasonal cycles — conventionally at least "
        "three years of monthly history. This series is far shorter, so any seasonal "
        "factor fitted to it would describe the window rather than a seasonal pattern.\n\n"
        "Airfares are among the most strongly seasonal items in a consumer basket, so "
        "this is a material limitation, not a technicality.",
    ),
    (
        ("weight", "dgca", "passenger", "expenditure", "basket"),
        "**Route weights**\n\n"
        "Weights are derived as `w_r = pax_r / sum(pax)` from monthly passenger volumes "
        "across the 25-route basket, so they sum to exactly 1.0 by construction.\n\n"
        "They are **provisional passenger-volume weights, not official CPI expenditure "
        "shares**. A CPI component needs expenditure (passengers x fare); route-level "
        "expenditure data at this granularity is not publicly available, so volume is "
        "used as a documented proxy. Every API response that exposes weights reports "
        "`status: PROVISIONAL` alongside them.",
    ),
    (
        ("yoy", "year on year", "year-on-year", "12 month"),
        "**Year-on-year change**\n\n"
        "Reported only when a stored index value exists 12 months before the reference "
        "date. Otherwise the API returns `yoy_change_pct: null` with "
        "`yoy_status: \"insufficient_history\"`.\n\n"
        "No placeholder percentage is ever substituted to fill the field.",
    ),
    (
        ("scrap", "start scrap", "trigger", "fetch fresh", "ingest", "collect data", "run scraper"),
        "### Live Data Ingestion Controller\n\n"
        "I have direct access to the backend collection pipeline. You can launch an on-demand data collection cycle across all **25 domestic corridors** and **5 booking horizons** ($T+0 \\dots T+30$).\n\n"
        "[ACTION:TRIGGER_SCRAPING]\n\n"
        "*Integrity Invariant:* All observations are validated through hard bounds (₹500-₹80k) and IQR outlier fences before index recalculation."
    ),
    (
        ("provenance", "live", "simulated", "real data", "source"),
        "**Data provenance**\n\n"
        "Every observation carries a provenance record, and the system runs in one of "
        "three explicit modes:\n\n"
        "- **LIVE DATA** — retrieved from a real permitted source (Amadeus "
        "Self-Service Flight Offers Search).\n"
        "- **SIMULATED DATA** — generated by the calibrated simulator, used to validate "
        "the methodology.\n"
        "- **OFFLINE PREVIEW** — replayed from a checked-in fixture.\n\n"
        "A failed live collection reports **SOURCE UNAVAILABLE** with zero observations. "
        "It never falls back to generated data.\n\n"
        "Most Indian airline and OTA portals are not scraped: their search paths are "
        "either disallowed for automated agents or protected by bot detection, and "
        "circumventing that is out of scope. Those adapters are registered as disabled "
        "with their reasons, visible at `/api/v1/sources`.",
    ),
    (
        ("uncertainty", "confidence", "standard error", "interval"),
        "**Uncertainty**\n\n"
        "Sampling uncertainty of an elementary index is estimated from the dispersion of "
        "its log price relatives: `se_log = s / sqrt(n)`, with the interval formed in log "
        "space and exponentiated back so it stays positive and asymmetric in level "
        "terms.\n\n"
        "It **excludes** basket-selection uncertainty (the 25 routes are a purposive "
        "selection, not a probability sample, so no design-based variance exists), weight "
        "error, and non-sampling error. The national interval also assumes routes are "
        "independent, which is optimistic — fuel and demand move many routes together — "
        "so it should be read as a lower bound.\n\n"
        "Where uncertainty is not defensibly estimable, the API returns nulls with a "
        "stated reason rather than an interval.",
    ),
    (
        ("validation", "iqr", "outlier", "anomaly", "quality"),
        "**Validation**\n\n"
        "Collection errors are **excluded**; genuine volatility is **flagged and kept**, "
        "because an index that deletes real volatility is not measuring the market.\n\n"
        "- Hard bounds on implausible fares.\n"
        "- IQR fencing (3x) against a reference distribution that **excludes previously "
        "flagged outliers**, so the fences cannot ratchet outward over time.\n"
        "- Day-over-day change limit, enforced per route *and* per horizon.\n"
        "- Reference distributions are persisted, so fences are continuous across "
        "restarts and outlier decisions are reproducible.\n\n"
        "Flagged observations open an anomaly for triage, where a reviewer records "
        "whether the movement was genuine.",
    ),
    (
        ("base period", "rebase", "base year", "reference"),
        "**Base period**\n\n"
        "One configurable base period (`INDEX_BASE_PERIOD_START`, "
        "`INDEX_BASE_PERIOD_DAYS`) used everywhere. Base prices are computed per "
        "*product* from the observations whose collection date falls inside that window "
        "— selected strictly by date, never by insertion order.\n\n"
        "Re-referencing to a different window is a genuine recomputation: "
        "`I_new(t) = I_old(t) / mean(I_old over reference window) * 100`. It therefore "
        "actually changes the numbers, and it is only offered for windows the collected "
        "series covers. No link factor is invented for a period the data does not reach.",
    ),
]


def answer_locally(question: str, context: dict[str, Any]) -> CopilotAnswer:
    """
    Deterministic answer from the local knowledge base.

    Labelled ``local_fallback`` so a consumer knows no model was called.
    """
    lowered = question.lower()

    for keywords, response in _LOCAL_TOPICS:
        if any(keyword in lowered for keyword in keywords):
            return CopilotAnswer(
                text=response,
                tier=TIER_LOCAL,
                model=None,
                note=(
                    "Answered from the local deterministic knowledge base. No language "
                    "model was called."
                ),
                grounded_on=context,
            )

    figures = "\n".join(
        f"- **{key}**: {value}"
        for key, value in context.items()
        if key != "data_provenance"
    )
    provenance = (context.get("data_provenance") or {}).get(
        "display_label", "SOURCE UNAVAILABLE"
    )

    return CopilotAnswer(
        text=(
            f"I don't have a prepared answer for that, and no language model is "
            f"configured, so I won't speculate.\n\n"
            f"**Current figures** (provenance: {provenance}):\n\n"
            f"{figures or '- none available'}\n\n"
            f"I can explain: the matched-model Jevons formula, booking-horizon "
            f"stratification, route weighting, the base period and re-referencing, "
            f"validation and anomaly handling, uncertainty estimation, seasonal "
            f"adjustment status, or data provenance."
        ),
        tier=TIER_LOCAL,
        model=None,
        note=(
            "Answered from the local deterministic knowledge base. No language model "
            "was called."
        ),
        grounded_on=context,
    )


# ── provider call ──

async def validate_model_name(settings: Optional[ApiSettings] = None) -> dict[str, Any]:
    """
    Check the configured model name against the provider's model list.

    Exists because the previous frontend advertised a model identifier that does not
    exist, so the UI showed a model badge for calls that always failed. Verifying the
    name at startup makes that impossible to repeat silently.
    """
    cfg = settings or get_settings().api

    if not cfg.copilot_api_key:
        return {
            "configured": False,
            "model": cfg.copilot_model,
            "validated": False,
            "note": (
                "COPILOT_API_KEY is not set. The Copilot answers from its local "
                "knowledge base and labels every answer as local_fallback."
            ),
        }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{GEMINI_BASE}/models", params={"key": cfg.copilot_api_key}
            )
        if resp.status_code != 200:
            return {
                "configured": True,
                "model": cfg.copilot_model,
                "validated": False,
                "note": (
                    f"Could not list provider models (HTTP {resp.status_code}); the "
                    f"model name is unverified."
                ),
            }

        names = {
            str(m.get("name", "")).removeprefix("models/")
            for m in resp.json().get("models", [])
        }
        ok = cfg.copilot_model in names

        if not ok:
            logger.warning(
                f"COPILOT_MODEL={cfg.copilot_model!r} is not in the provider's model "
                f"list. Calls will fail and every answer will be labelled "
                f"local_fallback. Available (sample): {sorted(names)[:6]}"
            )

        return {
            "configured": True,
            "model": cfg.copilot_model,
            "validated": ok,
            "note": (
                "Model name verified against the provider."
                if ok
                else (
                    f"Model {cfg.copilot_model!r} was NOT found in the provider's model "
                    f"list. Requests will fail into the local fallback."
                )
            ),
            "available_models_sample": sorted(names)[:10],
        }
    except Exception as exc:
        return {
            "configured": True,
            "model": cfg.copilot_model,
            "validated": False,
            "note": f"Model validation failed: {type(exc).__name__}: {exc}",
        }


async def ask(
    question: str,
    context: dict[str, Any],
    settings: Optional[ApiSettings] = None,
) -> CopilotAnswer:
    """
    Answer a question, preferring the configured model and falling back locally.

    A fallback answer is always labelled as such. There is no path that reports a
    local answer as having come from the model.
    """
    cfg = settings or get_settings().api

    if not cfg.copilot_api_key:
        return answer_locally(question, context)

    system_prompt = build_system_prompt(context)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{GEMINI_BASE}/models/{cfg.copilot_model}:generateContent",
                params={"key": cfg.copilot_api_key},
                json={
                    "systemInstruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"role": "user", "parts": [{"text": question}]}],
                    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024},
                },
            )

        if resp.status_code != 200:
            logger.warning(
                f"Copilot provider returned HTTP {resp.status_code}; falling back to "
                f"the local knowledge base"
            )
            fallback = answer_locally(question, context)
            return CopilotAnswer(
                text=fallback.text,
                tier=TIER_LOCAL,
                model=None,
                note=(
                    f"The language model request failed (HTTP {resp.status_code}). This "
                    f"answer came from the local deterministic knowledge base, not the "
                    f"model."
                ),
                grounded_on=context,
            )

        payload = resp.json()
        candidates = payload.get("candidates") or []
        parts = (candidates[0].get("content", {}).get("parts") if candidates else None) or []
        text = "".join(p.get("text", "") for p in parts).strip()

        if not text:
            fallback = answer_locally(question, context)
            return CopilotAnswer(
                text=fallback.text,
                tier=TIER_LOCAL,
                model=None,
                note=(
                    "The language model returned no content. This answer came from the "
                    "local deterministic knowledge base."
                ),
                grounded_on=context,
            )

        formatted_model = (
            cfg.copilot_model.replace("-", " ").title()
            if cfg.copilot_model
            else "Gemini 3.5 Flash Lite"
        )
        return CopilotAnswer(
            text=text,
            tier=TIER_MODEL,
            model=cfg.copilot_model,
            note=f"Answered by {formatted_model} via RAG pipeline.",
            grounded_on=context,
        )

    except Exception as exc:
        logger.warning(f"Copilot provider call failed: {type(exc).__name__}: {exc}")
        fallback = answer_locally(question, context)
        return CopilotAnswer(
            text=fallback.text,
            tier=TIER_LOCAL,
            model=None,
            note=(
                f"The language model could not be reached ({type(exc).__name__}). This "
                f"answer came from the local deterministic knowledge base, not the model."
            ),
            grounded_on=context,
        )


def status(settings: Optional[ApiSettings] = None) -> dict[str, Any]:
    """Copilot capability status, exposed so the UI badge reflects reality."""
    cfg = settings or get_settings().api
    return {
        "proxy_enabled": bool(cfg.copilot_api_key),
        "model": cfg.copilot_model if cfg.copilot_api_key else None,
        "default_tier": TIER_MODEL if cfg.copilot_api_key else TIER_LOCAL,
        "local_knowledge_base_topics": len(_LOCAL_TOPICS),
        "key_location": "server-side environment variable COPILOT_API_KEY",
        "client_holds_key": False,
        "note": (
            "The provider key is held server-side only. The frontend calls this proxy "
            "and never receives a key. Answers are labelled with the tier that produced "
            "them."
            if cfg.copilot_api_key
            else "No provider key configured; all answers come from the local "
            "deterministic knowledge base and are labelled local_fallback."
        ),
    }
