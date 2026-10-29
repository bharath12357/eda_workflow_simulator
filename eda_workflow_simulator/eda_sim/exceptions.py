"""Custom exception hierarchy.

Using our own exception types lets the pipeline distinguish *expected*
failures (bad input, a failing check) from *unexpected* bugs.
"""

from __future__ import annotations


class EdaSimError(Exception):
    """Base class for every error raised on purpose by this project."""


class ConfigError(EdaSimError):
    """The configuration file or an override is invalid."""


class InputValidationError(EdaSimError):
    """The design input file failed validation."""


class StageError(EdaSimError):
    """A workflow stage found a problem (a normal, expected failure)."""


class SimulatedTimeoutError(StageError):
    """A transient failure. The pipeline may retry the stage."""
