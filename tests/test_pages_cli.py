import argparse
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from test_pages import run_main

from pages_cli import (
    add_common_args,
    emit_db_warnings,
    load_focus_entries,
    parse_dump_checked,
    validate_limits,
)
from pages_db import ParseResult, ParseStats


class TestPagesCLI(unittest.TestCase):
    def test_common_args_flags(self) -> None:
        parser = argparse.ArgumentParser(add_help=False)
        add_common_args(
            parser,
            prefix_default=None,
            case_default=None,
            prefix_help="prefix help",
            case_help="case help",
        )
        cases = [
            (["--input", "custom.out"], {"input": "custom.out"}),
            (["--pages", "custom.list"], {"pages": "custom.list"}),
            (["--prefix"], {"use_prefix": True}),
            (["--noprefix"], {"use_prefix": False}),
            (["--case"], {"case_sensitive": True}),
            (["--nocase"], {"case_sensitive": False}),
            (["--lines", "5"], {"lines": 5}),
            (["--bytes", "10"], {"max_bytes": 10}),
            (["--csv"], {"csv": True}),
            (["--permit"], {"permit": True}),
            (["--permit-header"], {"strict_header": False}),
            (["--permit-columns"], {"strict_columns": False}),
        ]
        for args, expected in cases:
            with self.subTest(args=args):
                parsed = parser.parse_args(args)
                for key, value in expected.items():
                    self.assertEqual(getattr(parsed, key), value)

    def test_limits_negative_lines(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            ok = validate_limits(-1, 0)
        self.assertFalse(ok)
        self.assertIn("--lines must be 0 or a positive integer", stderr.getvalue())

    def test_limits_negative_bytes(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            ok = validate_limits(0, -5)
        self.assertFalse(ok)
        self.assertIn("--bytes must be 0 or a positive integer", stderr.getvalue())

    def test_focus_entries_missing(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            entries = load_focus_entries(Path("missing.list"), True)
        self.assertIsNone(entries)
        self.assertIn("pages list file not found", stderr.getvalue())

    def test_focus_entries_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                entries = load_focus_entries(path, True)
            self.assertIsNone(entries)
            self.assertIn(f"pages list could not be read: {path}", stderr.getvalue())

    def test_parse_missing_input(self) -> None:
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

    def test_parse_directory_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
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
            self.assertIn(f"input file could not be read: {path}", stderr.getvalue())

    def test_parse_error(self) -> None:
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

    def test_db_warnings_strict(self) -> None:
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

    def test_db_warnings_permit(self) -> None:
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
