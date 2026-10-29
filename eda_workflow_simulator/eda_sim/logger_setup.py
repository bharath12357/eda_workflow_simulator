"""Logging setup: console + timestamped log file."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Tuple

LOGGER_NAME = "eda_sim"
LOG_FORMAT = "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    log_dir: Path, run_id: str, level: str = "INFO", console: bool = True
) -> Tuple[logging.Logger, Path]:
    """Configure the ``eda_sim`` logger and return ``(logger, log_file_path)``.

    Existing handlers are removed first so calling this twice never
    produces duplicated lines.
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"run_{run_id}.log"

    logger = logging.getLogger(LOGGER_NAME)
    shutdown_logging(logger)
    logger.setLevel(getattr(logging, level.upper()))
    logger.propagate = False

    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    return logger, log_path


def shutdown_logging(logger: logging.Logger) -> None:
    """Close and remove every handler (releases the log file on Windows)."""
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
