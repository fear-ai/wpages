import contextlib
import io
import sys
import tempfile
import time
import unittest
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pages_cli import (
    emit_parse_warnings,
    load_focus_list_checked,
    parse_dump_checked,
    validate_limits,
)
from pages_db import ParseResult, ParseStats


class CompactResult(unittest.TextTestResult):
    def addSuccess(self, test) -> None:
        unittest.TestResult.addSuccess(self, test)
        if self.showAll:
            self.stream.writeln("ok")
        elif self.dots:
            self.stream.write("+")
            self.stream.flush()

    def addFailure(self, test, err) -> None:
        unittest.TestResult.addFailure(self, test, err)
        if self.showAll:
            self.stream.writeln("FAIL")
        elif self.dots:
            self.stream.write("-")
            self.stream.flush()

    def addError(self, test, err) -> None:
        unittest.TestResult.addError(self, test, err)
        if self.showAll:
            self.stream.writeln("ERROR")
        elif self.dots:
            self.stream.write("-")
            self.stream.flush()

    def addSkip(self, test, reason) -> None:
        unittest.TestResult.addSkip(self, test, reason)
        if self.showAll:
            self.stream.writeln("skipped")
        elif self.dots:
            self.stream.write("s")
            self.stream.flush()

    def printErrors(self) -> None:
        unexpected = getattr(self, "unexpectedSuccesses", ())
        if not (self.errors or self.failures or unexpected):
            return
        self.stream.writeln()
        self.stream.flush()
        self.printErrorList("ERROR", self.errors)
        self.printErrorList("FAIL", self.failures)
        if unexpected:
            self.stream.writeln(self.separator1)
            for test in unexpected:
                self.stream.writeln(f"UNEXPECTED SUCCESS: {self.getDescription(test)}")
            self.stream.flush()


class CompactRunner(unittest.TextTestRunner):
    resultclass = CompactResult

    def run(self, test):
        result = self._makeResult()
        unittest.registerResult(result)
        result.failfast = self.failfast
        result.buffer = self.buffer
        result.tb_locals = self.tb_locals
        with warnings.catch_warnings():
            if self.warnings:
                warnings.simplefilter(self.warnings)
            start_time = time.perf_counter()
            start_test_run = getattr(result, "startTestRun", None)
            if start_test_run is not None:
                start_test_run()
            try:
                test(result)
            finally:
                stop_test_run = getattr(result, "stopTestRun", None)
                if stop_test_run is not None:
                    stop_test_run()
            stop_time = time.perf_counter()

        result.printErrors()
        if self.durations is not None:
            self._printDurations(result)

        if result.dots and not result.showAll:
            self.stream.writeln()

        run_count = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        skipped = len(result.skipped) if hasattr(result, "skipped") else 0
        expected_failures = (
            len(result.expectedFailures) if hasattr(result, "expectedFailures") else 0
        )
        unexpected_successes = (
            len(result.unexpectedSuccesses)
            if hasattr(result, "unexpectedSuccesses")
            else 0
        )
        passed = (
            run_count
            - failures
            - errors
            - skipped
            - expected_failures
            - unexpected_successes
        )
        time_taken = stop_time - start_time
        summary = f"Ran {run_count} tests, passed {passed} tests, in {time_taken:.3f}s"
        if failures or errors:
            summary += f" (failures={failures}, errors={errors})"
        self.stream.writeln(summary)
        self.stream.flush()
        return result


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

    def test_emit_parse_warnings_strict(self) -> None:
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
            emit_parse_warnings(
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

    def test_emit_parse_warnings_non_strict(self) -> None:
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
            emit_parse_warnings(
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
    unittest.main(testRunner=CompactRunner, verbosity=1)
