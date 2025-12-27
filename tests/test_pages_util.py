import unittest

from test_pages import run_main

from pages_util import decode_mysql_escapes, filter_characters, safe_filename, strip_footer


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


if __name__ == "__main__":
    run_main()
