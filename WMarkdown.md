WMarkdown: Markdown output status, validation, and plan

Scope
- Track Markdown output behavior in pages_content.py, validation coverage, and planned improvements.
- This file complements PContent.md (behavior) and tests/TESTS.md (validation execution).

Current Markdown support
Primitives
- Headings: h1–h6 to #..###### lines.
- Emphasis: <strong>/<b> to **, <em>/<i> to *.
- Inline code: <code> to backticks (no adjacency spacing beyond link/image handling).
- Links: <a> to [text](url); titles preserved and escaped in markdown output.
- Images: <img> to ![alt](src); titles preserved and escaped in markdown output.

Structures
- Lists: ul/ol/li to bullets or numbered items; nested lists are flattened.
- Tables: table/tr/th/td to pipe-delimited rows; no header separator row.
- Code blocks: <pre>/<code> to fenced blocks.
- Paragraphs and block tags become blank-line separators.

Stripping and decoding
- Scripts/styles/comments removed; remaining tags stripped.
- HTML entities are decoded before character filtering.

Current validation (input-side)
- Warnings for malformed list and table structures in the HTML input.
- Unit/CLI tests cover Markdown conversion of headings, lists, tables, links/images, and code blocks.
- No explicit validation of Markdown output syntax.

Planned improvements

A) Add Markdown validation (active)
Goal
- Detect Markdown output issues early (even if HTML input is valid), and warn when output may be malformed or lossy.

Requirements
- Add a Markdown validator that reports counts for common output issues.
- Run validation after Markdown conversion and emit warnings in CLI output.
- Keep validation non-fatal (warnings only).

Validator output
- Emits per-page warnings to stderr (same channel as existing structure warnings).
- Warnings are non-fatal and include counts when multiple issues are detected.
- Intended format: \"Warning: Markdown validation: <issue> <count> in page '<Page>'\".

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

Detailed implementation and validation tasks
- Code:
  - Add a Markdown validator function (e.g., validate_markdown) that returns issue counts.
  - Call validator after clean_md and emit per-issue warnings in pages_content.py.
  - Optional: add a flag to disable validation (default on).
- Tests:
  - Unit tests for each validator rule (fences, inline code, empty URLs, table mismatch).
  - CLI tests with a markdown fixture that triggers warnings and asserts stderr lines.

B) Expand tests for Markdown (active)

Tables
Done
- Thead with th: output verified for thead/tbody rows.
- Mixed th/td: output verified for mixed header/data rows.
- Empty cells: output verified with empty-leading cells.
- Malformed table HTML: output verified (readable fallback).

Links/images
Done
- Missing scheme (//example.com): output verified with scheme marker.
- Blocked schemes (javascript:, data:): output verified with suppression marker and counts.
- Empty href/src: output verified to fall back to label text.
- Title attributes: output verified with escaped quotes in markdown titles.

Done
- Title attributes are now escaped for Markdown safety (quotes and newlines).
- Adjacency tests for inline code and link/image sequences added.
- Tables and link/image cases expanded in unit tests.

Incremental vs tests-only
- Code changes required:
  - Add a Markdown validation pass and emit warnings for fence imbalance, broken inline code, empty URLs, and table column mismatch.
  - Ensure warning counts are wired through existing stderr/info reporting in markdown mode.
- Tests-only once validation exists:
  - Unit tests for each validator rule.
  - CLI tests that assert warnings for malformed output.
- Tests-only for existing behavior:
  - Verify pipe output for thead/th, mixed th/td, empty cells, and malformed table HTML.
  - Verify link/image output for missing scheme, blocked scheme, empty href/src, and title attributes.

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
