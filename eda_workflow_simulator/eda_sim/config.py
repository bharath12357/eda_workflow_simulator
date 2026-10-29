"""Configuration loading and validation.

The JSON config is merged on top of ``DEFAULT_CONFIG`` and every key,
type and range is checked. Unknown keys are rejected so typos such as
``"max_warnigs"`` are caught instead of silently ignored.
"""

from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from eda_sim.constants import FAILURE_MODES, LOG_LEVELS, STAGE_ORDER
from eda_sim.exceptions import ConfigError

DEFAULT_CONFIG: Dict[str, Any] = {
    "project_name": "eda_workflow_demo",
    "input": {"allowed_extensions": [".v", ".sv"], "max_file_size_kb": 256},
    "output": {"report_dir": "reports", "log_dir": "logs"},
    "logging": {"level": "INFO"},
    "stages": list(STAGE_ORDER),
    "retry": {"max_attempts": 2},
    "simulated_delay_ms": 100,
    "lint": {"max_warnings": 5, "max_line_length": 100},
    "simulation": {"seed": 42, "tests_per_module": 5, "min_coverage_percent": 70.0},
    "timing": {"target_clock_mhz": 500.0, "min_slack_ns": 0.0},
    "failure_simulation": {
        "enabled": False,
        "stage": None,
        "mode": "error",
        "fail_attempts": 1,
    },
}


@dataclass(frozen=True)
class InputSettings:
    allowed_extensions: Tuple[str, ...]
    max_file_size_kb: int


@dataclass(frozen=True)
class OutputSettings:
    report_dir: str
    log_dir: str


@dataclass(frozen=True)
class RetrySettings:
    max_attempts: int


@dataclass(frozen=True)
class LintSettings:
    max_warnings: int
    max_line_length: int


@dataclass(frozen=True)
class SimulationSettings:
    seed: int
    tests_per_module: int
    min_coverage_percent: float


@dataclass(frozen=True)
class TimingSettings:
    target_clock_mhz: float
    min_slack_ns: float


@dataclass(frozen=True)
class FailureSettings:
    enabled: bool
    stage: Optional[str]
    mode: str
    fail_attempts: int


@dataclass(frozen=True)
class Config:
    """Validated, immutable configuration for one workflow run."""

    project_name: str
    input: InputSettings
    output: OutputSettings
    log_level: str
    stages: Tuple[str, ...]
    retry: RetrySettings
    simulated_delay_ms: int
    lint: LintSettings
    simulation: SimulationSettings
    timing: TimingSettings
    failure: FailureSettings

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-friendly dict with the same shape as the config file."""
        data: Dict[str, Any] = {
            "project_name": self.project_name,
            "input": asdict(self.input),
            "output": asdict(self.output),
            "logging": {"level": self.log_level},
            "stages": list(self.stages),
            "retry": asdict(self.retry),
            "simulated_delay_ms": self.simulated_delay_ms,
            "lint": asdict(self.lint),
            "simulation": asdict(self.simulation),
            "timing": asdict(self.timing),
            "failure_simulation": asdict(self.failure),
        }
        # Round-trip through JSON so tuples become lists.
        return json.loads(json.dumps(data))


# --------------------------------------------------------------------------
# Small typed helpers
# --------------------------------------------------------------------------
def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    """Return ``base`` with ``override`` applied recursively (inputs untouched)."""
    result = copy.deepcopy(dict(base))
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _section(data: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = data[name]
    if not isinstance(value, Mapping):
        raise ConfigError(f"'{name}' must be an object, got {type(value).__name__}")
    allowed = set(DEFAULT_CONFIG[name])
    unknown = set(value) - allowed
    if unknown:
        raise ConfigError(
            f"Unknown key(s) in '{name}': {sorted(unknown)}. Allowed: {sorted(allowed)}"
        )
    return value


def _get_int(sec: Mapping[str, Any], key: str, label: str, low: int, high: int = 10**9) -> int:
    value = sec[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"'{label}' must be an integer, got {value!r}")
    if not low <= value <= high:
        raise ConfigError(f"'{label}' must be between {low} and {high}, got {value}")
    return value


def _get_num(sec: Mapping[str, Any], key: str, label: str, low: float, high: float) -> float:
    value = sec[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"'{label}' must be a number, got {value!r}")
    if not low <= value <= high:
        raise ConfigError(f"'{label}' must be between {low} and {high}, got {value}")
    return float(value)


def _get_str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"'{label}' must be a non-empty string, got {value!r}")
    return value


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------
def parse_config(user_data: Mapping[str, Any]) -> Config:
    """Validate ``user_data`` (merged over the defaults) and build a ``Config``."""
    if not isinstance(user_data, Mapping):
        raise ConfigError("Config root must be a JSON object")
    unknown_top = set(user_data) - set(DEFAULT_CONFIG)
    if unknown_top:
        raise ConfigError(
            f"Unknown top-level key(s): {sorted(unknown_top)}. "
            f"Allowed: {sorted(DEFAULT_CONFIG)}"
        )
    data = _deep_merge(DEFAULT_CONFIG, user_data)

    project_name = _get_str(data["project_name"], "project_name")

    sec = _section(data, "input")
    exts = sec["allowed_extensions"]
    if not isinstance(exts, list) or not exts:
        raise ConfigError("'input.allowed_extensions' must be a non-empty list")
    clean_exts: List[str] = []
    for ext in exts:
        ext_s = _get_str(ext, "input.allowed_extensions[]")
        if not ext_s.startswith("."):
            raise ConfigError(f"Extension {ext_s!r} must start with '.' (e.g. '.v')")
        clean_exts.append(ext_s.lower())
    input_settings = InputSettings(
        tuple(clean_exts), _get_int(sec, "max_file_size_kb", "input.max_file_size_kb", 1, 1_048_576)
    )

    sec = _section(data, "output")
    output_settings = OutputSettings(
        _get_str(sec["report_dir"], "output.report_dir"),
        _get_str(sec["log_dir"], "output.log_dir"),
    )

    sec = _section(data, "logging")
    level = _get_str(sec["level"], "logging.level").upper()
    if level not in LOG_LEVELS:
        raise ConfigError(f"'logging.level' must be one of {list(LOG_LEVELS)}, got {level!r}")

    stages = data["stages"]
    if not isinstance(stages, list) or not stages:
        raise ConfigError("'stages' must be a non-empty list")
    for name in stages:
        if name not in STAGE_ORDER:
            raise ConfigError(f"Unknown stage {name!r}. Valid stages: {list(STAGE_ORDER)}")
    if len(set(stages)) != len(stages):
        raise ConfigError("'stages' contains duplicates")
    indexes = [STAGE_ORDER.index(s) for s in stages]
    if indexes != sorted(indexes):
        raise ConfigError(f"'stages' must follow the order {list(STAGE_ORDER)}")

    sec = _section(data, "retry")
    retry = RetrySettings(_get_int(sec, "max_attempts", "retry.max_attempts", 1, 10))

    delay = _get_int(data, "simulated_delay_ms", "simulated_delay_ms", 0, 60_000)

    sec = _section(data, "lint")
    lint = LintSettings(
        _get_int(sec, "max_warnings", "lint.max_warnings", 0, 100_000),
        _get_int(sec, "max_line_length", "lint.max_line_length", 20, 1000),
    )

    sec = _section(data, "simulation")
    simulation = SimulationSettings(
        _get_int(sec, "seed", "simulation.seed", 0, 2**31 - 1),
        _get_int(sec, "tests_per_module", "simulation.tests_per_module", 1, 10_000),
        _get_num(sec, "min_coverage_percent", "simulation.min_coverage_percent", 0.0, 100.0),
    )

    sec = _section(data, "timing")
    timing = TimingSettings(
        _get_num(sec, "target_clock_mhz", "timing.target_clock_mhz", 1.0, 100_000.0),
        _get_num(sec, "min_slack_ns", "timing.min_slack_ns", -1000.0, 1000.0),
    )

    sec = _section(data, "failure_simulation")
    enabled = sec["enabled"]
    if not isinstance(enabled, bool):
        raise ConfigError(f"'failure_simulation.enabled' must be true/false, got {enabled!r}")
    fail_stage = sec["stage"]
    mode = sec["mode"]
    if mode not in FAILURE_MODES:
        raise ConfigError(
            f"'failure_simulation.mode' must be one of {list(FAILURE_MODES)}, got {mode!r}"
        )
    fail_attempts = _get_int(sec, "fail_attempts", "failure_simulation.fail_attempts", 1, 10)
    if enabled:
        if fail_stage not in stages:
            raise ConfigError(
                f"'failure_simulation.stage' must be one of the enabled stages {stages}, "
                f"got {fail_stage!r}"
            )
    elif fail_stage is not None and fail_stage not in STAGE_ORDER:
        raise ConfigError(f"'failure_simulation.stage' is not a known stage: {fail_stage!r}")
    failure = FailureSettings(enabled, fail_stage, mode, fail_attempts)

    return Config(
        project_name=project_name,
        input=input_settings,
        output=output_settings,
        log_level=level,
        stages=tuple(stages),
        retry=retry,
        simulated_delay_ms=delay,
        lint=lint,
        simulation=simulation,
        timing=timing,
        failure=failure,
    )


def default_config() -> Config:
    """Return the built-in default configuration."""
    return parse_config({})


def load_config(path: Optional[Path] = None) -> Config:
    """Load a JSON config file (or the defaults when ``path`` is ``None``)."""
    if path is None:
        return default_config()
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Config file {path} is not valid JSON: {exc}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"Cannot read config file {path}: {exc}") from exc
    return parse_config(data)
