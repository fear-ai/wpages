import unittest

from test_pages import run_main

from pages_content import clean_content


class TestPagesContent(unittest.TestCase):
    def test_clean_content_links(self) -> None:
        text = '<a href="https://example.com">Link</a>'
        self.assertEqual(
            clean_content(text, table_delim=",", replace_char=""),
            "Link (https://example.com)\n",
        )

    def test_clean_content_anchor_nested(self) -> None:
        text = '<a href="https://example.com"><span>Go</span></a>'
        self.assertEqual(
            clean_content(text, table_delim=",", replace_char=""),
            "Go (https://example.com)\n",
        )

    def test_clean_content_entities(self) -> None:
        text = "A&nbsp;B &amp; C"
        self.assertEqual(
            clean_content(text, table_delim=",", replace_char=""),
            "A B & C\n",
        )

    def test_clean_content_removes_blocks(self) -> None:
        text = "<script>bad</script><style>x</style><!--c-->OK"
        self.assertEqual(
            clean_content(text, table_delim=",", replace_char=""),
            "OK\n",
        )

    def test_clean_content_structure(self) -> None:
        text = "<h2>Title</h2><ul><li>One</li><li>Two</li></ul>"
        self.assertEqual(
            clean_content(text, table_delim=",", replace_char=""),
            "## Title\n- One\n- Two\n",
        )

    def test_clean_content_table(self) -> None:
        text = "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"
        self.assertEqual(
            clean_content(text, table_delim=",", replace_char=""),
            "A,B\n1,2\n",
        )

    def test_clean_content_table_tab(self) -> None:
        text = "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"
        self.assertEqual(
            clean_content(text, table_delim="\t", replace_char=""),
            "A\tB\n1\t2\n",
        )

    def test_clean_content_mysql_escapes(self) -> None:
        text = "Line1\\nLine2\\tX"
        self.assertEqual(clean_content(text, table_delim=",", replace_char=""), "Line1\nLine2 X\n")

    def test_clean_content_ascii(self) -> None:
        text = "Caf\u00e9"
        self.assertEqual(clean_content(text, table_delim=",", replace_char=""), "Cafe\n")

    def test_clean_content_zero_width(self) -> None:
        text = "A\u200bB"
        self.assertEqual(clean_content(text, table_delim=",", replace_char=""), "AB\n")

    def test_clean_content_replace_char(self) -> None:
        text = "A\u200bB"
        self.assertEqual(clean_content(text, table_delim=",", replace_char="?"), "A?B\n")

    def test_clean_content_nested_lists(self) -> None:
        text = "<ul><li>One<ul><li>Sub</li></ul></li><li>Two</li></ul>"
        self.assertEqual(
            clean_content(text, table_delim=",", replace_char=""),
            "- One\n- Sub\n- Two\n",
        )


if __name__ == "__main__":
    run_main()
