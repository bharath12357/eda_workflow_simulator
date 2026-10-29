"""Tests for eda_sim.config."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from eda_sim.config import DEFAULT_CONFIG, default_config, load_config, parse_config
from eda_sim.exceptions import ConfigError
from tests.helpers import PROJECT_ROOT


class ConfigTests(unittest.TestCase):
    def test_defaults_are_valid(self) -> None:
        cfg = default_config()
        self.assertEqual(cfg.retry.max_attempts, 2)
        self.assertEqual(cfg.stages[0], "input_validation")

    def test_default_file_matches_builtin_defaults(self) -> None:
        on_disk = json.loads((PROJECT_ROOT / "config" / "default_config.json").read_text())
        self.assertEqual(on_disk, DEFAULT_CONFIG)

    def test_strict_config_file_is_valid(self) -> None:
        cfg = load_config(PROJECT_ROOT / "config" / "strict_config.json")
        self.assertEqual(cfg.simulation.min_coverage_percent, 95.0)

    def test_bad_config_file_is_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            load_config(PROJECT_ROOT / "config" / "bad_config.json")

    def test_to_dict_round_trips(self) -> None:
        cfg = default_config()
        self.assertEqual(parse_config(cfg.to_dict()), cfg)

    def test_partial_override_keeps_other_defaults(self) -> None:
        cfg = parse_config({"lint": {"max_warnings": 9}})
        self.assertEqual(cfg.lint.max_warnings, 9)
        self.assertEqual(cfg.lint.max_line_length, 100)

    def test_unknown_top_level_key(self) -> None:
        with self.assertRaisesRegex(ConfigError, "Unknown top-level"):
            parse_config({"colour": "red"})

    def test_unknown_nested_key(self) -> None:
        with self.assertRaisesRegex(ConfigError, "Unknown key"):
            parse_config({"lint": {"max_warnigs": 3}})

    def test_wrong_type(self) -> None:
        with self.assertRaisesRegex(ConfigError, "integer"):
            parse_config({"retry": {"max_attempts": "two"}})

    def test_bool_is_not_an_integer(self) -> None:
        with self.assertRaises(ConfigError):
            parse_config({"retry": {"max_attempts": True}})

    def test_out_of_range(self) -> None:
        with self.assertRaisesRegex(ConfigError, "between"):
            parse_config({"retry": {"max_attempts": 0}})

    def test_bad_log_level(self) -> None:
        with self.assertRaisesRegex(ConfigError, "logging.level"):
            parse_config({"logging": {"level": "LOUD"}})

    def test_extension_must_start_with_dot(self) -> None:
        with self.assertRaisesRegex(ConfigError, "start with"):
            parse_config({"input": {"allowed_extensions": ["v"]}})

    def test_unknown_stage(self) -> None:
        with self.assertRaisesRegex(ConfigError, "Unknown stage"):
            parse_config({"stages": ["input_validation", "synthesis"]})

    def test_stage_order_enforced(self) -> None:
        with self.assertRaisesRegex(ConfigError, "order"):
            parse_config({"stages": ["lint", "design_prep"]})

    def test_duplicate_stages(self) -> None:
        with self.assertRaisesRegex(ConfigError, "duplicates"):
            parse_config({"stages": ["lint", "lint"]})

    def test_failure_stage_must_be_enabled_stage(self) -> None:
        with self.assertRaisesRegex(ConfigError, "failure_simulation.stage"):
            parse_config(
                {
                    "stages": ["input_validation", "design_prep"],
                    "failure_simulation": {"enabled": True, "stage": "timing"},
                }
            )

    def test_bad_failure_mode(self) -> None:
        with self.assertRaisesRegex(ConfigError, "mode"):
            parse_config({"failure_simulation": {"mode": "explode"}})

    def test_root_must_be_object(self) -> None:
        with self.assertRaises(ConfigError):
            parse_config([1, 2, 3])  # type: ignore[arg-type]

    def test_missing_file(self) -> None:
        with self.assertRaisesRegex(ConfigError, "not found"):
            load_config(Path("no_such_config.json"))

    def test_invalid_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.json"
            path.write_text("{ not json", encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "not valid JSON"):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
