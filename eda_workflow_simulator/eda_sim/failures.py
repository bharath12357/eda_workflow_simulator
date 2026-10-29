"""Failure simulation: deliberately break a stage to test error handling."""

from __future__ import annotations

from eda_sim.config import FailureSettings
from eda_sim.exceptions import SimulatedTimeoutError, StageError


class FailureInjector:
    """Raises a chosen failure when a chosen stage runs.

    Modes:
        error   - a normal StageError (not retried).
        timeout - SimulatedTimeoutError for the first ``fail_attempts``
                  attempts, then succeeds (shows retry logic).
        crash   - an unexpected RuntimeError (shows crash handling).
    """

    def __init__(self, settings: FailureSettings) -> None:
        self._settings = settings

    @property
    def active(self) -> bool:
        return self._settings.enabled

    def maybe_fail(self, stage_name: str, attempt: int) -> None:
        """Raise if this ``stage_name`` / ``attempt`` is the injection target."""
        s = self._settings
        if not s.enabled or s.stage != stage_name:
            return
        if s.mode == "error":
            raise StageError(f"Injected error in stage '{stage_name}'")
        if s.mode == "timeout":
            if attempt <= s.fail_attempts:
                raise SimulatedTimeoutError(
                    f"Injected timeout in stage '{stage_name}' (attempt {attempt})"
                )
            return
        if s.mode == "crash":
            raise RuntimeError(f"Injected crash in stage '{stage_name}'")
