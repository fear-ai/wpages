import sys
import time
import unittest
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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


def run_main() -> None:
    unittest.main(testRunner=CompactRunner, verbosity=1)
