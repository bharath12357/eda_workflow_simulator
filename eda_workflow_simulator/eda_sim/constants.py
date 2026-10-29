"""Shared constants. Kept free of imports so any module can use them."""

from __future__ import annotations

# Canonical stage order. Config "stages" must be a subset in this order.
STAGE_ORDER: tuple[str, ...] = (
    "input_validation",
    "design_prep",
    "elaboration",
    "lint",
    "simulation",
    "timing",
)

LOG_LEVELS: tuple[str, ...] = ("DEBUG", "INFO", "WARNING", "ERROR")
FAILURE_MODES: tuple[str, ...] = ("error", "timeout", "crash")

STATUS_PASSED = "PASSED"
STATUS_FAILED = "FAILED"
STATUS_SKIPPED = "SKIPPED"

# Process exit codes used by the CLI.
EXIT_OK = 0
EXIT_WORKFLOW_FAILED = 1
EXIT_USAGE_ERROR = 2
