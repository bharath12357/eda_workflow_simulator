"""Tests for eda_sim.pipeline, failure simulation and retry logic."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from typing import List

from eda_sim.constants import STAGE_ORDER, STATUS_FAILED, STATUS_PASSED, STATUS_SKIPPED
from eda_sim.pipeline import Pipeline, iso, make_run_id
from tests.helpers import SAMPLES, make_config, silent_logger


class FakeClock:
    """Returns a new, later time on every call (deterministic timestamps)."""

    def __init__(self) -> None:
        self._now = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        self._now += timedelta(seconds=1)
        return self._now


def run_pipeline(sample: str, overrides=None, sleeps: List[float] = None):
    sleeps = sleeps if sleeps is not None else []
    pipeline = Pipeline(
        make_config(overrides), silent_logger(), clock=FakeClock(), sleep=sleeps.append
    )
    return pipeline.run(SAMPLES / sample)


class PipelineTests(unittest.TestCase):
    def test_success(self) -> None:
        report = run_pipeline("alu.v")
        self.assertEqual(report.status, STATUS_PASSED)
        self.assertEqual([s.name for s in report.stages], list(STAGE_ORDER))
        self.assertEqual(report.summary["stages_passed"], 6)
        self.assertTrue(all(s.attempts == 1 for s in report.stages))

    def test_failure_stops_and_skips_rest(self) -> None:
        report = run_pipeline("broken_unbalanced.v")
        statuses = {s.name: s.status for s in report.stages}
        self.assertEqual(report.status, STATUS_FAILED)
        self.assertEqual(statuses["input_validation"], STATUS_PASSED)
        self.assertEqual(statuses["design_prep"], STATUS_FAILED)
        self.assertEqual(statuses["elaboration"], STATUS_SKIPPED)
        self.assertEqual(statuses["timing"], STATUS_SKIPPED)
        self.assertEqual(report.summary["stages_skipped"], 4)

    def test_invalid_input_is_reported_not_raised(self) -> None:
        report = run_pipeline("empty.v")
        self.assertEqual(report.status, STATUS_FAILED)
        self.assertIn("empty", report.stages[0].error)

    def test_stage_failure_is_not_retried(self) -> None:
        report = run_pipeline("broken_unbalanced.v")
        self.assertEqual(report.stages[1].attempts, 1)

    def test_subset_of_stages(self) -> None:
        report = run_pipeline("counter.v", {"stages": ["input_validation", "design_prep"]})
        self.assertEqual(len(report.stages), 2)
        self.assertEqual(report.status, STATUS_PASSED)

    def test_timestamps_and_run_id_use_injected_clock(self) -> None:
        report = run_pipeline("counter.v")
        self.assertEqual(report.run_id, "20260102T030406000Z")
        self.assertTrue(report.started_at.startswith("2026-01-02T03:04:"))
        self.assertGreater(report.finished_at, report.started_at)
        self.assertGreater(report.stages[0].finished_at, report.stages[0].started_at)

    def test_delay_uses_injected_sleep(self) -> None:
        sleeps: List[float] = []
        run_pipeline("counter.v", {"simulated_delay_ms": 250}, sleeps)
        self.assertEqual(sleeps, [0.25] * 6)

    def test_config_is_embedded_in_report(self) -> None:
        report = run_pipeline("counter.v")
        self.assertEqual(report.config["retry"]["max_attempts"], 2)


class FailureSimulationTests(unittest.TestCase):
    def _fail(self, **kw):
        return {"failure_simulation": {"enabled": True, **kw}}

    def test_injected_error(self) -> None:
        report = run_pipeline("counter.v", self._fail(stage="lint", mode="error"))
        lint = next(s for s in report.stages if s.name == "lint")
        self.assertEqual(lint.status, STATUS_FAILED)
        self.assertIn("Injected error", lint.error)
        self.assertEqual(lint.attempts, 1)
        self.assertEqual(report.summary["stages_skipped"], 2)

    def test_timeout_recovers_with_retry(self) -> None:
        report = run_pipeline("counter.v", self._fail(stage="simulation", mode="timeout"))
        sim = next(s for s in report.stages if s.name == "simulation")
        self.assertEqual(sim.status, STATUS_PASSED)
        self.assertEqual(sim.attempts, 2)
        self.assertEqual(report.status, STATUS_PASSED)

    def test_timeout_exhausts_retries(self) -> None:
        report = run_pipeline(
            "counter.v", self._fail(stage="simulation", mode="timeout", fail_attempts=2)
        )
        sim = next(s for s in report.stages if s.name == "simulation")
        self.assertEqual(sim.status, STATUS_FAILED)
        self.assertEqual(sim.attempts, 2)
        self.assertIn("Injected timeout", sim.error)

    def test_more_retries_allowed_recovers(self) -> None:
        report = run_pipeline(
            "counter.v",
            {
                "retry": {"max_attempts": 3},
                "failure_simulation": {
                    "enabled": True, "stage": "timing", "mode": "timeout", "fail_attempts": 2,
                },
            },
        )
        timing = report.stages[-1]
        self.assertEqual((timing.status, timing.attempts), (STATUS_PASSED, 3))

    def test_crash_is_caught_and_reported(self) -> None:
        report = run_pipeline("counter.v", self._fail(stage="design_prep", mode="crash"))
        stage = report.stages[1]
        self.assertEqual(stage.status, STATUS_FAILED)
        self.assertIn("Unexpected RuntimeError", stage.error)
        self.assertEqual(report.status, STATUS_FAILED)

    def test_failure_disabled_by_default(self) -> None:
        self.assertEqual(run_pipeline("counter.v").status, STATUS_PASSED)


class HelperTests(unittest.TestCase):
    def test_make_run_id(self) -> None:
        moment = datetime(2026, 10, 18, 7, 13, 0, 123456, tzinfo=timezone.utc)
        self.assertEqual(make_run_id(moment), "20261018T071300123Z")

    def test_run_ids_differ_within_the_same_second(self) -> None:
        a = datetime(2026, 10, 18, 7, 13, 0, 100000, tzinfo=timezone.utc)
        b = datetime(2026, 10, 18, 7, 13, 0, 200000, tzinfo=timezone.utc)
        self.assertNotEqual(make_run_id(a), make_run_id(b))

    def test_iso_has_milliseconds_and_offset(self) -> None:
        moment = datetime(2026, 10, 18, 7, 13, 0, 123000, tzinfo=timezone.utc)
        self.assertEqual(iso(moment), "2026-10-18T07:13:00.123+00:00")


if __name__ == "__main__":
    unittest.main()
