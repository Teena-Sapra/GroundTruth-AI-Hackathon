import os
from typing import Dict, Any, List

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    PageBreak,
)

from ..utils.logging_utils import get_logger
from ..charts import generate_charts

logger = get_logger(__name__)


def _build_key_highlights(metrics: Dict[str, Any]) -> List[str]:
    overall = metrics["overall"]
    campaign_summary: pd.DataFrame = metrics["campaign_summary"]

    highlights: List[str] = []
    highlights.append(
        f"Campaigns delivered {int(overall['total_impressions']):,} impressions, "
        f"{int(overall['total_clicks']):,} clicks and "
        f"{int(overall['total_conversions']):,} conversions this week."
    )
    highlights.append(
        f"Overall CTR was {overall['overall_ctr']:.2%} with an average CPC of "
        f"{overall['overall_cpc']:.2f} and CPA of {overall['overall_cpa']:.2f}."
    )

    if not campaign_summary.empty:
        top_conv = campaign_summary.sort_values("conversions", ascending=False).iloc[0]
        highlights.append(
            f"Top converting campaign: {top_conv['campaign_id']} "
            f"with {int(top_conv['conversions']):,} conversions and a CPA of {top_conv['cpa']:.2f}."
        )

        top_ctr = campaign_summary.sort_values("ctr", ascending=False).iloc[0]
        if top_ctr["campaign_id"] != top_conv["campaign_id"]:
            highlights.append(
                f"Best CTR: {top_ctr['campaign_id']} with CTR of {top_ctr['ctr']:.2%}."
            )

        worst_cpa = campaign_summary.sort_values("cpa", ascending=False).iloc[0]
        highlights.append(
            f"Key cost risk: {worst_cpa['campaign_id']} has the highest CPA at {worst_cpa['cpa']:.2f}."
        )

    return highlights


def _build_top_wins(metrics: Dict[str, Any]) -> List[str]:
    campaign_summary: pd.DataFrame = metrics["campaign_summary"]
    wins: List[str] = []
    if campaign_summary.empty:
        return wins

    top_conv = campaign_summary.sort_values("conversions", ascending=False).head(2)
    for _, row in top_conv.iterrows():
        wins.append(
            f"{row['campaign_id']} delivered {int(row['conversions']):,} conversions "
            f"at a CPA of {row['cpa']:.2f}, making it a strong driver of performance."
        )

    low_cpa = campaign_summary.sort_values("cpa", ascending=True).head(1)
    row = low_cpa.iloc[0]
    wins.append(
        f"{row['campaign_id']} achieved the lowest CPA at {row['cpa']:.2f}, indicating high efficiency."
    )

    return wins


def _build_key_concerns(metrics: Dict[str, Any]) -> List[str]:
    campaign_summary: pd.DataFrame = metrics["campaign_summary"]
    concerns: List[str] = []
    if campaign_summary.empty:
        return concerns

    worst_cpa = campaign_summary.sort_values("cpa", ascending=False).head(2)
    for _, row in worst_cpa.iterrows():
        concerns.append(
            f"{row['campaign_id']} shows elevated CPA at {row['cpa']:.2f} with "
            f"{int(row['conversions']):,} conversions, suggesting room for optimization."
        )

    low_conv = campaign_summary.sort_values("conversions", ascending=True).head(1)
    row = low_conv.iloc[0]
    concerns.append(
        f"{row['campaign_id']} has the lowest conversion volume "
        f"({int(row['conversions']):,} conversions) and may require creative or targeting refresh."
    )

    return concerns


def _build_recommendations(metrics: Dict[str, Any]) -> List[str]:
    campaign_summary: pd.DataFrame = metrics["campaign_summary"]

    if campaign_summary.empty:
        return [
            "Increase data volume and tracking coverage to enable more granular optimization.",
            "Test multiple creatives per campaign to identify winning variations.",
        ]

    recs: List[str] = []

    top_cvr = campaign_summary.sort_values("cvr", ascending=False).head(2)
    low_cpa = campaign_summary.sort_values("cpa", ascending=True).head(2)
    worst_cpa = campaign_summary.sort_values("cpa", ascending=False).head(2)

    top_cvr_campaigns = ", ".join(top_cvr["campaign_id"].astype(str).tolist())
    low_cpa_campaigns = ", ".join(low_cpa["campaign_id"].astype(str).tolist())
    worst_cpa_campaigns = ", ".join(worst_cpa["campaign_id"].astype(str).tolist())

    recs.append(
        f"Reallocate a portion of budget toward high-CVR campaigns ({top_cvr_campaigns}) "
        f"and low-CPA campaigns ({low_cpa_campaigns}) to scale efficient volume."
    )
    recs.append(
        f"Audit creatives, audiences and landing pages for higher-CPA campaigns ({worst_cpa_campaigns}) "
        "to reduce cost and improve conversion efficiency."
    )
    recs.append(
        "Introduce structured A/B tests on creatives and audience segments and evaluate performance "
        "over the next 1–2 weeks before scaling further."
    )

    return recs


def _build_campaign_insights(metrics: Dict[str, Any]) -> str:
    campaign_summary: pd.DataFrame = metrics["campaign_summary"]
    if campaign_summary.empty:
        return "Insufficient campaign-level data to generate detailed insights."

    lines: List[str] = []

    top_by_conv = campaign_summary.sort_values("conversions", ascending=False).head(3)
    conv_names = ", ".join(top_by_conv["campaign_id"].astype(str).tolist())
    lines.append(
        f"The highest converting campaigns this week were {conv_names}, "
        "indicating strong alignment between messaging, targeting and audience intent."
    )

    top_by_spend = campaign_summary.sort_values("spend", ascending=False).head(3)
    spend_names = ", ".join(top_by_spend["campaign_id"].astype(str).tolist())
    lines.append(
        f"From a budget allocation perspective, {spend_names} absorbed the majority of spend. "
        "Monitoring their marginal returns will help avoid diminishing performance as budgets scale."
    )

    return " ".join(lines)


def _build_kpi_tile_table(overall: Dict[str, Any]) -> Table:
    data = [
        ["Metric", "Value"],
        ["Impressions", f"{int(overall['total_impressions']):,}"],
        ["Clicks", f"{int(overall['total_clicks']):,}"],
        ["Conversions", f"{int(overall['total_conversions']):,}"],
        ["Spend", f"{overall['total_spend']:.2f}"],
        ["CTR", f"{overall['overall_ctr']:.2%}"],
        ["CPC", f"{overall['overall_cpc']:.2f}"],
        ["CVR", f"{overall['overall_cvr']:.2%}"],
        ["CPA", f"{overall['overall_cpa']:.2f}"],
    ]

    table = Table(data, hAlign="LEFT", colWidths=[4 * cm, 5 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 11),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F5F5F5")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("TOPPADDING", (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
            ]
        )
    )
    return table


def _detect_anomalies(merged_df: pd.DataFrame, drop_threshold: float = 0.3) -> List[str]:
    """
    Detect significant drops in impressions by date + location vs previous day.
    Correlate with rainfall_mm if present.
    Returns human-readable strings like:
    "Traffic dropped 42.3% in Mumbai on 2025-01-05 (impressions 28,000 vs 48,500 previous day). Rainfall: 9.5mm."
    """
    if "impressions" not in merged_df.columns or "location" not in merged_df.columns or "date" not in merged_df.columns:
        return []

    daily = (
        merged_df.groupby(["date", "location"], as_index=False)["impressions"]
        .sum()
        .sort_values(["location", "date"])
    )

    anomalies: List[str] = []

    has_rain = "rainfall_mm" in merged_df.columns

    for location, grp in daily.groupby("location"):
        grp = grp.sort_values("date")
        for i in range(1, len(grp)):
            prev_row = grp.iloc[i - 1]
            curr_row = grp.iloc[i]
            prev_impr = prev_row["impressions"]
            curr_impr = curr_row["impressions"]
            if prev_impr <= 0:
                continue
            change = (curr_impr - prev_impr) / prev_impr
            if change <= -drop_threshold:
                drop_pct = -change * 100.0
                date_str = str(curr_row["date"])
                msg = (
                    f"Traffic dropped {drop_pct:.1f}% in {location} on {date_str} "
                    f"(impressions {int(curr_impr):,} vs {int(prev_impr):,} previous day)"
                )

                if has_rain:
                    rain_vals = merged_df[
                        (merged_df["date"] == curr_row["date"])
                        & (merged_df["location"] == location)
                    ]["rainfall_mm"]
                    if not rain_vals.empty:
                        rain = float(rain_vals.mean())
                        msg += f". Reported rainfall: {rain:.1f}mm."

                anomalies.append(msg + ".")

    return anomalies


def generate_pdf_report(
    merged_df: pd.DataFrame,
    metrics: Dict[str, Any],
    insights: Dict[str, str],
    config,
    output_path: str,
) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Generate charts
    base_output_dir = os.path.dirname(output_path)
    chart_paths = generate_charts(merged_df, metrics, base_output_dir)

    # Styles
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    body = styles["BodyText"]
    body.leading = 14

    # Centered style for subtitle lines
    center_body = ParagraphStyle(
        "CenterBody",
        parent=body,
        alignment=1,  # CENTER
    )

    # Smaller grey caption style
    caption = ParagraphStyle(
        "Caption",
        parent=body,
        fontSize=8,
        textColor=colors.grey,
        leading=10,
    )

    doc = SimpleDocTemplate(output_path, pagesize=A4)
    story = []

    client_name = config["report"]["client_name"]
    week_start = config["report"]["week_start"]
    week_end = config["report"]["week_end"]

    # --- Cover / Title Page ---
    story.append(Paragraph(f"{client_name} - Weekly Performance Report", title_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Reporting Period: {week_start} to {week_end}", center_body))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Prepared by: Automated Insight Engine", center_body))
    story.append(Spacer(1, 40))

    story.append(PageBreak())

    # --- Executive Summary ---
    story.append(Paragraph("Executive Summary", h1))
    story.append(Spacer(1, 6))
    story.append(Paragraph(insights["executive_summary"], body))
    story.append(Spacer(1, 18))

    # Top wins & concerns
    wins = _build_top_wins(metrics)
    concerns = _build_key_concerns(metrics)

    if wins:
        story.append(Paragraph("Top Wins", h2))
        for w in wins:
            story.append(Paragraph(f"• {w}", body))
            story.append(Spacer(1, 2))
        story.append(Spacer(1, 12))

    if concerns:
        story.append(Paragraph("Key Concerns", h2))
        for c in concerns:
            story.append(Paragraph(f"• {c}", body))
            story.append(Spacer(1, 2))
        story.append(Spacer(1, 18))

    # --- Key Highlights & KPIs ---
    story.append(Paragraph("Key Highlights & KPIs", h1))
    story.append(Spacer(1, 6))

    highlights = _build_key_highlights(metrics)
    story.append(Paragraph("Key Highlights", h2))
    story.append(Spacer(1, 4))
    for h in highlights:
        story.append(Paragraph(f"• {h}", body))
        story.append(Spacer(1, 2))
    story.append(Spacer(1, 10))

    overall = metrics["overall"]
    story.append(Paragraph("Core KPIs", h2))
    story.append(Spacer(1, 4))
    story.append(_build_kpi_tile_table(overall))
    story.append(Spacer(1, 18))

    # --- Visual Performance Overview ---
    story.append(Paragraph("Visual Performance Overview", h1))
    story.append(Spacer(1, 6))

    if "campaign_bar" in chart_paths:
        story.append(Paragraph("Top Campaigns – Impressions vs Clicks", h2))
        img = RLImage(chart_paths["campaign_bar"], width=16 * cm, height=9 * cm)
        img.hAlign = "CENTER"
        story.append(img)
        story.append(Spacer(1, 4))
        story.append(Paragraph("Figure 1: Comparison of impressions and clicks across top campaigns.", caption))
        story.append(Spacer(1, 12))

    if "daily_trend" in chart_paths:
        story.append(Paragraph("Daily Trend – Impressions & Clicks", h2))
        img = RLImage(chart_paths["daily_trend"], width=16 * cm, height=9 * cm)
        img.hAlign = "CENTER"
        story.append(img)
        story.append(Spacer(1, 4))
        story.append(Paragraph("Figure 2: Daily evolution of impressions and clicks for the reporting period.", caption))
        story.append(Spacer(1, 18))

    # --- Campaign Performance & Insights ---
    story.append(Paragraph("Campaign Performance & Insights", h1))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Narrative Insights", h2))
    story.append(Spacer(1, 4))
    story.append(Paragraph(_build_campaign_insights(metrics), body))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Campaign Performance (Top 10 by Spend)", h2))
    story.append(Spacer(1, 4))

    campaign_summary: pd.DataFrame = metrics["campaign_summary"]
    top_campaigns = campaign_summary.sort_values("spend", ascending=False).head(10)

    campaign_data = [
        ["Campaign", "Impr.", "Clicks", "Conv.", "Spend", "CTR", "CPC", "CVR", "CPA"]
    ]
    for _, row in top_campaigns.iterrows():
        campaign_data.append(
            [
                str(row["campaign_id"]),
                f"{int(row['impressions']):,}",
                f"{int(row['clicks']):,}",
                f"{int(row['conversions']):,}",
                f"{row['spend']:.2f}",
                f"{row['ctr']:.2%}",
                f"{row['cpc']:.2f}",
                f"{row['cvr']:.2%}",
                f"{row['cpa']:.2f}",
            ]
        )

    col_widths = [3 * cm] + [1.6 * cm] * 8
    campaign_table = Table(campaign_data, hAlign="LEFT", colWidths=col_widths)
    campaign_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8F8F8")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
            ]
        )
    )
    story.append(campaign_table)
    story.append(Spacer(1, 18))

    # --- Anomaly Detection ---
    anomalies = _detect_anomalies(merged_df)
    if anomalies:
        story.append(Paragraph("Anomaly Detection", h1))
        story.append(Spacer(1, 6))
        for a in anomalies:
            story.append(Paragraph(f"• {a}", body))
            story.append(Spacer(1, 2))
        story.append(Spacer(1, 18))

    # --- Optimization Recommendations ---
    story.append(Paragraph("Optimization Recommendations", h1))
    story.append(Spacer(1, 6))

    recs = _build_recommendations(metrics)
    for r in recs:
        story.append(Paragraph(f"• {r}", body))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 18))

    # --- Glossary ---
    story.append(Paragraph("Glossary", h1))
    story.append(Spacer(1, 6))
    glossary_items = [
        ("CTR (Click-Through Rate)", "Percentage of impressions that resulted in clicks."),
        ("CVR (Conversion Rate)", "Percentage of clicks that resulted in conversions."),
        ("CPA (Cost Per Acquisition)", "Average cost required to generate a single conversion."),
    ]
    for term, definition in glossary_items:
        story.append(Paragraph(f"<b>{term}</b>: {definition}", body))
        story.append(Spacer(1, 4))

    # Build PDF
    doc.build(story)
    logger.info("PDF report generated at %s", output_path)
