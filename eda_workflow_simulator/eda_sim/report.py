"""JSON report writing (atomic) and reading/summarising."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict

from eda_sim.exceptions import EdaSimError
from eda_sim.models import WorkflowReport

_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]+")
_REQUIRED_KEYS = ("run_id", "design_file", "status", "started_at", "stages", "summary")


def safe_filename(text: str) -> str:
    """Replace anything but letters, digits, ``_ . -`` so the name is Windows-safe."""
    cleaned = _UNSAFE.sub("_", text).strip("._")
    return cleaned or "report"


def write_report(report: WorkflowReport, report_dir: Path) -> Path:
    """Write ``report`` as JSON and return its path.

    The data goes to a temporary file in the same folder first and is then
    moved into place with ``os.replace`` so a crash can never leave a
    half-written report behind.
    """
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    stem = safe_filename(Path(report.design_file).stem)
    target = report_dir / f"report_{stem}_{report.run_id}.json"

    fd, tmp_name = tempfile.mkstemp(prefix=".tmp_report_", suffix=".json", dir=report_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(report.to_dict(), handle, indent=2)
            handle.write("\n")
        os.replace(tmp_name, target)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
    return target


def load_report(path: Path) -> Dict[str, Any]:
    """Read a report JSON file and check it has the expected top-level keys."""
    path = Path(path)
    if not path.is_file():
        raise EdaSimError(f"Report not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        raise EdaSimError(f"Cannot read report {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise EdaSimError(f"Report {path} must contain a JSON object")
    missing = [key for key in _REQUIRED_KEYS if key not in data]
    if missing:
        raise EdaSimError(f"Report {path} is missing key(s): {missing}")
    return data


def format_summary(data: Dict[str, Any]) -> str:
    """Return a human-readable table for a report dictionary."""
    lines = [
        f"Run ID   : {data['run_id']}",
        f"Design   : {data['design_file']}",
        f"Status   : {data['status']}",
        f"Started  : {data['started_at']}",
        "",
        f"{'Stage':<18}{'Status':<9}{'Tries':<7}{'ms':>9}  Detail",
        "-" * 70,
    ]
    for stage in data["stages"]:
        detail = stage.get("error") or "; ".join(stage.get("messages", []))
        lines.append(
            f"{stage['name']:<18}{stage['status']:<9}{stage.get('attempts', 0):<7}"
            f"{stage.get('duration_ms', 0.0):>9.1f}  {detail}"
        )
    summary = data["summary"]
    lines.append("-" * 70)
    lines.append(
        f"passed={summary['stages_passed']} failed={summary['stages_failed']} "
        f"skipped={summary['stages_skipped']} total={summary['stages_total']}"
    )
    return "\n".join(lines)
