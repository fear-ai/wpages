# PContent: Plain Text Content Extraction

## Purpose
Define the new plain text extraction approach implemented in `pages_content.py`.
This replaces the behavior of `pages_text.py` with clearer structure retention
and stronger character handling while keeping the implementation lightweight.

## Output Goals
- Readable, printable ASCII text output.
- Preserve page structure signals where practical (headings, lists, tables).
- Keep link destinations visible in the text output.
- Strong default sanitization and removal of suspicious characters.

## Pipeline Overview
1) Decode MySQL literal escapes: `\\r`, `\\n`, `\\t`.
2) Remove scripts, styles, and HTML comments.
3) Convert structural HTML into text markers:
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

## Structural Conversions
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

### Tables
- `<tr>` becomes a newline.
- `<td>`/`<th>` become a configurable delimiter.
- Delimiters are preserved in output for table-like rows.
- When structure cannot be preserved, fallback is delimiter or newline.

### Block Tags
- Common block tags (`p`, `div`, `section`, `article`, `header`, `footer`,
  `blockquote`, `figure`, `figcaption`, `form`, `label`, `input`,
  `textarea`, `button`, `pre`, `code`) become line breaks.

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

## CLI Options
In addition to the shared options from `pages_cli.py`:
- `--output-dir`: output directory for `.txt` files.
- `--footer`: keep footer-like sections instead of stripping.
- `--table-delim {comma,tab}`: table fallback delimiter (default: comma).
- `--replace-char CHAR`: replace suspicious characters instead of removing.

## Notes and Limitations
- Output is plain text only; HTML output is postponed.
- Markdown is not yet produced, but headings and list markers align with it.
- Parsing remains regex-based and can mis-handle malformed markup.
- Link, table, and list handling are best-effort fallbacks.

## Comparison to pages_text.py
- pages_text.py strips tags with regex, decodes HTML entities, normalizes
  whitespace, and forces ASCII via NFKD + ascii encode.
- pages_content.py adds structural conversions before tag stripping (links,
  headings, lists, tables) and explicit filtering for control, zero-width, and
  non-ASCII characters with optional replacement.
