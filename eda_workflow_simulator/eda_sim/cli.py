"""Command-line interface (argparse).

Exit codes: 0 = success, 1 = workflow/validation failed, 2 = usage or config error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from eda_sim import __version__
from eda_sim.config import Config, load_config, parse_config
from eda_sim.constants import (
    EXIT_OK,
    EXIT_USAGE_ERROR,
    EXIT_WORKFLOW_FAILED,
    FAILURE_MODES,
    LOG_LEVELS,
    STAGE_ORDER,
    STATUS_PASSED,
)
from eda_sim.exceptions import ConfigError, EdaSimError, InputValidationError
from eda_sim.logger_setup import setup_logging, shutdown_logging
from eda_sim.pipeline import Pipeline, make_run_id, utc_now
from eda_sim.report import format_summary, load_report, write_report
from eda_sim.stages import STAGE_REGISTRY
from eda_sim.validators import validate_input_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eda_sim",
        description="EDA Workflow Automation Simulator (educational; not a real EDA tool).",
    )
    parser.add_argument("--version", action="version", version=f"eda_sim {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run the full simulated workflow on a design file")
    run.add_argument("design", type=Path, help="path to a .v or .sv file")
    run.add_argument("--config", type=Path, help="JSON config file (default: built-in defaults)")
    run.add_argument("--report-dir", type=Path, help="override output.report_dir")
    run.add_argument("--log-dir", type=Path, help="override output.log_dir")
    run.add_argument("--log-level", choices=LOG_LEVELS, help="override logging.level")
    run.add_argument("--delay-ms", type=int, help="override simulated_delay_ms")
    run.add_argument("--target-mhz", type=float, help="override timing.target_clock_mhz")
    run.add_argument("--inject-failure", choices=STAGE_ORDER, metavar="STAGE",
                     help=f"force a failure in a stage: {', '.join(STAGE_ORDER)}")
    run.add_argument("--failure-mode", choices=FAILURE_MODES, help="error | timeout | crash")
    run.add_argument("--fail-attempts", type=int,
                     help="for timeout mode: how many attempts fail before success")
    run.add_argument("--quiet", action="store_true", help="log to file only (no console logs)")

    vc = sub.add_parser("validate-config", help="check a config file")
    vc.add_argument("config", type=Path)

    vi = sub.add_parser("validate-input", help="check a design file only")
    vi.add_argument("design", type=Path)
    vi.add_argument("--config", type=Path)

    sub.add_parser("list-stages", help="show the stages and what they do")

    sr = sub.add_parser("show-report", help="print a summary of a JSON report")
    sr.add_argument("report", type=Path)
    return parser


def apply_overrides(config: Config, args: argparse.Namespace) -> Config:
    """Apply CLI flags on top of the config, re-validating everything."""
    data = config.to_dict()
    if args.report_dir is not None:
        data["output"]["report_dir"] = str(args.report_dir)
    if args.log_dir is not None:
        data["output"]["log_dir"] = str(args.log_dir)
    if args.log_level is not None:
        data["logging"]["level"] = args.log_level
    if args.delay_ms is not None:
        data["simulated_delay_ms"] = args.delay_ms
    if args.target_mhz is not None:
        data["timing"]["target_clock_mhz"] = args.target_mhz
    if args.inject_failure is not None:
        data["failure_simulation"]["enabled"] = True
        data["failure_simulation"]["stage"] = args.inject_failure
    if args.failure_mode is not None:
        data["failure_simulation"]["mode"] = args.failure_mode
    if args.fail_attempts is not None:
        data["failure_simulation"]["fail_attempts"] = args.fail_attempts
    if (args.failure_mode or args.fail_attempts) and args.inject_failure is None:
        raise ConfigError("--failure-mode/--fail-attempts need --inject-failure STAGE")
    return parse_config(data)


def _cmd_run(args: argparse.Namespace) -> int:
    config = apply_overrides(load_config(args.config), args)
    moment = utc_now()
    run_id = make_run_id(moment)
    logger, log_path = setup_logging(
        Path(config.output.log_dir), run_id, config.log_level, console=not args.quiet
    )
    try:
        report = Pipeline(config, logger, run_id=run_id).run(args.design)
        report_path = write_report(report, Path(config.output.report_dir))
    finally:
        shutdown_logging(logger)
    print()
    print(format_summary(report.to_dict()))
    print(f"\nReport: {report_path}\nLog   : {log_path}")
    return EXIT_OK if report.status == STATUS_PASSED else EXIT_WORKFLOW_FAILED


def _cmd_validate_config(args: argparse.Namespace) -> int:
    load_config(args.config)
    print(f"OK: {args.config} is a valid configuration")
    return EXIT_OK


def _cmd_validate_input(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    try:
        validate_input_file(args.design, config)
    except InputValidationError as exc:
        print(f"INVALID: {exc}")
        return EXIT_WORKFLOW_FAILED
    print(f"OK: {args.design} passed input validation")
    return EXIT_OK


def _cmd_list_stages(_: argparse.Namespace) -> int:
    for index, name in enumerate(STAGE_ORDER, start=1):
        print(f"{index}. {name:<17} {STAGE_REGISTRY[name].description}")
    return EXIT_OK


def _cmd_show_report(args: argparse.Namespace) -> int:
    print(format_summary(load_report(args.report)))
    return EXIT_OK


_COMMANDS = {
    "run": _cmd_run,
    "validate-config": _cmd_validate_config,
    "validate-input": _cmd_validate_input,
    "list-stages": _cmd_list_stages,
    "show-report": _cmd_show_report,
}


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point. Returns an exit code instead of calling ``sys.exit``."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # argparse exits on --help or bad usage
        return int(exc.code) if isinstance(exc.code, int) else EXIT_USAGE_ERROR
    try:
        return _COMMANDS[args.command](args)
    except EdaSimError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_USAGE_ERROR
    except OSError as exc:
        print(f"ERROR: file system problem: {exc}", file=sys.stderr)
        return EXIT_USAGE_ERROR
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
