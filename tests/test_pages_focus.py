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

from pages_db import build_title_index, parse_dump
from pages_focus import (
    FocusEntry,
    build_rows_with_keys,
    load_focus_list,
    match_focus_entry,
    match_label,
)

TESTS_DIR = ROOT / "tests"


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


class TestPagesFocus(unittest.TestCase):
    def test_load_focus_list_dedupe_nocase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pages.list"
            path.write_text("Home, home\nAbout\n", encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                entries = load_focus_list(path, case_sensitive=False)
            self.assertEqual([entry.name for entry in entries], ["Home", "About"])
            self.assertEqual([entry.key for entry in entries], ["home", "about"])
            self.assertIn("Duplicate page name skipped", stderr.getvalue())

    def test_load_focus_list_case_sensitive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pages.list"
            path.write_text("Home\nhome\n", encoding="utf-8")
            entries = load_focus_list(path, case_sensitive=True)
            self.assertEqual([entry.name for entry in entries], ["Home", "home"])
            self.assertEqual([entry.key for entry in entries], ["Home", "home"])

    def test_build_rows_with_keys_case_insensitive(self) -> None:
        rows = parse_dump(TESTS_DIR / "sample.out").rows
        rows_with_keys = build_rows_with_keys(rows, case_sensitive=False)
        self.assertEqual(len(rows_with_keys), len(rows))
        self.assertEqual(rows_with_keys[0][0], "home")
        self.assertEqual(rows_with_keys[0][1].title, "Home")

    def test_match_focus_entry_exact_picks_best(self) -> None:
        rows = parse_dump(TESTS_DIR / "sample.out").rows
        title_index = build_title_index(rows, case_sensitive=True)
        rows_with_keys = build_rows_with_keys(rows, case_sensitive=True)
        entry = FocusEntry(name="Home", key="Home", key_len=4)
        label, row = match_focus_entry(
            entry, title_index=title_index, rows_with_keys=rows_with_keys, use_prefix=False
        )
        self.assertEqual(label, "exact")
        self.assertIsNotNone(row)
        self.assertEqual(row.id, "1")

    def test_match_focus_entry_prefix_picks_best(self) -> None:
        rows = parse_dump(TESTS_DIR / "sample.out").rows
        title_index = build_title_index(rows, case_sensitive=False)
        rows_with_keys = build_rows_with_keys(rows, case_sensitive=False)
        entry = FocusEntry(name="Con", key="con", key_len=3)
        label, row = match_focus_entry(
            entry, title_index=title_index, rows_with_keys=rows_with_keys, use_prefix=True
        )
        self.assertEqual(label, "prefix")
        self.assertIsNotNone(row)
        self.assertEqual(row.id, "6")

    def test_match_label_exact_over_prefix(self) -> None:
        rows = parse_dump(TESTS_DIR / "sample.out").rows
        row = next(r for r in rows if r.title == "Contact")
        entries = [
            FocusEntry(name="Con", key="Con", key_len=3),
            FocusEntry(name="Contact", key="Contact", key_len=7),
        ]
        label, focus = match_label(row, entries, case_sensitive=True, use_prefix=True)
        self.assertEqual(label, "exact")
        self.assertEqual(focus, "Contact")

    def test_match_label_longest_prefix(self) -> None:
        rows = parse_dump(TESTS_DIR / "sample.out").rows
        row = next(r for r in rows if r.title == "Contact")
        entries = [
            FocusEntry(name="Con", key="Con", key_len=3),
            FocusEntry(name="Contac", key="Contac", key_len=6),
        ]
        label, focus = match_label(row, entries, case_sensitive=True, use_prefix=True)
        self.assertEqual(label, "prefix")
        self.assertEqual(focus, "Contac")


if __name__ == "__main__":
    unittest.main(testRunner=CompactRunner, verbosity=1)
