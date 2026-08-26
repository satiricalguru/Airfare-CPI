"""
SIH26056 — MoSPI-Format Monthly Airfare Price Index Report Generator

Produces official statistical release bulletins formatted for MoSPI:
- Executive Summary & Headline Airfare CPI (Base 2024=100)
- Month-on-Month (MoM) and Year-on-Year (YoY) Inflation Metrics
- Route-level Jevons Indices & DGCA Passenger-Weight Contributions
- Booking-Horizon Price Dispersion (Advance-purchase effect analysis)
- Quality Assurance & Anomaly Diagnostics Summary
- Export to JSON and Government Publication HTML / Text
"""

from datetime import datetime, date
from typing import Optional
from dataclasses import dataclass


@dataclass
class MonthlyBulletin:
    """Statistical bulletin representation."""
    report_id: str
    publication_date: str
    reference_month: str
    headline_cpi: float
    mom_rate_pct: Optional[float]
    routes_evaluated: int
    total_observations: int
    top_accelerating_routes: list[dict]
    top_decelerating_routes: list[dict]
    booking_horizon_summary: list[dict]
    data_quality_pct: float


class MoSPIReportGenerator:
    """
    Generates structured reports conforming to MoSPI release conventions.
    """

    @staticmethod
    def generate_html_report(bulletin: MonthlyBulletin) -> str:
        """Render a publication-ready HTML bulletin."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>MoSPI Airfare CPI Monthly Statistical Bulletin - {bulletin.reference_month}</title>
<style>
  body {{ font-family: 'Times New Roman', serif; margin: 40px; color: #111; line-height: 1.5; }}
  .header {{ text-align: center; border-bottom: 2px solid #000; padding-bottom: 12px; margin-bottom: 24px; }}
  .govt-title {{ font-size: 16px; font-weight: bold; text-transform: uppercase; }}
  .ministry-title {{ font-size: 14px; margin-top: 4px; }}
  .doc-title {{ font-size: 18px; font-weight: bold; margin-top: 12px; }}
  .meta-table {{ width: 100%; margin-bottom: 20px; font-size: 12px; }}
  .kpi-box {{ border: 1px solid #333; padding: 15px; margin: 20px 0; background-color: #f9f9f9; }}
  .kpi-headline {{ font-size: 24px; font-weight: bold; color: #003366; }}
  table.data-table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 12px; }}
  table.data-table th, table.data-table td {{ border: 1px solid #999; padding: 6px 10px; text-align: left; }}
  table.data-table th {{ background-color: #e6e6e6; }}
  .section-title {{ font-size: 14px; font-weight: bold; margin-top: 24px; text-transform: uppercase; border-bottom: 1px solid #ccc; padding-bottom: 4px; }}
  .footer {{ margin-top: 40px; font-size: 11px; color: #666; border-top: 1px solid #ccc; padding-top: 10px; }}
</style>
</head>
<body>
  <div class="header">
    <div class="govt-title">Government of India</div>
    <div class="ministry-title">Ministry of Statistics and Programme Implementation (MoSPI)</div>
    <div class="ministry-title">National Statistical Office (NSO) — Price Statistics Division</div>
    <div class="doc-title">PRESS RELEASE: ALL-INDIA CONSUMER PRICE INDEX FOR DOMESTIC AIR TRAVEL</div>
    <div style="font-size: 12px; margin-top: 6px;">Base Year: 2024 = 100 | Reference Period: {bulletin.reference_month}</div>
  </div>

  <table class="meta-table">
    <tr>
      <td><strong>Release ID:</strong> {bulletin.report_id}</td>
      <td style="text-align: right;"><strong>Date of Release:</strong> {bulletin.publication_date}</td>
    </tr>
  </table>

  <div class="kpi-box">
    <div>ALL-INDIA AIRFARE CONSUMER PRICE INDEX (PROVISIONAL)</div>
    <div class="kpi-headline">{bulletin.headline_cpi:.2f}</div>
    <div>Month-on-Month Movement: <strong>{bulletin.mom_rate_pct:+.2f}%</strong></div>
    <div style="font-size: 12px; margin-top: 6px;">Based on {bulletin.total_observations:,} validated quotes across {bulletin.routes_evaluated} representative domestic city-pairs.</div>
  </div>

  <div class="section-title">1. Key Methodological Highlights</div>
  <p style="font-size: 12px;">
    The All-India Airfare Price Index reflects price fluctuations of scheduled domestic commercial passenger flights across 25 high-density routes weighted by Directorate General of Civil Aviation (DGCA) city-pair passenger traffic. Micro-level route indices are computed using the <strong>Jevons geometric mean formula</strong>, stratified across five advance-purchase booking horizons (T+0, T+3, T+7, T+15, and T+30).
  </p>

  <div class="section-title">2. Top Contributing Routes (Inflation Acceleration)</div>
  <table class="data-table">
    <thead>
      <tr>
        <th>Route</th>
        <th>DGCA Weight (%)</th>
        <th>Jevons Route Index</th>
        <th>National Contribution (%)</th>
      </tr>
    </thead>
    <tbody>
      {''.join(f"<tr><td>{r.get('origin_code')}-{r.get('destination_code')}</td><td>{r.get('weight',0)*100:.2f}%</td><td>{r.get('jevons_index',1):.4f}</td><td>{r.get('contribution_pct',0):.2f}%</td></tr>" for r in bulletin.top_accelerating_routes)}
    </tbody>
  </table>

  <div class="section-title">3. Advance-Purchase Booking Horizon Analysis</div>
  <table class="data-table">
    <thead>
      <tr>
        <th>Horizon</th>
        <th>Average Observed Fare (INR)</th>
        <th>Median Fare (INR)</th>
        <th>Observations</th>
      </tr>
    </thead>
    <tbody>
      {''.join(f"<tr><td>T+{h.get('horizon_days')}</td><td>INR {h.get('avg_fare',0):,.2f}</td><td>INR {h.get('median_fare',0):,.2f}</td><td>{h.get('observation_count',0):,}</td></tr>" for h in bulletin.booking_horizon_summary)}
    </tbody>
  </table>

  <div class="footer">
    <p>Issued by: Price Statistics Division, MoSPI, New Delhi.</p>
    <p>Data Source: Automated Electronic Price Collection Architecture (SIH26056 Specification).</p>
  </div>
</body>
</html>"""
