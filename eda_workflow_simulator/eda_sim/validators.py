"""Input file validation (the gate in front of the workflow)."""

from __future__ import annotations

from pathlib import Path

from eda_sim.config import Config
from eda_sim.exceptions import InputValidationError


def validate_input_file(path: Path, config: Config) -> str:
    """Validate a design file and return its text.

    Checks, in order: exists, is a regular file, allowed extension,
    non-empty, below the size limit, no NUL bytes, valid UTF-8.

    Raises:
        InputValidationError: with a beginner-friendly message.
    """
    path = Path(path)
    if not path.exists():
        raise InputValidationError(f"Input file not found: {path}")
    if not path.is_file():
        raise InputValidationError(f"Input path is not a file: {path}")

    suffix = path.suffix.lower()
    if suffix not in config.input.allowed_extensions:
        raise InputValidationError(
            f"Unsupported extension {suffix!r} for {path.name}. "
            f"Allowed: {list(config.input.allowed_extensions)}"
        )

    try:
        size_bytes = path.stat().st_size
        raw = path.read_bytes()
    except OSError as exc:
        raise InputValidationError(f"Cannot read {path}: {exc}") from exc

    if size_bytes == 0:
        raise InputValidationError(f"Input file is empty: {path.name}")
    limit = config.input.max_file_size_kb * 1024
    if size_bytes > limit:
        raise InputValidationError(
            f"{path.name} is {size_bytes} bytes; limit is {limit} bytes "
            f"({config.input.max_file_size_kb} KB)"
        )
    if b"\x00" in raw:
        raise InputValidationError(f"{path.name} contains NUL bytes (looks binary)")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InputValidationError(f"{path.name} is not valid UTF-8: {exc}") from exc
