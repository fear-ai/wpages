# PContent: Content Extraction Implementation

## Purpose
Define the extraction behavior implemented in `pages_content.py`.
This replaces the behavior of `pages_text.py` with clearer structure retention
and stronger character handling while keeping the implementation lightweight.

## Pipeline Overview
1) Decode MySQL literal escapes: `\\r`, `\\n`, `\\t`.
2) Remove scripts, styles, and HTML comments.
3) Convert structural HTML into text/Markdown markers:
   - Anchors to `text (URL)`.
   - Headings to `#`-style lines.
   - Lists to `- ` bullets.
   - Tables to delimited rows.
   - Block tags to line breaks.
4) Strip all remaining tags.
5) Unescape HTML entities and normalize line endings.
6) Filter control, zero-width, and non-ASCII characters.
7) Normalize whitespace and collapse repeated blank lines.
8) Write ASCII text with a trailing newline.

## Text Output Conversions

### Recognized Tags
- Removed: `script`, `style`, HTML comments.
- Links: `a` (to `text (URL)`).
- Line breaks: `br`.
- Headings: `h1`–`h6`.
- Lists: `ul`, `ol`, `li`.
- Tables: `table`, `thead`, `tbody`, `tfoot`, `tr`, `th`, `td`.
- Block tags to newline: `p`, `div`, `section`, `article`, `header`, `footer`,
  `blockquote`, `figure`, `figcaption`, `form`, `label`, `input`, `textarea`,
  `button`, `pre`, `code`, `hr`.
- Everything else is stripped as a generic tag.

### Links
- `<a href="URL">text</a>` becomes `text (URL)`.
- If the anchor text is empty after tag stripping, the URL alone is used.
- URLs remain visible even if the surrounding tag content is stripped.

### Headings
- `<h1>`..`<h6>` become `#`..`######` prefixed lines.
- Closing heading tags become line breaks.

### Lists
- `<li>` becomes `- ` and `</li>` becomes a newline.
- `<ul>` and `<ol>` become line breaks to separate lists.
- `<ol>` items are numbered (`1.`, `2.`, ...).
- Nested lists are flattened; list depth is not preserved.

### Tables
- `<tr>` becomes a newline.
- `<td>`/`<th>` become a configurable delimiter.
- Delimiters are preserved in output for table-like rows.
- When structure cannot be preserved, fallback is delimiter or newline.
- If the first cell is empty, a leading delimiter is dropped during normalization.

### Block Tags
- Common block tags (`p`, `div`, `section`, `article`, `header`, `footer`,
  `blockquote`, `figure`, `figcaption`, `form`, `label`, `input`,
  `textarea`, `button`, `pre`, `code`) become line breaks.

## Markdown Output Conversions

### Recognized Tags
- Removed: `script`, `style`, HTML comments.
- Code blocks: `pre`, `code` (nested or standalone).
- Headings: `h1`–`h6`.
- Emphasis: `strong`, `b`, `em`, `i`.
- Inline code: `code`.
- Paragraphs / breaks: `p`, `br`.
- Block tags to line breaks: `div`, `section`, `article`, `header`, `footer`,
  `blockquote`, `figure`, `figcaption`.
- Lists: `ul`, `ol`, `li`.
- Tables: `table`, `thead`, `tbody`, `tfoot`, `tr`, `th`, `td`.
- Links: `a` (to `[text](url)`).
- Images: `img` (to `![alt](src)`).
- Everything else is stripped as a generic tag.

- Headings become `#`..`######` lines.
- Paragraphs become blank-line separated blocks; `<br>` becomes a single line break.
- Lists become `-` bullets; nested lists are flattened.
- Ordered lists use numeric prefixes (`1.`, `2.`, ...).
- Tables become pipe-delimited rows (no header separator row).
- `<pre>`/`<code>` blocks become fenced code blocks; inline `<code>` uses backticks.
- `<strong>/<b>` become `**` and `<em>/<i>` become `*`.
- Links become `[text](url)` and images become `![alt](src)`.

## Block Tag Handling
- Text output: block-ish tags are replaced with `\n` on both open and close tags
  before generic tag stripping. `_normalize_lines()` then collapses blank lines
  and trims whitespace. This can introduce extra breaks for nested or inline
  usage but keeps blocks from being glued together.
- Markdown output: `<p>`, `<br>`, and block tags (`div`, `section`, `article`,
  `header`, `footer`, `blockquote`, `figure`, `figcaption`) are converted to line
  breaks (in addition to headings/lists/tables).

## Attribute Handling
- Anchor URLs are extracted from `href` and preserved in the output.
- Image URLs and alt text are extracted from `src` and `alt`.
- Link and image titles are extracted from `title` when present.
- Attribute extraction is regex-based and does not fully parse malformed HTML.
- Unquoted values stop at whitespace; `>` inside quoted values can truncate tags.
- Values are HTML-unescaped after extraction; entities in `href/src` are decoded.
- Bad schemes (`javascript`, `data`, `vbscript`, `file`, `blob`) are dropped and
  rendered as bracketed labels to require manual review.
- Scripts/styles/comments are stripped before link/image extraction; no extra
  URL normalization is applied beyond trimming and scheme checks.

### URL Processing Order and Implications
1) MySQL escapes are decoded and scripts/styles/comments are removed before
   link/image extraction.
2) `href/src/title/alt` are extracted, HTML-unescaped, and trimmed.
3) Bad schemes are dropped and replaced with bracketed labels.
4) Remaining tags are stripped, then character filtering runs.

Implications:
- Control/zero-width/bidi characters are removed after URL extraction, so they
  can appear in extracted URLs before filtering.
- Embedded newlines/tabs inside quoted attributes can survive extraction and
  become actual line breaks or tabs in output (filtering preserves `\n`/`\t`).
- Unquoted attributes stop at whitespace, so spaces/newlines truncate URLs.

## Character Filtering
- Control characters are removed or replaced (except newline and tab).
- Zero-width characters are removed or replaced.
- Non-ASCII characters are removed by default; replacement is optional.
- Replacement is suppressed after 1-2 consecutive replacements to avoid noise.

## Whitespace Normalization
- Line endings normalized to `\n`.
- Multiple spaces collapsed inside lines.
- Multiple blank lines collapsed to a single blank line.
- When table delimiter is `tab`, tabs are preserved between cells.
- Markdown output preserves whitespace inside fenced code blocks and only trims
  trailing spaces; other lines are normalized.

## CLI Options
In addition to the shared options from `pages_cli.py`:
- `--output-dir`: output directory for `.txt` or `.md` files.
- `--footer`: keep footer-like sections instead of stripping.
- `--format {text,markdown}`: output format (default: text).
- `--table-delim {comma,tab}`: table fallback delimiter (default: comma).
- `--replace-char CHAR`: replace suspicious characters instead of removing.

## Warnings
- Missing page names in the focus list are reported as warnings.
- Malformed list/table tags emit warnings based on opening/closing tag counts.
- Parsing warnings from `pages_db.py` (header mismatch, malformed rows, limits)
  are emitted before content extraction when present.

## Notes and Limitations
- HTML output is postponed.
- Markdown output is best-effort and uses regex-based tag handling.
- Parsing remains regex-based and can mis-handle malformed markup.
- Link, table, and list handling are best-effort fallbacks.
- Attribute parsing is best-effort and does not validate URL schemes.
- Blockquotes are treated as blank-line separators, not `>` prefixed Markdown.
- Nested lists are flattened rather than indented.
- Footnotes are not generated.
- Tables do not emit header separator rows in Markdown.
- Malformed list/table tags emit warnings based on tag count mismatches.

## Tables and Lists Gaps
- List nesting is lost; list depth is not preserved.
- Markdown tables are emitted without `| --- |` header separators.
- Table cell content is whitespace-normalized; alignment is not preserved.
- Mixed inline tags inside table cells are stripped, not formatted.
- Tag count warnings can fire for HTML with optional closing tags.

## Comparison to pages_text.py
- pages_text.py strips tags with regex, decodes HTML entities, normalizes
  whitespace, and forces ASCII via NFKD + ascii encode.
- pages_content.py adds structural conversions before tag stripping (links,
  headings, lists, tables) and explicit filtering for control, zero-width, and
  non-ASCII characters with optional replacement.
