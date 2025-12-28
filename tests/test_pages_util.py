import tempfile
import unittest
from pathlib import Path

from test_pages import run_main

from pages_util import (
    FilterCounts,
    decode_mysql_escapes,
    filter_characters,
    open_text_check,
    prepare_output_dir,
    read_text_check,
    safe_filename,
    strip_footer,
    write_bytes_check,
    write_text_check,
)


class TestPagesUtil(unittest.TestCase):
    def test_decode_mysql_escapes(self) -> None:
        text = "Line1\\nLine2\\tX\\rY"
        self.assertEqual(decode_mysql_escapes(text), "Line1\nLine2\tX\nY")

    def test_decode_mysql_escapes_empty(self) -> None:
        self.assertEqual(decode_mysql_escapes(""), "")

    def test_strip_footer(self) -> None:
        text = "A\nResources\nB\n"
        self.assertEqual(strip_footer(text), "A\n")

    def test_strip_footer_none(self) -> None:
        text = "A\nB\n"
        self.assertEqual(strip_footer(text), text)

    def test_safe_filename(self) -> None:
        name = "  Foo/Bar  Baz  "
        self.assertEqual(safe_filename(name), "Foo-Bar Baz.txt")

    def test_safe_filename_ascii(self) -> None:
        self.assertEqual(safe_filename("Caf\u00e9"), "Cafe.txt")

    def test_safe_filename_custom_ext(self) -> None:
        self.assertEqual(safe_filename("Name", ".md"), "Name.md")

    def test_safe_filename_reserved(self) -> None:
        self.assertEqual(safe_filename("CON"), "CON_1.txt")

    def test_safe_filename_collision(self) -> None:
        existing = {"Name.txt"}
        self.assertEqual(safe_filename("Name", existing=existing), "Name_1.txt")

    def test_safe_filename_reserved_collision(self) -> None:
        existing = {"CON_1.txt"}
        self.assertEqual(safe_filename("CON", existing=existing), "CON_2.txt")

    def test_safe_filename_max_length(self) -> None:
        name = "A" * 300
        result = safe_filename(name)
        self.assertTrue(result.endswith(".txt"))
        self.assertEqual(len(result), 255)

    def test_safe_filename_trailing_dots_spaces(self) -> None:
        self.assertEqual(safe_filename(" Name. "), "Name.txt")

    def test_safe_filename_long_extension(self) -> None:
        name = "A" * 300
        result = safe_filename(name, ".markdown")
        self.assertTrue(result.endswith(".markdown"))
        self.assertEqual(len(result), 255)

    def test_safe_filename_empty_base_collision(self) -> None:
        existing = {"page.txt"}
        self.assertEqual(safe_filename("   ", existing=existing), "page_1.txt")

    def test_filter_characters_ascii(self) -> None:
        text = "A\u200bB\u00e9\x01"
        self.assertEqual(filter_characters(text, " "), "A Be ")

    def test_filter_characters_delete(self) -> None:
        text = "A\u200bB"
        self.assertEqual(filter_characters(text, ""), "AB")

    def test_filter_characters_suppression(self) -> None:
        text = "A\u200b\u200bB\u200bC"
        self.assertEqual(filter_characters(text, "?"), "A?B?C")

    def test_filter_characters_control_suppression(self) -> None:
        text = "A\x01\x02B"
        self.assertEqual(filter_characters(text, "?"), "A?B")

    def test_filter_characters_utf(self) -> None:
        text = "Caf\u00e9"
        self.assertEqual(
            filter_characters(text, " ", ascii_only=False),
            "Caf\u00e9",
        )

    def test_filter_characters_counts(self) -> None:
        counts = FilterCounts()
        text = "\t\nA\u200bB\x01C\u00e9"
        cleaned = filter_characters(
            text,
            "?",
            keep_tabs=False,
            keep_newlines=False,
            ascii_only=True,
            counts=counts,
        )
        self.assertEqual(cleaned, "?A?B?Ce?")
        self.assertEqual(counts.re_tab, 1)
        self.assertEqual(counts.re_nl, 1)
        self.assertEqual(counts.re_zero, 1)
        self.assertEqual(counts.re_control, 1)
        self.assertEqual(counts.re_non_ascii, 1)
        self.assertEqual(counts.rep_chars, 4)

    def test_prepare_output_dir_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "output.txt"
            path.write_text("x", encoding="utf-8")
            with self.assertRaises(OSError) as raised:
                prepare_output_dir(path)
            self.assertIn("output path is not a directory", str(raised.exception))

    def test_prepare_output_dir_creates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "new_dir"
            prepare_output_dir(path)
            self.assertTrue(path.is_dir())

    def test_write_text_check_dir_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dir_path"
            path.mkdir()
            with self.assertRaises(OSError) as raised:
                write_text_check(path, "x")
            self.assertIn("output path is a directory", str(raised.exception))

    def test_write_text_check_missing_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing" / "file.txt"
            with self.assertRaises(OSError) as raised:
                write_text_check(path, "x")
            self.assertIn("output file could not be written", str(raised.exception))

    def test_write_bytes_check_dir_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dir_path"
            path.mkdir()
            with self.assertRaises(OSError) as raised:
                write_bytes_check(path, b"x")
            self.assertIn("output path is a directory", str(raised.exception))

    def test_write_bytes_check_missing_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing" / "file.bin"
            with self.assertRaises(OSError) as raised:
                write_bytes_check(path, b"x")
            self.assertIn("output file could not be written", str(raised.exception))

    def test_read_text_check_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.txt"
            with self.assertRaises(FileNotFoundError):
                read_text_check(path)

    def test_read_text_check_dir_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dir_path"
            path.mkdir()
            with self.assertRaises(OSError) as raised:
                read_text_check(path)
            self.assertIn("input file could not be read", str(raised.exception))

    def test_open_text_check_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.txt"
            with self.assertRaises(FileNotFoundError):
                open_text_check(path)


if __name__ == "__main__":
    run_main()
