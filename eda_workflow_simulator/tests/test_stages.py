"""Tests for eda_sim.stages (each stage in isolation)."""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any, Dict, Optional

from eda_sim.exceptions import EdaSimError, StageError
from eda_sim.stages import (
    STAGE_REGISTRY,
    DesignPrepStage,
    ElaborationStage,
    InputValidationStage,
    LintStage,
    SimulationStage,
    StageContext,
    TimingStage,
    create_stage,
    strip_comments,
)
from eda_sim.constants import STAGE_ORDER
from tests.helpers import SAMPLES, make_config


def prepared_context(name: str, overrides: Optional[Dict[str, Any]] = None) -> StageContext:
    """Run input_validation + design_prep on a sample and return the context."""
    ctx = StageContext(make_config(overrides), SAMPLES / name)
    InputValidationStage().run(ctx)
    DesignPrepStage().run(ctx)
    return ctx


class StageTests(unittest.TestCase):
    def test_registry_matches_constants(self) -> None:
        self.assertEqual(tuple(STAGE_REGISTRY), STAGE_ORDER)

    def test_create_unknown_stage(self) -> None:
        with self.assertRaises(EdaSimError):
            create_stage("synthesis")

    def test_strip_comments(self) -> None:
        text = "a // x\n/* b\n c */ d"
        self.assertEqual(strip_comments(text), "a \n\n d")

    def test_design_prep_counts(self) -> None:
        ctx = prepared_context("alu.v")
        self.assertEqual(ctx.state["modules"], ["counter", "alu"])
        self.assertEqual(ctx.state["counts"]["assign_statements"], 1)
        self.assertEqual(ctx.state["counts"]["always_blocks"], 1)

    def test_design_prep_unbalanced(self) -> None:
        ctx = StageContext(make_config(), SAMPLES / "broken_unbalanced.v")
        InputValidationStage().run(ctx)
        with self.assertRaisesRegex(StageError, "Unbalanced"):
            DesignPrepStage().run(ctx)

    def test_design_prep_commented_module_is_ignored(self) -> None:
        ctx = StageContext(make_config(), SAMPLES / "counter.v")
        ctx.state["source"] = "// module fake\n"
        with self.assertRaisesRegex(StageError, "No 'module'"):
            DesignPrepStage().run(ctx)

    def test_design_prep_duplicate_modules(self) -> None:
        ctx = StageContext(make_config(), SAMPLES / "counter.v")
        ctx.state["source"] = "module a; endmodule\nmodule a; endmodule\n"
        with self.assertRaisesRegex(StageError, "Duplicate"):
            DesignPrepStage().run(ctx)

    def test_stage_requires_earlier_stage(self) -> None:
        ctx = StageContext(make_config(), SAMPLES / "counter.v")
        with self.assertRaisesRegex(StageError, "must run first"):
            ElaborationStage().run(ctx)

    def test_elaboration_resolves_instance(self) -> None:
        ctx = prepared_context("alu.v")
        out = ElaborationStage().run(ctx)
        self.assertEqual(out.metrics["instances"], 1)

    def test_elaboration_no_false_positives_on_counter(self) -> None:
        ctx = prepared_context("counter.v")
        self.assertEqual(ElaborationStage().run(ctx).metrics["instances"], 0)

    def test_elaboration_unresolved(self) -> None:
        ctx = prepared_context("broken_missing_module.v")
        with self.assertRaisesRegex(StageError, "fast_multiplier"):
            ElaborationStage().run(ctx)

    def test_lint_clean(self) -> None:
        out = LintStage().run(prepared_context("counter.v"))
        self.assertEqual(out.metrics["warnings"], 0)

    def test_lint_over_limit(self) -> None:
        with self.assertRaisesRegex(StageError, "exceed limit"):
            LintStage().run(prepared_context("messy_style.v"))

    def test_lint_within_raised_limit(self) -> None:
        ctx = prepared_context("messy_style.v", {"lint": {"max_warnings": 6}})
        self.assertEqual(LintStage().run(ctx).metrics["warnings"], 6)

    def test_simulation_pass(self) -> None:
        out = SimulationStage().run(prepared_context("counter.v"))
        self.assertEqual(out.metrics["tests_total"], 5)
        self.assertEqual(out.metrics["tests_failed"], 0)

    def test_simulation_marker_fails(self) -> None:
        with self.assertRaisesRegex(StageError, "SIM_FAIL"):
            SimulationStage().run(prepared_context("sim_failure.v"))

    def test_simulation_is_deterministic(self) -> None:
        a = SimulationStage().run(prepared_context("counter.v")).metrics
        b = SimulationStage().run(prepared_context("counter.v")).metrics
        self.assertEqual(a, b)

    def test_simulation_seed_changes_coverage(self) -> None:
        a = SimulationStage().run(prepared_context("counter.v")).metrics["coverage_percent"]
        ctx = prepared_context("counter.v", {"simulation": {"seed": 7}})
        b = SimulationStage().run(ctx).metrics["coverage_percent"]
        self.assertNotEqual(a, b)

    def test_simulation_coverage_gate(self) -> None:
        ctx = prepared_context("counter.v", {"simulation": {"min_coverage_percent": 100.0}})
        with self.assertRaisesRegex(StageError, "Coverage"):
            SimulationStage().run(ctx)

    def test_timing_pass(self) -> None:
        out = TimingStage().run(prepared_context("counter.v"))
        self.assertGreater(out.metrics["slack_ns"], 0)

    def test_timing_violation_at_high_clock(self) -> None:
        ctx = prepared_context("counter.v", {"timing": {"target_clock_mhz": 5000.0}})
        with self.assertRaisesRegex(StageError, "Timing violated"):
            TimingStage().run(ctx)


class InputStageTests(unittest.TestCase):
    def test_input_stage_stores_source(self) -> None:
        ctx = StageContext(make_config(), SAMPLES / "counter.v")
        out = InputValidationStage().run(ctx)
        self.assertIn("source", ctx.state)
        self.assertGreater(out.metrics["bytes"], 0)

    def test_input_stage_missing_file(self) -> None:
        ctx = StageContext(make_config(), Path("missing.v"))
        with self.assertRaises(EdaSimError):
            InputValidationStage().run(ctx)


if __name__ == "__main__":
    unittest.main()
