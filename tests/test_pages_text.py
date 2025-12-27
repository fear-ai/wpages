import unittest

from test_pages import run_main

from pages_text import clean_text
from pages_util import SanitizeCounts


class TestPagesText(unittest.TestCase):
    def test_clean_text_strips_blocks(self) -> None:
        text = "<script>x</script><style>y</style><!--c--><div>Hi<br>There</div>"
        self.assertEqual(clean_text(text), "Hi There\n")

    def test_clean_text_entities(self) -> None:
        text = "A&nbsp;B &amp; C"
        self.assertEqual(clean_text(text), "A B C\n")

    def test_clean_text_mysql_escapes(self) -> None:
        text = "Line1\\nLine2\\tX"
        self.assertEqual(clean_text(text), "Line1\nLine2 X\n")

    def test_clean_text_ascii(self) -> None:
        text = "Caf\u00e9"
        self.assertEqual(clean_text(text), "Cafe\n")

    def test_clean_text_utf(self) -> None:
        text = "Caf\u00e9"
        self.assertEqual(clean_text(text, ascii_only=False), "Caf\u00e9\n")

    def test_clean_text_raw(self) -> None:
        text = "Caf\u00e9"
        self.assertEqual(clean_text(text, raw=True), "Caf\u00e9\n")

    def test_clean_text_raw_keeps_zero_width(self) -> None:
        text = "<b>Caf\u00e9\u200b</b>"
        self.assertEqual(clean_text(text, raw=True), "Caf\u00e9\u200b\n")

    def test_clean_text_notab_nonl_delete(self) -> None:
        text = "A\tB\nC"
        self.assertEqual(
            clean_text(text, replace_char="", keep_tabs=False, keep_newlines=False),
            "ABC\n",
        )

    def test_clean_text_counts(self) -> None:
        counts = SanitizeCounts()
        text = "<script>x</script><!--c--><b>Hi</b>&amp;"
        self.assertEqual(clean_text(text, counts=counts), "Hi\n")
        self.assertEqual(counts.blocks_rm, 1)
        self.assertEqual(counts.comments_rm, 1)
        self.assertEqual(counts.tags_rm, 2)
        self.assertEqual(counts.entities_rm, 1)


if __name__ == "__main__":
    run_main()
