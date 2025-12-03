import argparse
import os
from typing import List

from .config_loader import load_config
from .data_ingestion import ingest_all_data
from .data_processing import process_data
from .insight_engine import generate_insights
from .report_generator.pdf_report import generate_pdf_report
from .report_generator.ppt_report import generate_ppt_report
from .utils.logging_utils import get_logger

logger = get_logger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automated Insight Engine")
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to YAML config file",
    )
    return parser.parse_args()


def _ensure_output_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def main() -> None:
    args = _parse_args()
    config = load_config(args.config)

    # Ingest
    traffic_df, clicks_df, weather_df, sql_df = ingest_all_data(config)

    # Process
    merged_df, metrics = process_data(traffic_df, clicks_df, weather_df, sql_df)

    # Insights (LLM or fallback)
    insights = generate_insights(metrics, config)

    # Output
    output_dir = config["report"]["output_dir"]
    _ensure_output_dir(output_dir)

    client_name = config["report"]["client_name"].replace(" ", "_")
    week_start = config["report"]["week_start"]
    week_end = config["report"]["week_end"]
    base_filename = f"{client_name}_{week_start}_to_{week_end}"

    formats: List[str] = config["report"].get("output_formats", ["pdf"])

    if "pdf" in formats:
        pdf_path = os.path.join(output_dir, base_filename + ".pdf")
        generate_pdf_report(merged_df, metrics, insights, config, pdf_path)

    if "pptx" in formats:
        pptx_path = os.path.join(output_dir, base_filename + ".pptx")
        generate_ppt_report(merged_df, metrics, insights, config, pptx_path)

    logger.info("All reports generated successfully.")


if __name__ == "__main__":
    main()
