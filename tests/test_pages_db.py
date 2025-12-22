import tempfile
import unittest
from pathlib import Path

from pages_db import (
    ParseError,
    ParseLimits,
    build_id_index,
    build_title_index,
    parse_dump,
    pick_best,
)


ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"


class TestPagesDB(unittest.TestCase):
    def test_parse_dump_basic(self) -> None:
        result = parse_dump(TESTS_DIR / "sample.out")
        self.assertEqual(len(result.rows), 8)
        self.assertEqual(result.stats.read_lines, 8)
        self.assertEqual(result.stats.skipped_malformed, 0)
        self.assertEqual(result.stats.skipped_oversized, 0)
        self.assertFalse(result.stats.reached_limit)
        first = result.rows[0]
        self.assertEqual(first.id, "1")
        self.assertEqual(first.title, "Home")
        self.assertEqual(first.content, "Welcome home")
        self.assertEqual(first.status, "publish")
        self.assertEqual(first.date, "2023-01-01")

    def test_empty_file_error_includes_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "empty.out"
            path.write_text("", encoding="utf-8")
            with self.assertRaises(ParseError) as raised:
                parse_dump(path)
        self.assertIn(str(path), str(raised.exception))

    def test_header_error_includes_path(self) -> None:
        path = TESTS_DIR / "bad_header.out"
        with self.assertRaises(ParseError) as raised:
            parse_dump(path)
        message = str(raised.exception)
        self.assertIn("Unexpected header columns", message)
        self.assertIn(str(path), message)

    def test_malformed_strict_columns_error_includes_path(self) -> None:
        path = TESTS_DIR / "malformed.out"
        with self.assertRaises(ParseError) as raised:
            parse_dump(path)
        message = str(raised.exception)
        self.assertIn("line 2", message)
        self.assertIn(str(path), message)

    def test_malformed_non_strict_counts(self) -> None:
        result = parse_dump(TESTS_DIR / "malformed.out", strict_columns=False)
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.rows[0].id, "10")
        self.assertEqual(result.stats.skipped_malformed, 1)
        self.assertEqual(result.stats.read_lines, 2)

    def test_limits_max_lines(self) -> None:
        result = parse_dump(TESTS_DIR / "sample.out", limits=ParseLimits(max_lines=2))
        self.assertEqual(len(result.rows), 2)
        self.assertEqual(result.rows[0].id, "1")
        self.assertEqual(result.rows[1].id, "2")
        self.assertEqual(result.stats.read_lines, 2)
        self.assertTrue(result.stats.reached_limit)

    def test_limits_max_bytes(self) -> None:
        result = parse_dump(
            TESTS_DIR / "oversized.out", limits=ParseLimits(max_bytes=100)
        )
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.rows[0].id, "13")
        self.assertEqual(result.stats.read_lines, 2)
        self.assertEqual(result.stats.skipped_oversized, 1)

    def test_use_csv_parsing(self) -> None:
        result = parse_dump(TESTS_DIR / "sample.out", use_csv=True)
        self.assertEqual(len(result.rows), 8)
        self.assertEqual(result.rows[0].title, "Home")

    def test_include_content_false(self) -> None:
        result = parse_dump(TESTS_DIR / "sample.out", include_content=False)
        self.assertEqual(result.rows[0].content, "")

    def test_indexes_and_pick_best(self) -> None:
        rows = parse_dump(TESTS_DIR / "sample.out").rows
        title_index = build_title_index(rows)
        id_index = build_id_index(rows)
        self.assertEqual(len(title_index["Home"]), 2)
        self.assertEqual(len(id_index["1"]), 1)
        best = pick_best(title_index["Home"])
        self.assertIsNotNone(best)
        self.assertEqual(best.id, "1")


if __name__ == "__main__":
    unittest.main()
