# PText: Immediate Improvements to Plain Text Cleaning

## Purpose
Document small, low-risk improvements to the current plain text cleaning path
(`pages_text.py`) and a concrete testing/validation plan.

## Current Behavior Summary
- Replaces MySQL literal escapes (`\\r`, `\\n`, `\\t`).
- Strips scripts, styles, and HTML comments with regex.
- Converts block tags to newlines, strips remaining tags.
- Unescapes HTML entities and normalizes whitespace.
- Forces ASCII with NFKD normalization + `encode("ascii", "ignore")`.
- Collapses blank lines and ensures a trailing newline.
- Optional footer stripping ("Resources"/"Community").
 - Parsing uses newline="\\n" to avoid splitting rows on bare \\r inside content.

## Proposed Improvements (Quick Changes)
Each item is designed to fit within the existing regex-based approach.

### 1) Preserve Links as Text
Goal: keep link destinations in plain text.
Approach:
- Before stripping tags, convert `<a href="URL">text</a>` to
  `text (URL)` or `text [URL]`.
- If text is empty, emit `(URL)` alone.
Edge cases:
- Nested tags inside `<a>` should be stripped after substitution.
- Invalid or missing `href` should drop the URL.

### 2) Preserve Lists as Bullets
Goal: keep list structure readable.
Approach:
- Convert `<li>` to `- ` prefix and `</li>` to newline.
- Insert blank lines before/after `<ul>` and `<ol>`.
Edge cases:
- Nested lists should indent by a fixed number of spaces (optional).
- Empty list items should be dropped or rendered as `-`.

### 3) Preserve Headings as Section Markers
Goal: make section boundaries visible in plain text.
Approach:
- Convert `<h1>`..`<h6>` to line prefixes such as:
  - `# ` for h1, `## ` for h2, etc.
  - Or `H1: `, `H2: ` if Markdown style is undesired.
Edge cases:
- Multiple headings with blank lines should not collapse together.

### 4) Table Fallback Formatting
Goal: keep table content readable when structure cannot be preserved.
Approach:
- Convert `<tr>` to newline, `<td>/<th>` to delimiter (`\t` or `,`).
- Default delimiter: `\t`. Allow configuration (e.g., `--table-delim`).
Edge cases:
- Preserve cell order; trim trailing delimiters.

### 5) Control and Zero-Width Character Handling
Goal: remove confusing or unsafe characters explicitly.
Approach:
- Strip or replace control characters and zero-width characters.
- Default to removal; allow `--replace-char` (e.g., `?` or space).
- Suppress long sequences after 1-2 replacements.
Edge cases:
- Preserve `\n` and `\t` before whitespace normalization.

### 6) Configurable Non-ASCII Policy
Goal: make ASCII policy explicit and traceable.
Approach:
- Keep current default (remove non-ASCII).
- Add option: replace with `?` or a single space.
- Emit count of removed or replaced characters.

### 7) Simple Counters for Impact
Goal: quantify what sanitization removed or altered.
Approach:
- Count removed tags, stripped script/style blocks, and removed characters.
- Report counts via warnings after processing.

### 8) Preserve Code/Pre Blocks
Goal: avoid collapsing code examples into a single line.
Approach:
- Convert `<pre>` and `<code>` to newline blocks and avoid
  aggressive whitespace collapse inside them.
Edge cases:
- If full preservation is too complex, keep line breaks and trim ends.

## Suggested Flag Additions
- `--table-delim {tab,comma}` or `--table-delim "\t"`.
- `--replace-char "?"` for suspicious/removed characters.
- `--ascii-replace` to replace non-ASCII instead of removing.
- `--keep-code` to preserve code block line breaks.

## Implementation Notes
- Apply link/list/heading/table transformations before tag stripping.
- Keep transformations ordered: links -> block tags -> lists -> tables -> strip.
- Avoid double-normalizing whitespace; collapse only after structure markers.
- Ensure any replacement characters remain ASCII.

## Testing and Validation Plan

### Unit Tests (new or expanded)
Target: `clean_text()` and any helper functions.

1) Links
Input: `<a href="https://x">Go</a>`
Output: `Go (https://x)\n`

2) Lists
Input: `<ul><li>One</li><li>Two</li></ul>`
Output:
```
- One
- Two
```

3) Headings
Input: `<h2>Title</h2>Body`
Output:
```
## Title
Body
```

4) Tables
Input: `<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>`
Output:
```
A\tB
1\t2
```

5) Control/zero-width
Input: `A\u200B B`
Output: `A B` (or `A? B` if configured)

6) Non-ASCII
Input: `Caf\u00e9`
Output: `Cafe` (remove) or `Caf?` (replace)

7) Script/style removal
Input: `<script>alert(1)</script>OK`
Output: `OK`

8) MySQL escapes
Input: `Line1\\nLine2`
Output:
```
Line1
Line2
```

### Integration Tests (CLI)
Target: `pages_text.py` execution.

- Minimal `db.out` with one row and `pages.list` with the title.
- Run `pages_text.py` and assert output file content and warnings.
- Include a case with a missing page to ensure warning is emitted.
- Validate ASCII-only output by asserting no non-ASCII bytes exist.

### Validation and Regression Checks
- Verify footer stripping behavior remains unchanged.
- Verify `--footer` keeps the footer section intact.
- Verify `--permit*` handling still controls parsing strictness.
- Confirm new warnings do not appear in strict mode unless configured.

## Risks and Tradeoffs
- Regex-based parsing can still mis-handle malformed HTML.
- Aggressive normalization may remove intended formatting.
- Link handling without URL validation can preserve unsafe URLs as text.
- Table fallback may be lossy; delimiter choice affects downstream usage.

## Next Steps
- Implement link/list/heading/table pre-strip steps.
- Add control/zero-width handling and non-ASCII policy counters.
- Update tests to cover each new transform.
