import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from test_pages import run_main

from pages_cli import (
    emit_db_warnings,
    load_focus_list_checked,
    parse_dump_checked,
    validate_limits,
)
from pages_db import ParseResult, ParseStats


class TestPagesCLI(unittest.TestCase):
    def test_validate_limits_negative_lines(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            ok = validate_limits(-1, 0)
        self.assertFalse(ok)
        self.assertIn("--lines must be 0 or a positive integer", stderr.getvalue())

    def test_validate_limits_negative_bytes(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            ok = validate_limits(0, -5)
        self.assertFalse(ok)
        self.assertIn("--bytes must be 0 or a positive integer", stderr.getvalue())

    def test_load_focus_list_checked_missing(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            entries = load_focus_list_checked(Path("missing.list"), True)
        self.assertIsNone(entries)
        self.assertIn("pages list file not found", stderr.getvalue())

    def test_parse_dump_checked_missing_input(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = parse_dump_checked(
                Path("missing.out"),
                max_lines=0,
                max_bytes=0,
                use_csv=False,
                include_content=False,
            )
        self.assertIsNone(result)
        self.assertIn("input file not found", stderr.getvalue())

    def test_parse_dump_checked_parse_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.out"
            path.write_text("", encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                result = parse_dump_checked(
                    path,
                    max_lines=0,
                    max_bytes=0,
                    use_csv=False,
                    include_content=False,
                )
            self.assertIsNone(result)
            self.assertIn("Empty input file", stderr.getvalue())

    def test_emit_db_warnings_strict(self) -> None:
        stats = ParseStats(
            skipped_malformed=2,
            skipped_oversized=1,
            header_mismatch=True,
            header_columns=["bad"],
            invalid_id_count=1,
        )
        result = ParseResult(rows=[], stats=stats)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            emit_db_warnings(
                result,
                Path("db.out"),
                strict_header=True,
                strict_columns=True,
            )
        output = stderr.getvalue()
        self.assertIn("Oversized line count: 1", output)
        self.assertNotIn("Malformed row count", output)
        self.assertNotIn("Header error", output)
        self.assertIn("Invalid id count: 1", output)

    def test_emit_db_warnings_non_strict(self) -> None:
        stats = ParseStats(
            skipped_malformed=2,
            skipped_oversized=1,
            header_mismatch=True,
            header_columns=["bad"],
            invalid_id_count=1,
        )
        result = ParseResult(rows=[], stats=stats)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            emit_db_warnings(
                result,
                Path("db.out"),
                strict_header=False,
                strict_columns=False,
            )
        output = stderr.getvalue()
        self.assertIn("Oversized line count: 1", output)
        self.assertIn("Malformed row count: 2", output)
        self.assertIn("Header error in", output)
        self.assertIn("Invalid id count: 1", output)


if __name__ == "__main__":
    run_main()
