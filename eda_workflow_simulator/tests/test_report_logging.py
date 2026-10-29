"""Tests for eda_sim.report and eda_sim.logger_setup."""

from __future__ import annotations

import json
import logging
import tempfile
import unittest
from pathlib import Path

from eda_sim.exceptions import EdaSimError
from eda_sim.logger_setup import LOGGER_NAME, setup_logging, shutdown_logging
from eda_sim.pipeline import Pipeline
from eda_sim.report import format_summary, load_report, safe_filename, write_report
from tests.helpers import SAMPLES, make_config, silent_logger


class ReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        pipeline = Pipeline(make_config(), silent_logger(), sleep=lambda s: None)
        self.report = pipeline.run(SAMPLES / "counter.v")

    def test_write_creates_valid_json(self) -> None:
        path = write_report(self.report, self.tmp / "nested" / "out")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["status"], "PASSED")
        self.assertEqual(data["run_id"], self.report.run_id)
        self.assertEqual(len(data["stages"]), 6)
        self.assertIn("counter", path.name)

    def test_no_temp_files_left_behind(self) -> None:
        write_report(self.report, self.tmp)
        leftovers = [p.name for p in self.tmp.iterdir() if p.name.startswith(".tmp_")]
        self.assertEqual(leftovers, [])

    def test_overwrite_same_run_id_is_safe(self) -> None:
        first = write_report(self.report, self.tmp)
        second = write_report(self.report, self.tmp)
        self.assertEqual(first, second)
        self.assertEqual(len(list(self.tmp.glob("report_*.json"))), 1)

    def test_load_and_summarise(self) -> None:
        path = write_report(self.report, self.tmp)
        text = format_summary(load_report(path))
        self.assertIn("PASSED", text)
        self.assertIn("simulation", text)

    def test_load_missing(self) -> None:
        with self.assertRaises(EdaSimError):
            load_report(self.tmp / "none.json")

    def test_load_bad_json(self) -> None:
        bad = self.tmp / "bad.json"
        bad.write_text("{", encoding="utf-8")
        with self.assertRaises(EdaSimError):
            load_report(bad)

    def test_load_missing_keys(self) -> None:
        bad = self.tmp / "partial.json"
        bad.write_text('{"run_id": "x"}', encoding="utf-8")
        with self.assertRaisesRegex(EdaSimError, "missing key"):
            load_report(bad)

    def test_safe_filename(self) -> None:
        self.assertEqual(safe_filename('my design:v1*?'), "my_design_v1")
        self.assertEqual(safe_filename("***"), "report")


class LoggingTests(unittest.TestCase):
    def test_log_file_has_timestamped_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            logger, path = setup_logging(Path(tmp) / "logs", "RUN1", "INFO", console=False)
            logger.info("hello world")
            shutdown_logging(logger)
            line = path.read_text(encoding="utf-8").splitlines()[0]
            self.assertRegex(line, r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d{3} \| INFO     \| hello world$")

    def test_repeated_setup_does_not_duplicate_handlers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            setup_logging(Path(tmp), "A", console=False)
            logger, _ = setup_logging(Path(tmp), "B", console=False)
            self.assertEqual(len(logger.handlers), 1)
            shutdown_logging(logger)

    def test_level_is_respected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            logger, path = setup_logging(Path(tmp), "C", "WARNING", console=False)
            logger.info("hidden")
            logger.warning("shown")
            shutdown_logging(logger)
            text = path.read_text(encoding="utf-8")
            self.assertIn("shown", text)
            self.assertNotIn("hidden", text)
            self.assertEqual(logging.getLogger(LOGGER_NAME).handlers, [])


if __name__ == "__main__":
    unittest.main()
