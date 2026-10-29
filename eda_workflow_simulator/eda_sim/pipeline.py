"""The workflow engine: runs stages in order with retry and failure handling."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional

from eda_sim import __version__
from eda_sim.config import Config
from eda_sim.constants import STATUS_FAILED, STATUS_PASSED, STATUS_SKIPPED
from eda_sim.exceptions import EdaSimError, SimulatedTimeoutError
from eda_sim.failures import FailureInjector
from eda_sim.models import StageResult, WorkflowReport
from eda_sim.stages import StageContext, create_stage

Clock = Callable[[], datetime]
Sleeper = Callable[[float], None]


def utc_now() -> datetime:
    """Current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def iso(moment: datetime) -> str:
    """ISO-8601 timestamp with milliseconds, e.g. 2026-10-18T07:13:00.123+00:00."""
    return moment.isoformat(timespec="milliseconds")


def make_run_id(moment: datetime) -> str:
    """Filename-safe run id with milliseconds, e.g. ``20261018T071300123Z``.

    Milliseconds keep two runs started in the same second from overwriting
    each other's report and log files.
    """
    utc = moment.astimezone(timezone.utc)
    return utc.strftime("%Y%m%dT%H%M%S") + f"{utc.microsecond // 1000:03d}Z"


class Pipeline:
    """Runs the configured stages against one design file.

    ``clock`` and ``sleep`` can be replaced in unit tests so tests are
    fast and deterministic.
    """

    def __init__(
        self,
        config: Config,
        logger: logging.Logger,
        clock: Clock = utc_now,
        sleep: Sleeper = time.sleep,
        run_id: Optional[str] = None,
    ) -> None:
        self._config = config
        self._log = logger
        self._clock = clock
        self._sleep = sleep
        self._injector = FailureInjector(config.failure)
        self.run_id = run_id or make_run_id(clock())

    def run(self, design_path: Path) -> WorkflowReport:
        """Execute all stages and return the report (never raises for stage failures)."""
        design_path = Path(design_path)
        started = self._clock()
        t0 = time.perf_counter()
        self._log.info("Run %s started for %s", self.run_id, design_path)
        if self._injector.active:
            self._log.warning(
                "Failure simulation ENABLED: stage=%s mode=%s",
                self._config.failure.stage,
                self._config.failure.mode,
            )

        ctx = StageContext(self._config, design_path)
        results: List[StageResult] = []
        failed = False
        for name in self._config.stages:
            if failed:
                self._log.info("[%s] SKIPPED (earlier stage failed)", name)
                results.append(
                    StageResult(name, STATUS_SKIPPED, messages=["Skipped: earlier stage failed"])
                )
                continue
            result = self._run_stage(name, ctx)
            results.append(result)
            failed = result.status != STATUS_PASSED

        status = STATUS_FAILED if failed else STATUS_PASSED
        finished = self._clock()
        duration_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        summary = {
            "stages_total": len(results),
            "stages_passed": sum(r.status == STATUS_PASSED for r in results),
            "stages_failed": sum(r.status == STATUS_FAILED for r in results),
            "stages_skipped": sum(r.status == STATUS_SKIPPED for r in results),
        }
        self._log.info("Run %s finished: %s (%.1f ms)", self.run_id, status, duration_ms)
        return WorkflowReport(
            run_id=self.run_id,
            tool_version=__version__,
            design_file=str(design_path),
            status=status,
            started_at=iso(started),
            finished_at=iso(finished),
            duration_ms=duration_ms,
            config=self._config.to_dict(),
            stages=results,
            summary=summary,
        )

    # ------------------------------------------------------------------
    def _run_stage(self, name: str, ctx: StageContext) -> StageResult:
        """Run one stage with retry on transient (timeout) failures."""
        stage = create_stage(name)
        max_attempts = self._config.retry.max_attempts
        result = StageResult(name, STATUS_FAILED, started_at=iso(self._clock()))
        t0 = time.perf_counter()

        for attempt in range(1, max_attempts + 1):
            result.attempts = attempt
            self._log.info("[%s] attempt %d/%d: %s", name, attempt, max_attempts, stage.description)
            try:
                if self._config.simulated_delay_ms:
                    self._sleep(self._config.simulated_delay_ms / 1000.0)
                self._injector.maybe_fail(name, attempt)
                output = stage.run(ctx)
            except SimulatedTimeoutError as exc:
                self._log.warning("[%s] transient failure: %s", name, exc)
                result.error = str(exc)
                if attempt < max_attempts:
                    self._log.info("[%s] retrying", name)
                    continue
                self._log.error("[%s] FAILED after %d attempt(s)", name, attempt)
                break
            except EdaSimError as exc:
                self._log.error("[%s] FAILED: %s", name, exc)
                result.error = str(exc)
                break
            except Exception as exc:  # noqa: BLE001 - last line of defence
                self._log.exception("[%s] UNEXPECTED ERROR", name)
                result.error = f"Unexpected {type(exc).__name__}: {exc}"
                break
            else:
                result.status = STATUS_PASSED
                result.error = None
                result.messages = output.messages
                result.metrics = output.metrics
                for message in output.messages:
                    self._log.info("[%s] %s", name, message)
                self._log.info("[%s] PASSED", name)
                break

        result.finished_at = iso(self._clock())
        result.duration_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        return result
