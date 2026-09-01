"""
SIH26056 — Normalization.

Converts heterogeneous source payloads into canonical :class:`FareObservation`
values: INR monetary amounts, canonical cabin labels, canonical airline codes, and
a consistent stop count.

Currency policy
---------------
Sources are asked for INR wherever they support a currency parameter, so in normal
operation no conversion happens and the observation records
``source_currency == "INR"``.

When a source returns a non-INR amount, conversion needs a rate, and a rate that is
not sourced is a fabricated number. So:

* If ``FX_RATES_INR`` supplies an explicit, operator-configured rate, it is applied
  and recorded in provenance notes for audit.
* Otherwise :class:`CurrencyNotSupported` is raised and the observation is dropped
  with a recorded reason. Inventing a plausible exchange rate to keep the row would
  put an unverifiable number into the index.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Iterable, Optional

from loguru import logger

from scraper.base import (
    CABIN_BUSINESS,
    CABIN_ECONOMY,
    CABIN_FIRST,
    CABIN_PREMIUM_ECONOMY,
    FareObservation,
    VALID_CABINS,
)


class NormalizationError(ValueError):
    """A payload could not be turned into a valid observation."""


class CurrencyNotSupported(NormalizationError):
    """A non-INR amount was received with no operator-configured conversion rate."""


# Cabin label variants seen across sources, mapped to canonical labels.
_CABIN_ALIASES: dict[str, str] = {
    "ECONOMY": CABIN_ECONOMY,
    "ECO": CABIN_ECONOMY,
    "E": CABIN_ECONOMY,
    "COACH": CABIN_ECONOMY,
    "PREMIUM_ECONOMY": CABIN_PREMIUM_ECONOMY,
    "PREMIUMECONOMY": CABIN_PREMIUM_ECONOMY,
    "PREMIUM ECONOMY": CABIN_PREMIUM_ECONOMY,
    "W": CABIN_PREMIUM_ECONOMY,
    "BUSINESS": CABIN_BUSINESS,
    "BUS": CABIN_BUSINESS,
    "C": CABIN_BUSINESS,
    "FIRST": CABIN_FIRST,
    "F": CABIN_FIRST,
}

# Marketing carrier codes for Indian domestic operators, used to fill airline_name
# when a source returns only a code. Purely cosmetic: absence never blocks an
# observation, and the code is what the index matches on.
AIRLINE_NAMES: dict[str, str] = {
    "6E": "IndiGo",
    "AI": "Air India",
    "IX": "Air India Express",
    "SG": "SpiceJet",
    "UK": "Vistara",
    "QP": "Akasa Air",
    "I5": "AIX Connect",
    "9I": "Alliance Air",
    "S5": "Star Air",
    "QO": "IndiaOne Air",
}


def _fx_rates() -> dict[str, float]:
    """
    Operator-configured FX rates, as ``FX_RATES_INR="USD=83.2,EUR=90.1"``.

    Empty by default: there is no built-in rate table, because a hardcoded rate
    would silently go stale and quietly distort every converted fare.
    """
    raw = os.getenv("FX_RATES_INR", "").strip()
    rates: dict[str, float] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part or "=" not in part:
            continue
        code, _, value = part.partition("=")
        try:
            rates[code.strip().upper()] = float(value)
        except ValueError:
            logger.warning(f"FX_RATES_INR: ignoring unparseable entry {part!r}")
    return rates


def normalize_cabin(raw: Any, default: str = CABIN_ECONOMY) -> str:
    """Map a source cabin label to a canonical one."""
    if raw is None:
        return default
    key = str(raw).strip().upper().replace("-", "_")
    if key in VALID_CABINS:
        return key
    mapped = _CABIN_ALIASES.get(key)
    if mapped:
        return mapped
    logger.debug(f"Unrecognised cabin label {raw!r}; treating as {default}")
    return default


def normalize_airline_code(raw: Any) -> str:
    code = str(raw or "").strip().upper()
    if not code:
        raise NormalizationError("airline code is missing")
    return code


def airline_name_for(code: str, fallback: Optional[str] = None) -> Optional[str]:
    return AIRLINE_NAMES.get(code) or fallback


def normalize_flight_number(airline_code: str, raw: Any) -> Optional[str]:
    """Render a flight number as ``6E-2134``, tolerating source formatting."""
    if raw is None:
        return None
    text = str(raw).strip().upper().replace(" ", "")
    if not text:
        return None
    if text.startswith(airline_code):
        digits = text[len(airline_code):].lstrip("-")
        return f"{airline_code}-{digits}" if digits else text
    if "-" in text:
        return text
    return f"{airline_code}-{text}"


def to_inr(
    amount: float,
    currency: str,
    rates: Optional[dict[str, float]] = None,
) -> tuple[float, Optional[float]]:
    """
    Convert ``amount`` to INR.

    Returns ``(inr_amount, rate_applied)``; ``rate_applied`` is None when the input
    was already INR. Raises :class:`CurrencyNotSupported` when conversion would
    require a rate that has not been configured.
    """
    code = (currency or "INR").strip().upper()
    if code == "INR":
        return float(amount), None

    table = rates if rates is not None else _fx_rates()
    rate = table.get(code)
    if rate is None or rate <= 0:
        raise CurrencyNotSupported(
            f"Fare quoted in {code} but no INR conversion rate is configured. Set "
            f"FX_RATES_INR (e.g. 'FX_RATES_INR={code}=<rate>') or request INR from the "
            f"source. The observation is dropped rather than converted at a guessed rate."
        )
    return float(amount) * rate, rate


def parse_iso_date(raw: Any) -> date:
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    if isinstance(raw, datetime):
        return raw.date()
    text = str(raw or "").strip()
    if not text:
        raise NormalizationError("departure date is missing")
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise NormalizationError(f"unparseable departure date {raw!r}") from exc


def normalize_stops(raw: Any, segments: Optional[int] = None) -> int:
    """
    Stop count. Prefers an explicit value; otherwise derives from segment count
    (``stops = segments - 1``).
    """
    if raw is not None:
        try:
            value = int(raw)
            if value >= 0:
                return value
        except (TypeError, ValueError):
            pass
    if segments is not None and segments >= 1:
        return int(segments) - 1
    return 0


def normalize_bool(raw: Any) -> Optional[bool]:
    """Tri-state: None means the source did not disclose it, which is not False."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().lower()
    if text in {"true", "yes", "y", "1", "refundable"}:
        return True
    if text in {"false", "no", "n", "0", "non-refundable", "nonrefundable"}:
        return False
    return None


def normalize_baggage_kg(raw: Any) -> Optional[int]:
    """
    Checked baggage allowance in kg.

    A piece-based allowance ("1PC") is not convertible to kg without the carrier's
    per-piece weight, so it returns None rather than an assumed 15 or 23 kg. None
    participates in the product key as ``BAGUNKNOWN``, which still matches
    like-for-like across periods.
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        value = int(raw)
        return value if value >= 0 else None
    text = str(raw).strip().upper()
    if not text:
        return None
    if text.endswith("KG"):
        text = text[:-2].strip()
    try:
        return int(float(text))
    except ValueError:
        return None


@dataclass
class NormalizationOutcome:
    """Result of normalizing a batch, including why anything was dropped."""

    observations: list[FareObservation]
    dropped: list[dict[str, Any]]

    @property
    def dropped_count(self) -> int:
        return len(self.dropped)

    def summary(self) -> dict[str, Any]:
        reasons: dict[str, int] = {}
        for d in self.dropped:
            reasons[d.get("reason_type", "unknown")] = (
                reasons.get(d.get("reason_type", "unknown"), 0) + 1
            )
        return {
            "normalized": len(self.observations),
            "dropped": self.dropped_count,
            "drop_reasons": reasons,
        }


def collect_normalized(
    builders: Iterable[tuple[dict[str, Any], Any]],
) -> NormalizationOutcome:
    """
    Run a sequence of ``(context, callable)`` normalizations, recording failures.

    A malformed offer must not abort the whole batch, but it must not vanish either:
    every drop is recorded with its reason so the collection run's yield is
    explainable.
    """
    observations: list[FareObservation] = []
    dropped: list[dict[str, Any]] = []

    for context, build in builders:
        try:
            obs = build()
            if obs is not None:
                observations.append(obs)
        except CurrencyNotSupported as exc:
            dropped.append({**context, "reason_type": "currency_unsupported", "reason": str(exc)})
        except NormalizationError as exc:
            dropped.append({**context, "reason_type": "normalization_error", "reason": str(exc)})
        except ValueError as exc:
            # FareObservation's own invariants (positive fare, valid cabin, ...).
            dropped.append({**context, "reason_type": "invalid_observation", "reason": str(exc)})

    if dropped:
        logger.info(
            f"Normalization dropped {len(dropped)} offer(s); "
            f"kept {len(observations)}"
        )
    return NormalizationOutcome(observations=observations, dropped=dropped)
