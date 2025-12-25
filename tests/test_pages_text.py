import unittest

from test_pages import run_main

from pages_text import clean_text


class TestPagesText(unittest.TestCase):
    def test_clean_text_strips_blocks(self) -> None:
        text = "<script>x</script><style>y</style><!--c--><div>Hi<br>There</div>"
        self.assertEqual(clean_text(text), "Hi\nThere\n")

    def test_clean_text_entities(self) -> None:
        text = "A&nbsp;B &amp; C"
        self.assertEqual(clean_text(text), "A B & C\n")

    def test_clean_text_mysql_escapes(self) -> None:
        text = "Line1\\nLine2\\tX"
        self.assertEqual(clean_text(text), "Line1\nLine2 X\n")

    def test_clean_text_ascii(self) -> None:
        text = "Caf\u00e9"
        self.assertEqual(clean_text(text), "Cafe\n")


if __name__ == "__main__":
    run_main()
