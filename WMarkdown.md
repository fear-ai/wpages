WMarkdown: Markdown output status, validation, and plan

Scope
- Track Markdown output behavior in pages_content.py, validation coverage, and planned improvements.
- This file complements PContent.md (behavior) and tests/TESTS.md (validation execution).

Current Markdown support
- Headings: h1–h6 to #..###### lines.
- Lists: ul/ol/li to bullets or numbered items; nested lists are flattened.
- Tables: table/tr/th/td to pipe-delimited rows; no header separator row.
- Links: <a> to [text](url); images to ![alt](src).
- Code: <pre>/<code> to fenced blocks; inline <code> uses backticks.
- Block tags: paragraph and block elements become line breaks.
- Scripts/styles/comments removed; remaining tags stripped.

Current validation (input-side)
- Warnings for malformed list and table structures in the HTML input.
- Unit/CLI tests cover Markdown conversion of headings, lists, tables, links/images, and code blocks.
- No explicit validation of Markdown output syntax.

Planned improvements

A) Add Markdown validation (active)
Goal
- Detect Markdown output issues early (even if HTML input is valid), and warn when output may be malformed or lossy.

Validation checks (initial set)
- Code fences: ensure opening/closing fence counts are balanced.
- Inline code: detect unescaped backticks inside code spans.
- Links/images: warn when output URL is empty after scheme filtering or missing schemes.
- Tables: warn when rows have inconsistent column counts or empty header separator (when/if added).

Implementation plan
1) Add a validation pass to the Markdown pipeline in pages_content.py (post-conversion).
2) Emit warnings without failing the run.
3) Reuse existing count/warning plumbing to include a “Markdown validation warnings” count.
4) Gate validation behind a flag if needed (default on in markdown mode).

Test plan
- Unit tests that feed Markdown output into the validator for each case.
- CLI tests in markdown mode that assert warnings for malformed output.

B) Expand tests for Markdown (active)

Tables
- Thead with th: ensure header row is emitted and flagged when separators are missing.
- Mixed th/td: confirm consistent column counts and warning on mismatch.
- Empty cells: confirm empty placeholders are preserved, not collapsed.
- Malformed table HTML: ensure warnings propagate and Markdown output stays readable.

Links/images
- Missing scheme (//example.com): ensure warning and marker behavior is consistent.
- Blocked schemes (javascript:, data:): ensure suppression and warning counts are correct.
- Empty href/src: ensure output uses placeholder text and warns.
- Title attributes: ensure they do not corrupt Markdown syntax.

C) Preserve nested list depth (active)

Explanation
- Current Markdown output flattens nested lists, which loses hierarchy and can change meaning.
- Preserving depth means indenting nested list items (e.g., 2 spaces per level) while keeping the correct bullet or numbering.

Implementation outline
- Track list depth during HTML conversion.
- Emit indentation prefix for each list item based on depth.
- Keep numbering per depth for ordered lists.
- Keep flattening as a fallback if structure is malformed.

Postponed improvements
- Add Markdown table header separators (defer until validation + tests are in place).
- Leave inline HTML instead of stripping unknown tags (policy decision deferred).
- Add strict/abort mode for Markdown output (defer until validation is stable).

References
- PContent.md for Markdown conversion rules.
- tests/TESTS.md for current coverage and fixtures.
