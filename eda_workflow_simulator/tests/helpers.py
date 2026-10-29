"""Shared helpers for the test suite."""

from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from eda_sim.config import DEFAULT_CONFIG, Config, parse_config

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLES = PROJECT_ROOT / "sample_inputs"


def make_config(overrides: Optional[Dict[str, Any]] = None) -> Config:
    """Default config with zero delay, plus optional (nested) overrides."""
    data = copy.deepcopy(DEFAULT_CONFIG)
    data["simulated_delay_ms"] = 0
    for key, value in (overrides or {}).items():
        if isinstance(value, dict) and isinstance(data.get(key), dict):
            data[key].update(value)
        else:
            data[key] = value
    return parse_config(data)


def silent_logger(name: str = "eda_sim_test") -> logging.Logger:
    """A logger that discards everything."""
    logger = logging.getLogger(name)
    logger.handlers = [logging.NullHandler()]
    logger.propagate = False
    return logger
