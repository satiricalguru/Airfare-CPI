/**
 * SIH26056 — Display formatting.
 *
 * Every formatter here returns the {@link NOT_AVAILABLE} marker for a null or
 * non-finite input. That is the whole point: a formatter that silently renders `0`, or
 * a plausible default, for missing data produces a screen where an absent measurement
 * is indistinguishable from a real one.
 *
 * Nothing in this module invents a value.
 */

import { NOT_AVAILABLE } from "./api";

/** Index level, e.g. `103.44`. */
export function fmtIndex(value, places = 2) {
  if (value == null || !Number.isFinite(Number(value))) return NOT_AVAILABLE;
  return Number(value).toFixed(places);
}

/**
 * Signed percentage change, e.g. `+1.88%`.
 *
 * When `status` is supplied and the value is null, the status is turned into a short
 * human reason so the UI can show *why* rather than a bare dash.
 */
export function fmtChange(value, status = null, places = 2) {
  if (value == null || !Number.isFinite(Number(value))) {
    return NOT_AVAILABLE;
  }
  const n = Number(value);
  return `${n > 0 ? "+" : ""}${n.toFixed(places)}%`;
}

/** Human explanation for a null change, from the backend's status string. */
export function changeReason(status) {
  switch (status) {
    case "insufficient_history":
      return "The collected series is too short for this comparison.";
    case "invalid_comparison_base":
      return "The comparison period's index is not usable.";
    case "not_computable":
      return "No index was computable for the comparison period.";
    case "available":
      return null;
    default:
      return status ? `Not available (${status}).` : "Not available.";
  }
}

/** Integer with thousands separators. */
export function fmtCount(value) {
  if (value == null || !Number.isFinite(Number(value))) return NOT_AVAILABLE;
  return Number(value).toLocaleString("en-IN");
}

/** Rupee amount, e.g. `₹5,432`. */
export function fmtInr(value, places = 0) {
  if (value == null || !Number.isFinite(Number(value))) return NOT_AVAILABLE;
  return `₹${Number(value).toLocaleString("en-IN", {
    minimumFractionDigits: places,
    maximumFractionDigits: places,
  })}`;
}

/** Fraction rendered as a percentage, e.g. `0.379` -> `37.9%`. */
export function fmtPctFromFraction(value, places = 1) {
  if (value == null || !Number.isFinite(Number(value))) return NOT_AVAILABLE;
  return `${(Number(value) * 100).toFixed(places)}%`;
}

/** Percentage already on a 0-100 scale. */
export function fmtPct(value, places = 1) {
  if (value == null || !Number.isFinite(Number(value))) return NOT_AVAILABLE;
  return `${Number(value).toFixed(places)}%`;
}

/** Large passenger volumes, e.g. `1.20M`. */
export function fmtPax(value) {
  if (value == null || !Number.isFinite(Number(value))) return NOT_AVAILABLE;
  const n = Number(value);
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

/** ISO date as `30 Aug 2026`. */
export function fmtDate(iso) {
  if (!iso) return NOT_AVAILABLE;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return NOT_AVAILABLE;
  return d.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

/** ISO timestamp as `30 Aug 2026, 18:42`. */
export function fmtDateTime(iso) {
  if (!iso) return NOT_AVAILABLE;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return NOT_AVAILABLE;
  return `${fmtDate(iso)}, ${d.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  })}`;
}

/** Short axis label, e.g. `30 Aug`. */
export function fmtShortDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

/**
 * A confidence interval, or a stated reason for its absence.
 *
 * Never renders an interval that was not estimated.
 */
export function fmtInterval(low, high, places = 2) {
  if (low == null || high == null) return NOT_AVAILABLE;
  if (!Number.isFinite(Number(low)) || !Number.isFinite(Number(high))) {
    return NOT_AVAILABLE;
  }
  return `${Number(low).toFixed(places)} – ${Number(high).toFixed(places)}`;
}

/** Relative time, e.g. `4 min ago`. */
export function fmtRelative(iso) {
  if (!iso) return NOT_AVAILABLE;
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return NOT_AVAILABLE;
  const seconds = Math.round((Date.now() - then) / 1000);
  if (seconds < 10) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}
