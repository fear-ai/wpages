import unittest

from test_pages import run_main

from pages_content import clean_content, clean_md, _structure_warnings
from pages_util import SanitizeCounts


class TestPagesContent(unittest.TestCase):
    def test_clean_content_links(self) -> None:
        text = '<a href="https://example.com">Link</a>'
        self.assertEqual(
            clean_content(text, table_delim=",", replace_char=""),
            "Link (https://example.com)\n",
        )

    def test_clean_content_link_title(self) -> None:
        text = '<a href="https://example.com" title="Site">Link</a>'
        self.assertEqual(
            clean_content(text, table_delim=",", replace_char=""),
            'Link (https://example.com "Site")\n',
        )

    def test_clean_content_link_blocked_scheme(self) -> None:
        text = '<a href="javascript:alert(1)">Link</a>'
        self.assertEqual(
            clean_content(text, table_delim=",", replace_char=""),
            "[Link]\n",
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

    def test_clean_content_ordered_list(self) -> None:
        text = "<ol><li>One</li><li>Two</li></ol>"
        self.assertEqual(
            clean_content(text, table_delim=",", replace_char=""),
            "1. One\n2. Two\n",
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

    def test_clean_content_utf(self) -> None:
        text = "Caf\u00e9"
        self.assertEqual(
            clean_content(text, table_delim=",", replace_char=" ", ascii_only=False),
            "Caf\u00e9\n",
        )

    def test_clean_content_zero_width(self) -> None:
        text = "A\u200bB"
        self.assertEqual(clean_content(text, table_delim=",", replace_char=""), "AB\n")

    def test_clean_content_replace_char(self) -> None:
        text = "A\u200bB"
        self.assertEqual(clean_content(text, table_delim=",", replace_char="?"), "A?B\n")

    def test_clean_content_raw_keeps_zero_width(self) -> None:
        text = "Caf\u00e9\u200b"
        self.assertEqual(
            clean_content(text, table_delim=",", replace_char=" ", raw=True),
            "Caf\u00e9\u200b\n",
        )

    def test_clean_content_notab_nonl_delete(self) -> None:
        text = "A\tB\nC"
        self.assertEqual(
            clean_content(
                text,
                table_delim=",",
                replace_char="",
                keep_tabs=False,
                keep_newlines=False,
            ),
            "ABC\n",
        )

    def test_clean_content_counts(self) -> None:
        counts = SanitizeCounts()
        text = (
            '<a href="javascript:alert(1)">Link</a>'
            "<h2>H</h2>"
            "<ul><li>One</li></ul>"
            "<table><tr><td>A</td></tr></table>"
            "<!--c-->"
        )
        clean_content(text, table_delim=",", replace_char="", counts=counts)
        self.assertEqual(counts.anchors_conv, 1)
        self.assertEqual(counts.blocked_scheme_links, 1)
        self.assertEqual(counts.headings_conv, 1)
        self.assertEqual(counts.lists_conv, 1)
        self.assertEqual(counts.tables_conv, 1)
        self.assertEqual(counts.comments_rm, 1)

    def test_clean_content_notags_sink(self) -> None:
        seen: list[str] = []

        def sink(value: str) -> None:
            seen.append(value)

        self.assertEqual(
            clean_content("<b>Hi</b>&amp;", table_delim=",", replace_char="", notags_sink=sink),
            "Hi &\n",
        )
        self.assertEqual(len(seen), 1)
        self.assertIn("Hi", seen[0])
        self.assertIn("&amp;", seen[0])
        self.assertNotIn("<", seen[0])

    def test_clean_content_nested_lists(self) -> None:
        text = "<ul><li>One<ul><li>Sub</li></ul></li><li>Two</li></ul>"
        self.assertEqual(
            clean_content(text, table_delim=",", replace_char=""),
            "- One\n- Sub\n- Two\n",
        )

    def test_clean_content_list_block_tags(self) -> None:
        text = "<ul><li><p>One</p></li><li><div>Two</div></li></ul>"
        self.assertEqual(
            clean_content(text, table_delim=",", replace_char=""),
            "- One\n- Two\n",
        )

    def test_clean_md_headings_emphasis_code(self) -> None:
        text = "<h2>Title</h2><p><strong>Bold</strong> <em>Ital</em> <code>x=1</code></p><pre><code>line  1</code></pre>"
        self.assertEqual(
            clean_md(text, replace_char=""),
            "## Title\n\n**Bold** *Ital* `x=1`\n\n```\nline  1\n```\n",
        )

    def test_clean_md_paragraph_breaks(self) -> None:
        text = "<p>One<br>Two</p>"
        self.assertEqual(
            clean_md(text, replace_char=""),
            "One\nTwo\n",
        )

    def test_clean_md_block_tags(self) -> None:
        text = "<div>One</div><section>Two</section><blockquote>Three</blockquote>"
        self.assertEqual(
            clean_md(text, replace_char=""),
            "One\n\nTwo\n\nThree\n",
        )

    def test_clean_md_pre(self) -> None:
        text = "<pre>line 1</pre>"
        self.assertEqual(
            clean_md(text, replace_char=""),
            "```\nline 1\n```\n",
        )

    def test_clean_md_pre_whitespace(self) -> None:
        text = (
            "<pre>line 1\n  indented line\n\t\ttabs\n\n"
            "line  with  double  spaces\ntrailing spaces   \n"
            "brace {x: 1}\n</pre>"
        )
        self.assertEqual(
            clean_md(text, replace_char=""),
            "```\nline 1\n  indented line\n\t\ttabs\n\n"
            "line  with  double  spaces\ntrailing spaces\n"
            "brace {x: 1}\n\n```\n",
        )

    def test_clean_md_code(self) -> None:
        text = "<code>line 1</code>"
        self.assertEqual(
            clean_md(text, replace_char=""),
            "`line 1`\n",
        )

    def test_clean_md_pre_code_attrs(self) -> None:
        text = '<pre class="code" data-lang="txt"><code class="lang">line 1</code></pre>'
        self.assertEqual(
            clean_md(text, replace_char=""),
            "```\nline 1\n```\n",
        )

    def test_clean_md_pre_then_code(self) -> None:
        text = "<pre>line 1</pre><code>line 2</code>"
        self.assertEqual(
            clean_md(text, replace_char=""),
            "```\nline 1\n```\n`line 2`\n",
        )

    def test_clean_md_code_then_pre(self) -> None:
        text = "<code>line 1</code><pre>line 2</pre>"
        self.assertEqual(
            clean_md(text, replace_char=""),
            "`line 1`\n```\nline 2\n```\n",
        )

    def test_clean_md_pre_code_nested(self) -> None:
        text = "<pre><code>line 1</code></pre>"
        self.assertEqual(
            clean_md(text, replace_char=""),
            "```\nline 1\n```\n",
        )

    def test_clean_md_pre_code_mixed(self) -> None:
        text = "<pre><code>CODE<pre><code>"
        self.assertEqual(
            clean_md(text, replace_char=""),
            "```\nCODE\n```\n",
        )

    def test_clean_md_code_pre_nested(self) -> None:
        text = "<code><pre>line 1</pre></code>"
        self.assertEqual(
            clean_md(text, replace_char=""),
            "`\n```\nline 1\n```\n`\n",
        )

    def test_clean_md_lists_tables(self) -> None:
        text = "<ul><li>One</li><li>Two</li></ul><table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"
        self.assertEqual(
            clean_md(text, replace_char=""),
            "- One\n- Two\nA | B\n1 | 2\n",
        )

    def test_clean_md_list_block_tags(self) -> None:
        text = "<ul><li><p>One</p></li><li><div>Two</div></li></ul>"
        self.assertEqual(
            clean_md(text, replace_char=""),
            "- One\n- Two\n",
        )

    def test_clean_md_ordered_list(self) -> None:
        text = "<ol><li>One</li><li>Two</li></ol>"
        self.assertEqual(
            clean_md(text, replace_char=""),
            "1. One\n2. Two\n",
        )

    def test_clean_md_links_images(self) -> None:
        text = '<p><a href="https://x">Link</a> <img src="img.png" alt="Alt"></p>'
        self.assertEqual(
            clean_md(text, replace_char=""),
            "[Link](https://x) ![Alt](img.png)\n",
        )

    def test_clean_md_link_title(self) -> None:
        text = '<a href="https://x" title="T">Link</a>'
        self.assertEqual(
            clean_md(text, replace_char=""),
            '[Link](https://x "T")\n',
        )

    def test_clean_md_link_blocked_scheme(self) -> None:
        text = '<a href="data:text/html">Link</a>'
        self.assertEqual(
            clean_md(text, replace_char=""),
            "[Link]\n",
        )

    def test_clean_md_image_title(self) -> None:
        text = '<img src="img.png" alt="Alt" title="T">'
        self.assertEqual(
            clean_md(text, replace_char=""),
            '![Alt](img.png "T")\n',
        )

    def test_clean_md_image_blocked_scheme(self) -> None:
        text = '<img src="blob:xyz" alt="Alt">'
        self.assertEqual(
            clean_md(text, replace_char=""),
            "[Alt]\n",
        )

    def test_clean_md_notags_sink(self) -> None:
        seen: list[str] = []

        def sink(value: str) -> None:
            seen.append(value)

        self.assertEqual(clean_md("<b>Hi</b>&amp;", replace_char="", notags_sink=sink), "**Hi**&\n")
        self.assertEqual(len(seen), 1)
        self.assertIn("Hi", seen[0])
        self.assertIn("&amp;", seen[0])
        self.assertNotIn("<", seen[0])

    def test_clean_md_ent(self) -> None:
        text = "<script>bad</script>A&nbsp;B &amp; C"
        self.assertEqual(
            clean_md(text, replace_char=""),
            "A B & C\n",
        )

    def test_structure_warnings_lists(self) -> None:
        text = "<ul><li>One"
        warnings = _structure_warnings(text)
        self.assertEqual(
            warnings,
            ["Malformed list structure: <ul> 1 != </ul> 0; <li> 1 != </li> 0"],
        )

    def test_structure_warnings_tables(self) -> None:
        text = "<table><tr><td>A"
        warnings = _structure_warnings(text)
        self.assertEqual(
            warnings,
            [
                "Malformed table structure: <table> 1 != </table> 0; <tr> 1 != </tr> 0; <td> 1 != </td> 0"
            ],
        )


if __name__ == "__main__":
    run_main()
