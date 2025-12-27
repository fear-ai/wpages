Status for WPages tooling and tests

Documents
- WPages.md documents the WordPress page dump workflow, requirements, and usage guidance.
- HStrip.md documents content sanitization policies and considerations.
- PText.md documents pages_text.py cleaning behavior and improvements.
- PContent.md documents pages_content.py extraction behavior.
- Status.md tracks implementation state, decisions, and backlog items.
- tests/TESTS.md documents fixture-based CLI tests and runner usage.

Environment
- Python 3 is required; scripts use the standard library only.
- CLI scripts run locally, read/write the filesystem, and write results to stdout/stderr.
- No network access or external services are required.

Progress
- pages_content.py now supports Markdown output, ordered list numbering, link/image titles, scheme blocking, and list/table structure warnings.
- Tests split into list/text/content/unit groups, with new content-focused coverage in tests/test_pages_content.py.

Implementation
- pages_db.py: parse_dump returns rows + stats with limits, csv mode, and newline="\\n" to avoid CR splitting; trims trailing CR/LF and strips leading CR to tolerate LFCR; warnings emitted via pages_cli.py.
- pages_cli.py: shared CLI options include `--rows` to dump raw row values for debugging.
- pages_focus.py: focus list parsing and match_entries encapsulate matching behavior; warnings on duplicate focus names.
- pages_list.py: CLI list output and matching behavior documented in WPages.md and PList.md.
- pages_util.py: shared helpers for output paths and text cleanup (decode_mysql_escapes, strip_footer, and safe_filename with Windows-safe ASCII rules, 255-byte cap, and `_N` suffixing).
- pages_text.py: legacy cleaner; strips tags/entities, filters control/zero-width/non-ASCII with default space replacement (overridable via --replace, plus --raw/--utf/--nonl/--notab), writes ASCII by default (UTF-8 for --utf/--raw), and supports `--notags` dump notags after tag stripping; behavior documented in PText.md.
- pages_content.py: text/Markdown extraction, scheme blocking, ordered lists, structural warnings, and optional `--notags` dump notags after tag stripping; character filtering replaces control/zero-width/non-ASCII with space by default or `--replace` (suppressed per run); behavior documented in PContent.md.
- tests: runner groups are documented in tests/TESTS.md.

Module partitioning
- pages_db.py: dump parsing, header/row validation, size/line limits, parse stats.
- pages_focus.py: focus list parsing, dedupe, normalization, and matching logic.
- pages_cli.py: shared CLI options, input validation, error/warning emission.
- pages_list.py: list-mode CLI output (CSV) and focus/details listing behavior.
- pages_text.py: plain text extraction policy and output files.
- pages_content.py: structure-aware extraction and Markdown/text output policy.
- pages_util.py: shared output-layer helpers (escape decoding, footer stripping, filenames).

Filenames
- safe_filename applies Windows-safe ASCII rules: NFKD + drop non-ASCII, invalid
  character replacement, whitespace/dot trimming, 255-byte cap (ext preserved),
  reserved-name suffixing, and `_N` collision suffixes.

Decisions
1) Raw dump handling (embedded tabs/newlines) postponed; expect mysql -e tab output.
2) Backslash unescaping policy postponed.
3) Row integrity and validation remain warnings; dedupe and error escalation postponed; possible policies include keep first/keep best/aggregate focus names and suppressing prefix hits after exact matches.
4) File size heuristic postponed.
5) Focus list streaming postponed.
6) Focus list encoding error policy postponed.

Concerns
1) Input brittleness: raw dumps with literal tabs/newlines will misparse unless using mysql -e or --csv (see Decisions 1 and 2).
2) Warning visibility: parse_dump returns stats only; non-CLI callers must surface warnings explicitly (see Decision 3).
3) Memory scale: rows and content live in memory; large dumps need limits or profiling (see Decisions 4 and 5).
4) Character removal/replacement is now summarized as Info counts per page (control/zero-width/tab/newline/non-ASCII removals and replacement chars). Sanitization steps (tags/blocks/entities) also emit Info counts. Data loss is still possible when ASCII-only output is used.

Pending
- Raw dump/backslash unescaping decisions (see Decisions 1-2).
- File size heuristics and streaming approach (see Decisions 4-5).
- Focus list encoding error policy (see Decision 6).
- URL normalization policy beyond scheme blocking (see HStrip.md).
 - Removal/replacement reporting policy (counts vs warnings) for sanitization steps (see HStrip.md).
- Revisit filename edge-case test coverage (trailing dots/spaces, long extensions, empty-base suffixing).
- Revisit UTF-8 + Markdown output tests (CLI and unit coverage).
- Revisit sharing HTML/entity stripping between pages_text.py and pages_content.py.

TODO
- Add progress reporting for long runs (every N lines and matches).
- Report when --lines truncates input or when oversized lines are skipped outside CLI warnings.
- Use a prefix index or sorted list for details labeling to reduce O(R x F) scans.
- Type pages_list emit_row output with a TypedDict or small dataclass for clarity.
