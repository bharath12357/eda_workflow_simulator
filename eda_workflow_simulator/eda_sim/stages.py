"""Simulated workflow stages.

Each stage is a small class with a ``run`` method. Stages share data
through a ``StageContext`` (for example ``design_prep`` stores the module
list that ``elaboration`` later reads). A stage signals a normal failure
by raising ``StageError``.

IMPORTANT: these are educational checks on Verilog-looking text. They are
not real parsing, synthesis, simulation or timing analysis.
"""

from __future__ import annotations

import random
import re
import zlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from eda_sim.config import Config
from eda_sim.constants import STAGE_ORDER
from eda_sim.exceptions import EdaSimError, StageError
from eda_sim.validators import validate_input_file

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"//[^\n]*")
_MODULE_DECL = re.compile(r"^\s*module\s+([A-Za-z_]\w*)", re.MULTILINE)
_ENDMODULE = re.compile(r"\bendmodule\b")
_ASSIGN = re.compile(r"\bassign\b")
_ALWAYS = re.compile(r"\balways(?:_ff|_comb|_latch)?\b")
_INSTANCE = re.compile(
    r"^\s*([A-Za-z_]\w*)\s+(?:#\s*\([^)]*\)\s*)?([A-Za-z_]\w*)\s*\(", re.MULTILINE
)
_KEYWORDS = frozenset(
    """module endmodule input output inout wire reg logic assign always initial
    if else case casez casex for while function task integer parameter localparam
    begin end posedge negedge generate genvar endcase return automatic""".split()
)


def strip_comments(text: str) -> str:
    """Remove ``/* */`` and ``//`` comments (line breaks inside blocks are kept)."""
    no_block = _BLOCK_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return _LINE_COMMENT.sub("", no_block)


@dataclass
class StageContext:
    """Data shared by all stages during one run."""

    config: Config
    design_path: Path
    state: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StageOutput:
    """What a successful stage returns."""

    messages: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


class Stage(ABC):
    """Base class for all stages."""

    name: str = ""
    description: str = ""

    @abstractmethod
    def run(self, ctx: StageContext) -> StageOutput:
        """Execute the stage. Raise ``StageError`` on a normal failure."""


def _require(ctx: StageContext, key: str, producer: str) -> Any:
    """Fetch shared state or fail with a clear message about stage ordering."""
    if key not in ctx.state:
        raise StageError(f"Missing '{key}'. The '{producer}' stage must run first.")
    return ctx.state[key]


def _seeded_rng(ctx: StageContext, label: str) -> random.Random:
    """Deterministic RNG: same seed + same file text -> same numbers."""
    digest = zlib.crc32(_require(ctx, "source", "input_validation").encode("utf-8"))
    return random.Random(f"{label}:{ctx.config.simulation.seed}:{digest}")


class InputValidationStage(Stage):
    name = "input_validation"
    description = "Check the file exists, has an allowed extension, size and encoding."

    def run(self, ctx: StageContext) -> StageOutput:
        text = validate_input_file(ctx.design_path, ctx.config)
        ctx.state["source"] = text
        lines = text.count("\n") + 1
        return StageOutput(
            [f"{ctx.design_path.name} accepted"],
            {"bytes": len(text.encode("utf-8")), "lines": lines},
        )


class DesignPrepStage(Stage):
    name = "design_prep"
    description = "Strip comments, find modules, check module/endmodule balance."

    def run(self, ctx: StageContext) -> StageOutput:
        source = _require(ctx, "source", "input_validation")
        clean = strip_comments(source)
        modules = _MODULE_DECL.findall(clean)
        ends = len(_ENDMODULE.findall(clean))
        if not modules:
            raise StageError("No 'module' declaration found")
        if len(modules) != ends:
            raise StageError(
                f"Unbalanced design: {len(modules)} 'module' vs {ends} 'endmodule'"
            )
        duplicates = sorted({m for m in modules if modules.count(m) > 1})
        if duplicates:
            raise StageError(f"Duplicate module name(s): {duplicates}")
        ctx.state["clean"] = clean
        ctx.state["modules"] = modules
        counts = {
            "modules": len(modules),
            "assign_statements": len(_ASSIGN.findall(clean)),
            "always_blocks": len(_ALWAYS.findall(clean)),
        }
        ctx.state["counts"] = counts
        return StageOutput([f"Found modules: {', '.join(modules)}"], counts)


class ElaborationStage(Stage):
    name = "elaboration"
    description = "Check that every instantiated module is defined."

    def run(self, ctx: StageContext) -> StageOutput:
        clean = _require(ctx, "clean", "design_prep")
        modules = _require(ctx, "modules", "design_prep")
        defined = set(modules)
        instances = [
            (mod, inst)
            for mod, inst in _INSTANCE.findall(clean)
            if mod not in _KEYWORDS
        ]
        unresolved = sorted({mod for mod, _ in instances if mod not in defined})
        if unresolved:
            raise StageError(f"Unresolved module reference(s): {unresolved}")
        return StageOutput(
            [f"{len(instances)} instance(s) resolved"], {"instances": len(instances)}
        )


class LintStage(Stage):
    name = "lint"
    description = "Style checks: tabs, trailing spaces, long lines, TODO/FIXME."

    def run(self, ctx: StageContext) -> StageOutput:
        source = _require(ctx, "source", "input_validation")
        cfg = ctx.config.lint
        warnings: List[str] = []
        for number, line in enumerate(source.splitlines(), start=1):
            if "\t" in line:
                warnings.append(f"line {number}: tab character")
            if line != line.rstrip():
                warnings.append(f"line {number}: trailing whitespace")
            if len(line) > cfg.max_line_length:
                warnings.append(
                    f"line {number}: {len(line)} chars (max {cfg.max_line_length})"
                )
            if re.search(r"\b(TODO|FIXME)\b", line):
                warnings.append(f"line {number}: TODO/FIXME marker")
        metrics = {
            "warnings": len(warnings),
            "max_warnings": cfg.max_warnings,
            "first_warnings": warnings[:10],
        }
        if len(warnings) > cfg.max_warnings:
            raise StageError(
                f"{len(warnings)} lint warning(s) exceed limit of {cfg.max_warnings}; "
                f"first: {warnings[0]}"
            )
        return StageOutput([f"{len(warnings)} lint warning(s)"], metrics)


class SimulationStage(Stage):
    name = "simulation"
    description = "Simulated test run. A '// SIM_FAIL' marker forces a failing test."

    def run(self, ctx: StageContext) -> StageOutput:
        source = _require(ctx, "source", "input_validation")
        modules = _require(ctx, "modules", "design_prep")
        cfg = ctx.config.simulation
        total = cfg.tests_per_module * len(modules)
        failed = min(total, source.count("SIM_FAIL"))
        rng = _seeded_rng(ctx, "simulation")
        coverage = round(75.0 + rng.random() * 25.0, 1)
        metrics = {
            "tests_total": total,
            "tests_failed": failed,
            "tests_passed": total - failed,
            "coverage_percent": coverage,
            "min_coverage_percent": cfg.min_coverage_percent,
            "seed": cfg.seed,
        }
        if failed:
            raise StageError(f"{failed} of {total} simulated test(s) failed (SIM_FAIL marker)")
        if coverage < cfg.min_coverage_percent:
            raise StageError(
                f"Coverage {coverage}% is below required {cfg.min_coverage_percent}%"
            )
        return StageOutput([f"{total} test(s) passed, coverage {coverage}%"], metrics)


class TimingStage(Stage):
    name = "timing"
    description = "Estimated critical path vs. target clock period (slack check)."

    def run(self, ctx: StageContext) -> StageOutput:
        counts = _require(ctx, "counts", "design_prep")
        cfg = ctx.config.timing
        rng = _seeded_rng(ctx, "timing")
        path_ns = (
            0.5
            + 0.12 * counts["assign_statements"]
            + 0.20 * counts["always_blocks"]
            + rng.random() * 0.15
        )
        period_ns = 1000.0 / cfg.target_clock_mhz
        slack = period_ns - path_ns
        metrics = {
            "critical_path_ns": round(path_ns, 3),
            "target_period_ns": round(period_ns, 3),
            "slack_ns": round(slack, 3),
            "min_slack_ns": cfg.min_slack_ns,
            "max_frequency_mhz": round(1000.0 / path_ns, 1),
        }
        if slack < cfg.min_slack_ns:
            raise StageError(
                f"Timing violated: slack {slack:.3f} ns < required {cfg.min_slack_ns} ns "
                f"at {cfg.target_clock_mhz} MHz"
            )
        return StageOutput([f"Timing met, slack {slack:.3f} ns"], metrics)


_STAGE_CLASSES = (
    InputValidationStage,
    DesignPrepStage,
    ElaborationStage,
    LintStage,
    SimulationStage,
    TimingStage,
)
STAGE_REGISTRY: Dict[str, type] = {cls.name: cls for cls in _STAGE_CLASSES}

# Guard against the registry and the constants drifting apart.
assert tuple(STAGE_REGISTRY) == STAGE_ORDER, "STAGE_REGISTRY must match STAGE_ORDER"


def create_stage(name: str) -> Stage:
    """Instantiate a stage by name."""
    try:
        return STAGE_REGISTRY[name]()
    except KeyError:
        raise EdaSimError(f"Unknown stage {name!r}") from None
