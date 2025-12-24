import tempfile
import unittest
from pathlib import Path

from test_pages import TESTS_DIR, run_main

from pages_db import (
    ParseError,
    ParseLimits,
    build_id_index,
    build_title_index,
    parse_dump,
    pick_best,
)


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

    def test_empty_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "empty.out"
            path.write_text("", encoding="utf-8")
            with self.assertRaises(ParseError) as raised:
                parse_dump(path)
        self.assertIn(str(path), str(raised.exception))

    def test_missing_file_notfound(self) -> None:
        path = Path("nonexistant.file")
        with self.assertRaises(FileNotFoundError):
            parse_dump(path)

    def test_header_error_path(self) -> None:
        path = TESTS_DIR / "bad_header.out"
        with self.assertRaises(ParseError) as raised:
            parse_dump(path)
        message = str(raised.exception)
        self.assertIn("Header error", message)
        self.assertIn(str(path), message)

    def test_header_permit_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "alt_header.out"
            content = (
                "post_title\tid\tpost_content\tpost_status\tpost_date\n"
                "1\tTitle\tBody\tpublish\t2023-01-01\n"
            )
            path.write_text(content, encoding="utf-8")

            with self.assertRaises(ParseError):
                parse_dump(path)

            result = parse_dump(path, strict_header=False)
            self.assertTrue(result.stats.header_mismatch)
            self.assertEqual(len(result.stats.header_columns), 5)
            self.assertEqual(result.rows[0].id, "1")
            self.assertEqual(result.rows[0].title, "Title")

    def test_malformed_strict_path(self) -> None:
        path = TESTS_DIR / "malformed.out"
        with self.assertRaises(ParseError) as raised:
            parse_dump(path)
        message = str(raised.exception)
        self.assertIn("line 2", message)
        self.assertIn(str(path), message)

    def test_malformed_permit_counts(self) -> None:
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

    def test_validation_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "invalid_values.out"
            content = (
                "id\tpost_title\tpost_content\tpost_status\tpost_date\n"
                "abc\tTitle\tBody\tcustom\t2023-13-99\n"
            )
            path.write_text(content, encoding="utf-8")
            result = parse_dump(path)
            self.assertEqual(result.stats.invalid_id_count, 1)
            self.assertEqual(result.stats.unknown_status_count, 1)
            self.assertEqual(result.stats.invalid_date_count, 1)

    def test_use_csv_parsing(self) -> None:
        result = parse_dump(TESTS_DIR / "sample.out", use_csv=True)
        self.assertEqual(len(result.rows), 8)
        self.assertEqual(result.rows[0].title, "Home")

    def test_csv_escaped_delim(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "escaped.out"
            content = (
                "id\tpost_title\tpost_content\tpost_status\tpost_date\n"
                "1\tTitle\tHello\\\tWorld\tpublish\t2023-01-01\n"
            )
            path.write_text(content, encoding="utf-8")

            baseline = parse_dump(path)
            self.assertNotEqual(baseline.rows[0].status, "publish")
            self.assertNotEqual(baseline.rows[0].date, "2023-01-01")

            result = parse_dump(path, use_csv=True)
            self.assertEqual(len(result.rows), 1)
            self.assertEqual(result.rows[0].content, "Hello\tWorld")
            self.assertEqual(result.rows[0].status, "publish")
            self.assertEqual(result.rows[0].date, "2023-01-01")

    def test_newline_variants(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "newline.out"
            content = (
                b"id\tpost_title\tpost_content\tpost_status\tpost_date\r\n"
                b"1\tA\tX\tpublish\t2023-01-01\n"
                b"2\tB\tY\tdraft\t2023-01-02\r\n"
                b"3\tC\tZ\tprivate\t2023-01-03\r"
                b"4\tD\tW\tpublish\t2023-01-04\n\r"
            )
            path.write_bytes(content)
            result = parse_dump(path)
            self.assertEqual(len(result.rows), 4)
            for row in result.rows:
                self.assertNotIn("\r", row.date)

    def test_include_content_false(self) -> None:
        result = parse_dump(TESTS_DIR / "sample.out", include_content=False)
        self.assertEqual(result.rows[0].content, "")

    def test_duplicate_id_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate_id.out"
            path.write_text(
                "id\tpost_title\tpost_content\tpost_status\tpost_date\n"
                "1\tOne\tFirst\tpublish\t2023-01-01\n"
                "1\tTwo\tSecond\tdraft\t2023-01-02\n",
                encoding="utf-8",
            )
            result = parse_dump(path)
            self.assertEqual(len(result.rows), 2)
            self.assertEqual(result.stats.duplicate_id_count, 1)

    def test_indexes_and_best(self) -> None:
        rows = parse_dump(TESTS_DIR / "sample.out").rows
        title_index = build_title_index(rows)
        id_index = build_id_index(rows)
        self.assertEqual(len(title_index["Home"]), 2)
        self.assertEqual(len(id_index["1"]), 1)
        best = pick_best(title_index["Home"])
        self.assertIsNotNone(best)
        self.assertEqual(best.id, "1")


if __name__ == "__main__":
    run_main()
