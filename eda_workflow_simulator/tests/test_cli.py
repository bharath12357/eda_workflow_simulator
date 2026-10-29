"""End-to-end tests for eda_sim.cli (main() called in-process)."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import List, Tuple

from eda_sim.cli import main
from tests.helpers import PROJECT_ROOT, SAMPLES


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def _call(self, *argv: str) -> Tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def _run(self, sample: str, *extra: str) -> Tuple[int, str, str]:
        return self._call(
            "run", str(SAMPLES / sample), "--delay-ms", "0", "--quiet",
            "--report-dir", str(self.tmp / "reports"), "--log-dir", str(self.tmp / "logs"),
            *extra,
        )

    def _reports(self) -> List[Path]:
        return sorted((self.tmp / "reports").glob("report_*.json"))

    def test_run_success_writes_report_and_log(self) -> None:
        code, out, _ = self._run("counter.v")
        self.assertEqual(code, 0)
        self.assertIn("Status   : PASSED", out)
        reports = self._reports()
        self.assertEqual(len(reports), 1)
        self.assertEqual(json.loads(reports[0].read_text())["status"], "PASSED")
        self.assertEqual(len(list((self.tmp / "logs").glob("run_*.log"))), 1)

    def test_run_workflow_failure_exit_1(self) -> None:
        code, out, _ = self._run("broken_unbalanced.v")
        self.assertEqual(code, 1)
        self.assertIn("Unbalanced", out)
        self.assertEqual(len(self._reports()), 1)

    def test_run_missing_input_is_a_failed_run_not_a_crash(self) -> None:
        code, out, _ = self._call(
            "run", str(self.tmp / "ghost.v"), "--delay-ms", "0", "--quiet",
            "--report-dir", str(self.tmp / "reports"), "--log-dir", str(self.tmp / "logs"),
        )
        self.assertEqual(code, 1)
        self.assertIn("not found", out)

    def test_inject_failure_flags(self) -> None:
        code, _, _ = self._run("counter.v", "--inject-failure", "lint", "--failure-mode", "crash")
        self.assertEqual(code, 1)
        data = json.loads(self._reports()[0].read_text())
        self.assertIn("Unexpected RuntimeError", data["stages"][3]["error"])

    def test_inject_timeout_recovers(self) -> None:
        code, _, _ = self._run("counter.v", "--inject-failure", "simulation",
                               "--failure-mode", "timeout")
        self.assertEqual(code, 0)
        data = json.loads(self._reports()[0].read_text())
        self.assertEqual(data["stages"][4]["attempts"], 2)

    def test_failure_mode_without_stage_is_usage_error(self) -> None:
        code, _, err = self._run("counter.v", "--failure-mode", "crash")
        self.assertEqual(code, 2)
        self.assertIn("--inject-failure", err)

    def test_target_mhz_override_causes_timing_failure(self) -> None:
        code, out, _ = self._run("counter.v", "--target-mhz", "5000")
        self.assertEqual(code, 1)
        self.assertIn("Timing violated", out)

    def test_bad_config_exit_2(self) -> None:
        code, _, err = self._run("counter.v", "--config", str(PROJECT_ROOT / "config" / "bad_config.json"))
        self.assertEqual(code, 2)
        self.assertIn("ERROR", err)

    def test_validate_config(self) -> None:
        code, out, _ = self._call("validate-config", str(PROJECT_ROOT / "config" / "default_config.json"))
        self.assertEqual(code, 0)
        self.assertIn("valid configuration", out)
        code, _, err = self._call("validate-config", str(PROJECT_ROOT / "config" / "bad_config.json"))
        self.assertEqual(code, 2)

    def test_validate_input(self) -> None:
        self.assertEqual(self._call("validate-input", str(SAMPLES / "counter.v"))[0], 0)
        code, out, _ = self._call("validate-input", str(SAMPLES / "wrong_extension.txt"))
        self.assertEqual(code, 1)
        self.assertIn("INVALID", out)

    def test_list_stages(self) -> None:
        code, out, _ = self._call("list-stages")
        self.assertEqual(code, 0)
        self.assertIn("6. timing", out)

    def test_show_report_round_trip(self) -> None:
        self._run("counter.v")
        code, out, _ = self._call("show-report", str(self._reports()[0]))
        self.assertEqual(code, 0)
        self.assertIn("passed=6", out)

    def test_show_report_missing_file(self) -> None:
        code, _, err = self._call("show-report", str(self.tmp / "none.json"))
        self.assertEqual(code, 2)
        self.assertIn("not found", err)

    def test_no_command_is_usage_error(self) -> None:
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(main([]), 2)

    def test_version(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["--version"]), 0)
        self.assertIn("eda_sim 1.0.0", out.getvalue())


if __name__ == "__main__":
    unittest.main()
