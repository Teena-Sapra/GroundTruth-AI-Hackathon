import os
from typing import Dict, Any

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for servers / scripts

import matplotlib.pyplot as plt
import pandas as pd

from .utils.logging_utils import get_logger

logger = get_logger(__name__)


def generate_charts(
    merged_df: pd.DataFrame,
    metrics: Dict[str, Any],
    output_dir: str,
) -> Dict[str, str]:
    """
    Generate charts and save them as PNGs.
    Returns a dict of chart_name -> file_path.
    """
    charts_dir = os.path.join(output_dir, "charts")
    os.makedirs(charts_dir, exist_ok=True)

    paths: Dict[str, str] = {}

    # 1) Campaign bar chart: impressions & clicks per campaign (top 5 by spend)
    try:
        campaign_summary: pd.DataFrame = metrics["campaign_summary"]
        if not campaign_summary.empty:
            top_campaigns = campaign_summary.sort_values("spend", ascending=False).head(5)

            fig, ax = plt.subplots(figsize=(8, 5))
            x = range(len(top_campaigns))
            labels = top_campaigns["campaign_id"].astype(str).tolist()
            impressions = top_campaigns["impressions"].tolist()
            clicks = top_campaigns["clicks"].tolist()

            width = 0.35
            ax.bar(
                [i - width / 2 for i in x],
                impressions,
                width,
                label="Impressions",
            )
            ax.bar(
                [i + width / 2 for i in x],
                clicks,
                width,
                label="Clicks",
            )

            ax.set_xticks(list(x))
            ax.set_xticklabels(labels, rotation=0)
            ax.set_ylabel("Volume")
            ax.set_title("Top Campaigns by Spend – Impressions vs Clicks")
            ax.legend()
            plt.tight_layout()

            path_campaign = os.path.join(charts_dir, "campaign_bar.png")
            fig.savefig(path_campaign, dpi=150)
            plt.close(fig)

            paths["campaign_bar"] = path_campaign
    except Exception as e:
        logger.exception("Error generating campaign bar chart: %s", e)

    # 2) Daily trend chart: impressions & clicks by date
    try:
        if "date" in merged_df.columns:
            daily = (
                merged_df.groupby("date", as_index=False)[["impressions", "clicks"]]
                .sum()
                .sort_values("date")
            )

            fig, ax = plt.subplots(figsize=(8, 4.5))
            ax.plot(daily["date"], daily["impressions"], marker="o", label="Impressions")
            ax.plot(daily["date"], daily["clicks"], marker="o", label="Clicks")

            ax.set_title("Daily Trend – Impressions & Clicks")
            ax.set_xlabel("Date")
            ax.set_ylabel("Volume")
            plt.xticks(rotation=45)
            ax.legend()
            plt.tight_layout()

            path_trend = os.path.join(charts_dir, "daily_trend.png")
            fig.savefig(path_trend, dpi=150)
            plt.close(fig)

            paths["daily_trend"] = path_trend
    except Exception as e:
        logger.exception("Error generating daily trend chart: %s", e)

    logger.info("Charts generated: %s", paths)
    return paths
