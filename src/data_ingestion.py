import os
from typing import Optional, Tuple

import pandas as pd
from sqlalchemy import create_engine, text

from .utils.logging_utils import get_logger

logger = get_logger(__name__)


def load_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV not found: {path}")
    logger.info("Loading CSV: %s", path)
    df = pd.read_csv(path)
    return df


def load_sql_table(connection_string: str, query: str) -> pd.DataFrame:
    logger.info("Loading SQL data from %s", connection_string)
    engine = create_engine(connection_string)
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
    return df


def ingest_all_data(config) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Optional[pd.DataFrame]]:
    ds = config["data_sources"]

    traffic_df = load_csv(ds["traffic_csv"])
    clicks_df = load_csv(ds["clicks_csv"])
    weather_df = load_csv(ds["weather_csv"])

    sql_df = None
    sql_cfg = ds.get("sql", {})
    if sql_cfg.get("enabled", False):
        sql_df = load_sql_table(
            sql_cfg["connection_string"],
            sql_cfg["query"],
        )

    logger.info("Ingestion complete: traffic=%d rows, clicks=%d rows, weather=%d rows, sql=%s",
                len(traffic_df), len(clicks_df), len(weather_df),
                "None" if sql_df is None else f"{len(sql_df)} rows")

    return traffic_df, clicks_df, weather_df, sql_df
