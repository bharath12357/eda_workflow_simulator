"""Tests for eda_sim.validators."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from eda_sim.exceptions import InputValidationError
from eda_sim.validators import validate_input_file
from tests.helpers import SAMPLES, make_config


class ValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.cfg = make_config()

    def _write(self, name: str, data: bytes) -> Path:
        path = self.tmp / name
        path.write_bytes(data)
        return path

    def test_valid_sample(self) -> None:
        text = validate_input_file(SAMPLES / "counter.v", self.cfg)
        self.assertIn("module counter", text)

    def test_missing_file(self) -> None:
        with self.assertRaisesRegex(InputValidationError, "not found"):
            validate_input_file(self.tmp / "nope.v", self.cfg)

    def test_directory(self) -> None:
        with self.assertRaisesRegex(InputValidationError, "not a file"):
            validate_input_file(self.tmp, self.cfg)

    def test_wrong_extension(self) -> None:
        path = self._write("design.txt", b"module a; endmodule")
        with self.assertRaisesRegex(InputValidationError, "Unsupported extension"):
            validate_input_file(path, self.cfg)

    def test_extension_check_is_case_insensitive(self) -> None:
        path = self._write("DESIGN.V", b"module a; endmodule")
        self.assertIn("module", validate_input_file(path, self.cfg))

    def test_empty_file(self) -> None:
        with self.assertRaisesRegex(InputValidationError, "empty"):
            validate_input_file(self._write("e.v", b""), self.cfg)

    def test_too_large(self) -> None:
        cfg = make_config({"input": {"max_file_size_kb": 1}})
        path = self._write("big.v", b"a" * 2048)
        with self.assertRaisesRegex(InputValidationError, "limit"):
            validate_input_file(path, cfg)

    def test_binary_nul(self) -> None:
        with self.assertRaisesRegex(InputValidationError, "NUL"):
            validate_input_file(self._write("b.v", b"module\x00a"), self.cfg)

    def test_not_utf8(self) -> None:
        with self.assertRaisesRegex(InputValidationError, "UTF-8"):
            validate_input_file(self._write("u.v", b"\xff\xfe\xfa"), self.cfg)


if __name__ == "__main__":
    unittest.main()
