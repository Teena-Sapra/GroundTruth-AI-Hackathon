from typing import Dict, Any, Optional, Tuple

import pandas as pd

from .utils.logging_utils import get_logger

logger = get_logger(__name__)


def process_data(
    traffic_df: pd.DataFrame,
    clicks_df: pd.DataFrame,
    weather_df: pd.DataFrame,
    sql_df: Optional[pd.DataFrame] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Basic processing:
    - Ensure date columns are datetime
    - Aggregate by date + campaign_id
    - Join traffic, clicks, weather
    - Compute metrics: CTR, CPC, CVR, etc.
    """
    # Ensure required columns exist
    required_traffic_cols = {"date", "location", "campaign_id", "impressions"}
    required_clicks_cols = {"date", "campaign_id", "clicks", "conversions", "spend"}
    required_weather_cols = {"date", "location", "temperature_c", "rainfall_mm"}

    for cols, name in [
        (required_traffic_cols, "traffic.csv"),
        (required_clicks_cols, "clicks.csv"),
        (required_weather_cols, "weather.csv"),
    ]:
        missing = cols - set(eval(f"{name.split('.')[0].split('_')[0]}_df").columns)
        if missing:
            logger.warning("Dataset %s is missing columns: %s", name, ", ".join(missing))

    # Convert date columns
    for df in (traffic_df, clicks_df, weather_df):
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])

    # Aggregate traffic by date, campaign, location
    traffic_agg = (
        traffic_df.groupby(["date", "campaign_id", "location"], as_index=False)
        .agg({"impressions": "sum"})
    )

    # Aggregate clicks by date, campaign
    clicks_agg = (
        clicks_df.groupby(["date", "campaign_id"], as_index=False)
        .agg({"clicks": "sum", "conversions": "sum", "spend": "sum"})
    )

    # Aggregate weather by date, location (mean)
    weather_agg = (
        weather_df.groupby(["date", "location"], as_index=False)
        .agg({"temperature_c": "mean", "rainfall_mm": "sum"})
    )

    # Join traffic + clicks on date + campaign_id (location kept only from traffic)
    merged = pd.merge(
        traffic_agg,
        clicks_agg,
        on=["date", "campaign_id"],
        how="left",
    )

    # Join weather on date + location
    merged = pd.merge(
        merged,
        weather_agg,
        on=["date", "location"],
        how="left",
    )

    # Compute metrics
    merged["ctr"] = merged["clicks"] / merged["impressions"]
    merged["cpc"] = merged["spend"] / merged["clicks"]
    merged["conversion_rate"] = merged["conversions"] / merged["clicks"]
    merged["cpa"] = merged["spend"] / merged["conversions"]

    # Handle division by zero / NaNs
    for col in ["ctr", "cpc", "conversion_rate", "cpa"]:
        merged[col] = merged[col].replace([float("inf"), float("-inf")], float("nan"))

    # Overall metrics
    overall = {
        "total_impressions": float(merged["impressions"].sum()),
        "total_clicks": float(merged["clicks"].sum()),
        "total_conversions": float(merged["conversions"].sum()),
        "total_spend": float(merged["spend"].sum()),
    }
    overall["overall_ctr"] = overall["total_clicks"] / overall["total_impressions"] if overall["total_impressions"] else 0.0
    overall["overall_cpc"] = overall["total_spend"] / overall["total_clicks"] if overall["total_clicks"] else 0.0
    overall["overall_cvr"] = overall["total_conversions"] / overall["total_clicks"] if overall["total_clicks"] else 0.0
    overall["overall_cpa"] = overall["total_spend"] / overall["total_conversions"] if overall["total_conversions"] else 0.0

    # Campaign-level summary
    campaign_summary = (
        merged.groupby("campaign_id")
        .agg(
            impressions=("impressions", "sum"),
            clicks=("clicks", "sum"),
            conversions=("conversions", "sum"),
            spend=("spend", "sum"),
        )
        .reset_index()
    )
    campaign_summary["ctr"] = campaign_summary["clicks"] / campaign_summary["impressions"]
    campaign_summary["cpc"] = campaign_summary["spend"] / campaign_summary["clicks"]
    campaign_summary["cvr"] = campaign_summary["conversions"] / campaign_summary["clicks"]
    campaign_summary["cpa"] = campaign_summary["spend"] / campaign_summary["conversions"]

    metrics = {
        "overall": overall,
        "campaign_summary": campaign_summary,
    }

    if sql_df is not None:
        metrics["sql_preview"] = sql_df.head(5).to_dict(orient="records")

    logger.info("Processing complete. Rows in merged dataset: %d", len(merged))

    return merged, metrics
