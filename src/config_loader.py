import os
from typing import Any, Dict

import yaml

from .utils.logging_utils import get_logger

logger = get_logger(__name__)


def load_config(config_path: str) -> Dict[str, Any]:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    logger.info("Loaded config from %s", config_path)
    return config
