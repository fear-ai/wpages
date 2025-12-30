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
        self.assertEqual(first.content_bytes, 12)
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

    def test_directory_path_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            with self.assertRaises(ParseError) as raised:
                parse_dump(path)
            self.assertIn("input file could not be read", str(raised.exception))

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
                b"3\tC\tZ\tprivate\t2023-01-03\n"
                b"4\tD\tW\tpublish\t2023-01-04\r\n"
            )
            path.write_bytes(content)
            result = parse_dump(path)
            self.assertEqual(len(result.rows), 4)
            for row in result.rows:
                self.assertNotIn("\r", row.date)

    def test_newline_lfcr(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "lfcr.out"
            content = (
                b"id\tpost_title\tpost_content\tpost_status\tpost_date\n\r"
                b"1\tA\tX\tpublish\t2023-01-01\n\r"
                b"2\tB\tY\tdraft\t2023-01-02\n\r"
            )
            path.write_bytes(content)
            result = parse_dump(path)
            self.assertEqual(len(result.rows), 2)
            self.assertEqual(result.rows[0].id, "1")
            self.assertEqual(result.rows[1].id, "2")

    def test_embedded_newline_raw_dump(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "embedded_newline.out"
            content = (
                b"id\tpost_title\tpost_content\tpost_status\tpost_date\n"
                b"1\tTitle\tLine1\nLine2\tpublish\t2023-01-01\n"
            )
            path.write_bytes(content)
            with self.assertRaises(ParseError) as raised:
                parse_dump(path)
            message = str(raised.exception)
            self.assertIn("line 2", message)
            self.assertIn("expected 5 columns", message)

    def test_cr_only_newlines_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "cr_only.out"
            content = (
                b"id\tpost_title\tpost_content\tpost_status\tpost_date\r"
                b"1\tA\tX\tpublish\t2023-01-01\r"
                b"2\tB\tY\tdraft\t2023-01-02\r"
            )
            path.write_bytes(content)
            with self.assertRaises(ParseError) as raised:
                parse_dump(path)
            message = str(raised.exception)
            self.assertIn("Header error", message)
            self.assertIn(str(path), message)

    def test_include_content_false(self) -> None:
        result = parse_dump(TESTS_DIR / "sample.out", include_content=False)
        self.assertEqual(result.rows[0].content, "")
        self.assertEqual(result.rows[0].content_bytes, 12)

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

    def test_dump_rows_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "rows"
            result = parse_dump(TESTS_DIR / "sample.out", dump_rows_dir=out_dir)
            self.assertEqual(len(result.rows), 8)
            files = sorted(out_dir.glob("*.txt"))
            self.assertEqual(len(files), 8)
            first = (out_dir / "1.txt").read_text(encoding="utf-8")
            self.assertEqual(
                first,
                "1\nHome\nWelcome home\npublish\n2023-01-01\n",
            )

    def test_dump_rows_dir_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "rows"
            out_dir.write_text("not a dir", encoding="utf-8")
            with self.assertRaises(ParseError) as raised:
                parse_dump(TESTS_DIR / "sample.out", dump_rows_dir=out_dir)
            self.assertIn("Dump rows directory is not a directory", str(raised.exception))

    def test_dump_rows_path_is_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "rows"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "1.txt").mkdir()
            with self.assertRaises(ParseError) as raised:
                parse_dump(TESTS_DIR / "sample.out", dump_rows_dir=out_dir)
            self.assertIn("Dump rows path is a directory", str(raised.exception))

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
