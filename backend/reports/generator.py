"""
SIH26056 — Research bulletin generator.

Produces a research output. It is NOT and must never resemble an official government
statistical release.

What was removed and why
------------------------
The previous generator emitted a document headed "Government of India / Ministry of
Statistics and Programme Implementation" with a Release ID and "Issued by: Price
Statistics Division, MoSPI, New Delhi", populated entirely with synthetic figures
including a hardcoded ``+2.84% (Provisional)`` inflation rate. That is fabricated
official statistics attributed to the sponsoring ministry — the single highest-risk
item in the audit (C2).

All of it is gone: no government header, no ministry attribution, no named officials,
no Release ID presented as an official identifier, and no hardcoded figure anywhere. A
value that is unavailable is printed as unavailable, with the reason.

What every bulletin must state, and does
----------------------------------------
data source, data provenance, collection period, base period, methodology,
limitations, sample size, revision status.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from provenance import (
    PROVENANCE_LABELS,
    SOURCE_UNAVAILABLE_LABEL,
    SourceType,
)


PROTOTYPE_TITLE = "Prototype / Research Output"

NOT_OFFICIAL_STATEMENT = (
    "This document is a research output produced by a student prototype built for "
    "Smart India Hackathon problem statement SIH26056. It is NOT an official "
    "statistical release. It is not issued by, endorsed by, or affiliated with the "
    "Ministry of Statistics and Programme Implementation, the National Statistical "
    "Office, or the Government of India. No official branding or attribution is used, "
    "because this project holds no authorization to use any."
)


@dataclass
class ResearchBulletin:
    """Everything a bulletin needs. No field has a fabricated default."""

    report_id: str
    generated_at: datetime
    reference_date: date
    headline_index: float
    base_period: str
    source_type: str
    provenance_label: str
    sample_size: int
    methodology_version: str
    validation_rules_version: str
    collector_version: str

    mom_change_pct: Optional[float] = None
    mom_status: str = "insufficient_history"
    yoy_change_pct: Optional[float] = None
    yoy_status: str = "insufficient_history"

    matched_products: int = 0
    routes_included: int = 0
    routes_in_basket: int = 0
    coverage_weight: float = 0.0
    renormalization_applied: bool = False
    is_publishable: bool = True
    suppression_reason: Optional[str] = None

    standard_error: Optional[float] = None
    confidence_interval_low: Optional[float] = None
    confidence_interval_high: Optional[float] = None
    uncertainty_basis: Optional[str] = None

    seasonal_adjustment: str = "NOT IMPLEMENTED"
    weighting_method: str = "passenger_volume"
    weighting_status: str = "PROVISIONAL"
    weight_basket_version: str = "unknown"

    collection_period_start: Optional[date] = None
    collection_period_end: Optional[date] = None
    collection_run_count: int = 0
    data_quality_pct: Optional[float] = None

    top_increasing_routes: list[dict] = field(default_factory=list)
    top_decreasing_routes: list[dict] = field(default_factory=list)
    horizon_summary: list[dict] = field(default_factory=list)
    missing_routes: list[dict] = field(default_factory=list)

    anomalies_open: int = 0
    revision_count: int = 0

    # ── derived presentation values ──

    @property
    def is_real_data(self) -> bool:
        return self.source_type == SourceType.LIVE.value

    @property
    def collection_period_label(self) -> str:
        if not self.collection_period_start or not self.collection_period_end:
            return "Not available (no collection runs recorded)"
        return (
            f"{self.collection_period_start.isoformat()} to "
            f"{self.collection_period_end.isoformat()} "
            f"({self.collection_run_count} collection run(s))"
        )

    def mom_display(self) -> str:
        return _change_display(self.mom_change_pct, self.mom_status, "month-on-month")

    def yoy_display(self) -> str:
        return _change_display(self.yoy_change_pct, self.yoy_status, "year-on-year")

    def uncertainty_display(self) -> str:
        if self.standard_error is None:
            return (
                f"Not available. {self.uncertainty_basis or 'No basis recorded.'}"
            )
        return (
            f"± {self.standard_error:.4f} (standard error); "
            f"95% interval {self.confidence_interval_low:.2f} to "
            f"{self.confidence_interval_high:.2f}"
        )

    def to_dict(self) -> dict[str, Any]:
        """JSON form, matching the HTML in what it discloses."""
        return {
            "document_type": PROTOTYPE_TITLE,
            "is_official_statistic": False,
            "disclaimer": NOT_OFFICIAL_STATEMENT,
            "report_id": self.report_id,
            "report_id_note": (
                "Internal identifier for this prototype output. Not an official "
                "government release identifier."
            ),
            "generated_at": self.generated_at.isoformat(),
            "reference_date": self.reference_date.isoformat(),
            "headline_index": round(self.headline_index, 4),
            "is_publishable": self.is_publishable,
            "suppression_reason": self.suppression_reason,
            "data_source": {
                "provenance_label": self.provenance_label,
                "source_type": self.source_type,
                "is_collected_data": self.is_real_data,
                "note": (
                    "Figures derive from observations collected from a real permitted "
                    "source."
                    if self.is_real_data
                    else (
                        "Figures derive from generated or replayed observations. They "
                        "demonstrate that the index pipeline computes correctly and carry "
                        "NO inferential validity about actual Indian airfare inflation."
                    )
                ),
            },
            "collection_period": self.collection_period_label,
            "base_period": self.base_period,
            "changes": {
                "mom_change_pct": self.mom_change_pct,
                "mom_status": self.mom_status,
                "yoy_change_pct": self.yoy_change_pct,
                "yoy_status": self.yoy_status,
            },
            "sample": {
                "sample_size": self.sample_size,
                "matched_products": self.matched_products,
                "routes_included": self.routes_included,
                "routes_in_basket": self.routes_in_basket,
                "coverage_weight": round(self.coverage_weight, 6),
                "renormalization_applied": self.renormalization_applied,
                "data_quality_pct": self.data_quality_pct,
                "missing_routes": self.missing_routes,
            },
            "uncertainty": {
                "standard_error": self.standard_error,
                "confidence_interval_low": self.confidence_interval_low,
                "confidence_interval_high": self.confidence_interval_high,
                "basis": self.uncertainty_basis,
                "is_estimable": self.standard_error is not None,
            },
            "methodology": {
                "elementary_index": "matched-model Jevons (geometric mean of price relatives)",
                "upper_level": "Young-type weighted mean over route indices",
                "booking_horizons": "stratified, combined with fixed equal weights",
                "weighting_method": self.weighting_method,
                "weighting_status": self.weighting_status,
                "weight_basket_version": self.weight_basket_version,
                "seasonal_adjustment": self.seasonal_adjustment,
                "methodology_version": self.methodology_version,
                "validation_rules_version": self.validation_rules_version,
                "collector_version": self.collector_version,
            },
            "limitations": self.limitations(),
            "revision_status": {
                "revision_count": self.revision_count,
                "open_anomalies": self.anomalies_open,
                "status": "provisional",
                "note": (
                    "All figures are provisional. Every publication and recomputation is "
                    "recorded in the revision log."
                ),
            },
            "top_increasing_routes": self.top_increasing_routes,
            "top_decreasing_routes": self.top_decreasing_routes,
            "horizon_summary": self.horizon_summary,
        }

    def limitations(self) -> list[str]:
        """Stated on every bulletin, in both output formats."""
        items = [
            f"Seasonal adjustment is {self.seasonal_adjustment}. The series is observed "
            f"(not seasonally adjusted), so festival, holiday and vacation effects appear "
            f"in it and must not be read as underlying inflation.",
            f"Route weights are {self.weighting_status.lower()} "
            f"{self.weighting_method.replace('_', ' ')} shares, NOT official CPI "
            f"expenditure weights. A CPI component requires expenditure "
            f"(passengers x fare), which is not available at this granularity.",
            "The route basket is a purposive selection of city pairs, not a probability "
            "sample of the domestic market, so no design-based variance can be computed "
            "for its coverage.",
            "Uncertainty covers sampling error only and assumes routes are independent. "
            "Airfares are plausibly correlated across routes through fuel and demand, so "
            "the stated interval is a lower bound.",
            "Most airline and OTA portals are not collected: their search paths are "
            "either disallowed for automated agents or protected by bot detection. Only "
            "sources that can be used as intended are collected.",
        ]

        if not self.is_real_data:
            items.insert(
                0,
                "THE UNDERLYING DATA IS NOT COLLECTED FROM A LIVE SOURCE. Every figure "
                "in this document derives from generated or replayed observations and "
                "describes the generator, not the market.",
            )

        if self.renormalization_applied:
            items.append(
                f"Basket coverage was {self.coverage_weight:.1%}. Weights of present "
                f"routes were renormalized to 1.0, which imputes the collected routes' "
                f"average movement onto the {len(self.missing_routes)} absent route(s)."
            )

        if not self.is_publishable:
            items.insert(
                0,
                f"THIS FIGURE IS MARKED NOT PUBLISHABLE. {self.suppression_reason or ''}".strip(),
            )

        return items


def _change_display(value: Optional[float], status: str, label: str) -> str:
    """
    Render a period change, or state plainly that it is unavailable.

    Never substitutes 0.0, which would read as "no inflation" rather than "not
    computable", and never substitutes a placeholder percentage.
    """
    if value is None:
        if status == "insufficient_history":
            return (
                f"Not available — the collected series is too short for a {label} "
                f"comparison"
            )
        if status == "invalid_comparison_base":
            return "Not available — the comparison period's index is not usable"
        if status == "not_computable":
            return "Not available — no index was computable for the comparison period"
        return f"Not available ({status})"
    return f"{value:+.2f}%"


class ResearchReportGenerator:
    """Renders a :class:`ResearchBulletin` as HTML."""

    @staticmethod
    def render_html(bulletin: ResearchBulletin) -> str:
        e = html.escape
        is_real = bulletin.is_real_data

        provenance_banner_class = "banner-live" if is_real else "banner-synthetic"
        provenance_headline = (
            bulletin.provenance_label
            if bulletin.provenance_label
            else SOURCE_UNAVAILABLE_LABEL
        )

        limitations_html = "".join(
            f"<li>{e(item)}</li>" for item in bulletin.limitations()
        )

        routes_up_html = "".join(
            f"<tr><td>{e(str(r.get('route_code', '—')))}</td>"
            f"<td>{_pct(r.get('weight'))}</td>"
            f"<td>{_num(r.get('index_100'))}</td>"
            f"<td>{_num(r.get('contribution_pct'))}%</td>"
            f"<td>{r.get('matched_products', '—')}</td></tr>"
            for r in bulletin.top_increasing_routes
        ) or "<tr><td colspan='5'>No route contributions available.</td></tr>"

        routes_down_html = "".join(
            f"<tr><td>{e(str(r.get('route_code', '—')))}</td>"
            f"<td>{_pct(r.get('weight'))}</td>"
            f"<td>{_num(r.get('index_100'))}</td>"
            f"<td>{_num(r.get('contribution_pct'))}%</td>"
            f"<td>{r.get('matched_products', '—')}</td></tr>"
            for r in bulletin.top_decreasing_routes
        ) or "<tr><td colspan='5'>No route contributions available.</td></tr>"

        horizon_html = "".join(
            f"<tr><td>{e(str(h.get('label', '—')))}</td>"
            f"<td>{_num(h.get('mean_index'))}</td>"
            f"<td>{h.get('routes_with_index', '—')}</td>"
            f"<td>{h.get('matched_products', '—')}</td>"
            f"<td>{_num(h.get('policy_weight'), 3)}</td></tr>"
            for h in bulletin.horizon_summary
        ) or (
            "<tr><td colspan='5'>No horizon indices available for this reference "
            "date.</td></tr>"
        )

        missing_html = (
            "".join(
                f"<tr><td>{e(str(m.get('route_code', '—')))}</td>"
                f"<td>{_pct(m.get('weight'))}</td>"
                f"<td>{e(str(m.get('reason', '—')))}</td>"
                f"<td>none</td></tr>"
                for m in bulletin.missing_routes[:15]
            )
            or "<tr><td colspan='4'>No routes were missing from this period.</td></tr>"
        )

        suppression_html = (
            f"""
  <div class="suppression">
    <strong>FIGURE MARKED NOT PUBLISHABLE.</strong>
    <p>{e(bulletin.suppression_reason or '')}</p>
  </div>"""
            if not bulletin.is_publishable
            else ""
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(PROTOTYPE_TITLE)} — Experimental Airfare Price Index — {bulletin.reference_date.isoformat()}</title>
<style>
  body {{ font-family: Georgia, 'Times New Roman', serif; margin: 0; padding: 32px;
         color: #16191d; line-height: 1.6; max-width: 960px; margin: 0 auto;
         background: #fdfdfb; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  h2 {{ font-size: 15px; text-transform: uppercase; letter-spacing: .06em;
        border-bottom: 1px solid #c9cdd2; padding-bottom: 6px; margin-top: 34px; }}
  .doc-type {{ display: inline-block; background: #16191d; color: #fff;
               font-family: system-ui, sans-serif; font-size: 11px; font-weight: 700;
               letter-spacing: .12em; text-transform: uppercase; padding: 5px 11px;
               margin-bottom: 14px; }}
  .banner {{ border: 2px solid; padding: 14px 18px; margin: 18px 0; font-size: 13px;
             font-family: system-ui, sans-serif; }}
  .banner-synthetic {{ border-color: #b3261e; background: #fdf3f2; }}
  .banner-live {{ border-color: #1b6b3a; background: #f2f9f4; }}
  .banner-title {{ font-weight: 700; font-size: 14px; letter-spacing: .06em;
                   text-transform: uppercase; margin-bottom: 6px; }}
  .banner-synthetic .banner-title {{ color: #b3261e; }}
  .banner-live .banner-title {{ color: #1b6b3a; }}
  .disclaimer {{ border: 1px solid #c9cdd2; background: #f6f7f8; padding: 14px 18px;
                 font-size: 12px; font-family: system-ui, sans-serif; margin: 18px 0; }}
  .headline {{ border: 1px solid #16191d; padding: 20px; margin: 22px 0; }}
  .headline-value {{ font-size: 40px; font-weight: 700; line-height: 1; }}
  .headline-label {{ font-family: system-ui, sans-serif; font-size: 11px;
                     text-transform: uppercase; letter-spacing: .1em; color: #5b6169; }}
  .headline-changes {{ margin-top: 12px; font-size: 13px; }}
  .suppression {{ border: 2px solid #b3261e; background: #fdf3f2; padding: 14px 18px;
                  margin: 18px 0; font-family: system-ui, sans-serif; font-size: 13px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 12px;
           font-family: system-ui, sans-serif; }}
  th, td {{ border: 1px solid #c9cdd2; padding: 7px 10px; text-align: left; }}
  th {{ background: #eceef0; font-weight: 600; }}
  dl {{ font-family: system-ui, sans-serif; font-size: 13px; }}
  dt {{ font-weight: 600; margin-top: 10px; }}
  dd {{ margin: 2px 0 0 0; color: #33383e; }}
  ul {{ font-family: system-ui, sans-serif; font-size: 13px; }}
  li {{ margin-bottom: 7px; }}
  footer {{ margin-top: 40px; border-top: 1px solid #c9cdd2; padding-top: 14px;
            font-family: system-ui, sans-serif; font-size: 11px; color: #5b6169; }}
  code {{ background: #eceef0; padding: 1px 5px; font-size: 12px; }}
</style>
</head>
<body>

  <span class="doc-type">{e(PROTOTYPE_TITLE)}</span>
  <h1>Experimental Airfare Price Index for Domestic Air Travel in India</h1>
  <p class="headline-label">Reference date {bulletin.reference_date.isoformat()}
     &middot; Index reference base {e(bulletin.base_period)}</p>

  <div class="banner {provenance_banner_class}">
    <div class="banner-title">Data provenance: {e(provenance_headline)}</div>
    <p>{e(
        "Figures derive from observations collected from a real permitted source. They "
        "remain provisional and unvalidated."
        if is_real else
        "Figures derive from generated or replayed observations, NOT from collected "
        "airline or OTA prices. They demonstrate that the index pipeline computes "
        "correctly and carry no inferential validity about actual Indian airfare "
        "inflation."
    )}</p>
  </div>

  <div class="disclaimer">{e(NOT_OFFICIAL_STATEMENT)}</div>
{suppression_html}
  <div class="headline">
    <div class="headline-label">Experimental all-India airfare price index</div>
    <div class="headline-value">{bulletin.headline_index:.2f}</div>
    <div class="headline-changes">
      <div>Month-on-month: <strong>{e(bulletin.mom_display())}</strong></div>
      <div>Year-on-year: <strong>{e(bulletin.yoy_display())}</strong></div>
      <div>Sampling uncertainty: {e(bulletin.uncertainty_display())}</div>
    </div>
  </div>

  <h2>1. Data source and provenance</h2>
  <dl>
    <dt>Data source</dt>
    <dd>{e(provenance_headline)} — source type <code>{e(bulletin.source_type)}</code></dd>
    <dt>Collection period</dt>
    <dd>{e(bulletin.collection_period_label)}</dd>
    <dt>Base period</dt>
    <dd>{e(bulletin.base_period)} (index = 100)</dd>
    <dt>Sample size</dt>
    <dd>{bulletin.sample_size:,} validated observations across
        {bulletin.matched_products:,} matched product comparisons</dd>
    <dt>Basket coverage</dt>
    <dd>{bulletin.routes_included} of {bulletin.routes_in_basket} routes
        ({bulletin.coverage_weight:.1%} of basket weight);
        renormalization {"applied" if bulletin.renormalization_applied else "not applied"}</dd>
    <dt>Data quality</dt>
    <dd>{_num(bulletin.data_quality_pct)}% of observations passed validation</dd>
  </dl>

  <h2>2. Methodology</h2>
  <dl>
    <dt>Elementary aggregate</dt>
    <dd>Matched-model Jevons index: the geometric mean of price relatives over products
        matched on route, airline, cabin, fare family, stop count, refundability and
        baggage allowance. Matching prevents a change in product quality or sample mix
        from being read as a price change.</dd>
    <dt>Booking-horizon treatment</dt>
    <dd>Horizons T+0, T+3, T+7, T+15 and T+30 are indexed <strong>separately</strong>
        and combined with fixed equal weights, so the index does not move when the
        horizon mix of the sample changes.</dd>
    <dt>Upper-level aggregation</dt>
    <dd>Young-type weighted mean over route indices, using
        {e(bulletin.weighting_status.lower())}
        {e(bulletin.weighting_method.replace("_", " "))} weights
        (basket version {e(bulletin.weight_basket_version)}).</dd>
    <dt>Seasonal adjustment</dt>
    <dd>{e(bulletin.seasonal_adjustment)}</dd>
    <dt>Versions</dt>
    <dd>methodology <code>{e(bulletin.methodology_version)}</code> &middot;
        validation rules <code>{e(bulletin.validation_rules_version)}</code> &middot;
        collector <code>{e(bulletin.collector_version)}</code></dd>
  </dl>

  <h2>3. Booking-horizon indices</h2>
  <table>
    <thead><tr><th>Horizon</th><th>Mean index</th><th>Routes with index</th>
      <th>Matched products</th><th>Policy weight</th></tr></thead>
    <tbody>{horizon_html}</tbody>
  </table>

  <h2>4. Routes with the largest increases</h2>
  <table>
    <thead><tr><th>Route</th><th>Weight</th><th>Route index</th>
      <th>Contribution</th><th>Matched products</th></tr></thead>
    <tbody>{routes_up_html}</tbody>
  </table>

  <h2>5. Routes with the largest decreases</h2>
  <table>
    <thead><tr><th>Route</th><th>Weight</th><th>Route index</th>
      <th>Contribution</th><th>Matched products</th></tr></thead>
    <tbody>{routes_down_html}</tbody>
  </table>

  <h2>6. Missing routes and imputation</h2>
  <p style="font-family: system-ui, sans-serif; font-size: 12px;">
    Routes with no computable index for this period. No value is imputed for them;
    their absence is recorded and reflected in the coverage figure above.
  </p>
  <table>
    <thead><tr><th>Route</th><th>Weight</th><th>Reason</th><th>Imputed value</th></tr></thead>
    <tbody>{missing_html}</tbody>
  </table>

  <h2>7. Limitations</h2>
  <ul>{limitations_html}</ul>

  <h2>8. Revision status</h2>
  <dl>
    <dt>Status</dt>
    <dd>Provisional. All figures are subject to revision.</dd>
    <dt>Recorded revisions</dt>
    <dd>{bulletin.revision_count} entries in the revision log</dd>
    <dt>Open anomalies awaiting review</dt>
    <dd>{bulletin.anomalies_open}</dd>
    <dt>Revision policy</dt>
    <dd>Every publication and recomputation appends a revision record, so any change to
        a published figure carries a recorded reason.</dd>
  </dl>

  <footer>
    <p><strong>{e(PROTOTYPE_TITLE)}</strong> &middot; internal identifier
       {e(bulletin.report_id)} &middot; generated
       {bulletin.generated_at.isoformat()}</p>
    <p>{e(NOT_OFFICIAL_STATEMENT)}</p>
    <p>Methodological references: ILO/IMF Consumer Price Index Manual (2020) for
       elementary aggregate formulae. Passenger volumes used for weighting are
       approximations of published domestic city-pair traffic and are labelled
       provisional.</p>
  </footer>

</body>
</html>"""


def _num(value: Optional[float], places: int = 2) -> str:
    """Render a number, or an em dash when absent. Never a zero standing in for absent."""
    if value is None:
        return "—"
    try:
        return f"{float(value):.{places}f}"
    except (TypeError, ValueError):
        return "—"


def _pct(value: Optional[float]) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return "—"
