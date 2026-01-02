Tests for WPages tooling

Applicability:
- pages_list.py CLI tests validate stdout CSV (including content_bytes, the UTF-8 byte length of post_content) and stderr warnings/errors; warnings are non-fatal (exit 0) and errors exit 1 with only stderr output.
- pages_text.py CLI tests validate output .text files per focus name.
- pages_content.py CLI tests validate output .txt files per focus name and content formatting options.
- pages_db.py unit tests validate parse_dump behavior and index helpers.
- pages_focus.py unit tests validate focus list parsing and matching helpers.
- pages_cli.py unit tests validate CLI helpers (limits, parsing errors, warning emission).
- pages_text.py unit tests validate clean_text behavior.
- pages_util.py unit tests validate shared helper behavior (decode_mysql_escapes, safe_filename, strip_footer), including filename edge cases (trailing dots/spaces, long extensions, empty-base collisions).
- pages_content.py unit tests validate clean_content and clean_md behavior.

Coverage focus:
- This document enumerates CLI/unit checks, fixtures, and expected outputs used to validate behavior.
- See PList.md, PText.md, and PContent.md for program behavior details.

Runner and conventions:
- Run all tests: ./tests/run_tests.sh [--results PATH]
- Run a group: ./tests/run_tests.sh --group all|cli|list|text|content|unit
- Run pages_db tests only: python tests/test_pages_db.py
- Run pages_focus tests only: python tests/test_pages_focus.py
- Run pages_cli tests only: python tests/test_pages_cli.py
- The runner writes stdout/stderr/status per test under tests/results_YYYYMMDD_HHMMSS*/; override with --results or RESULTS.
- Diff files are always created for stdout/file comparisons; empty .diff means no differences and non-empty .diff holds the mismatch details.
- Order is the group order in tests/run_tests.sh; --group all runs unit tests first, then list and text CLI tests.
- results_YYYYMMDD_HHMMSS* directories are run artifacts and should be ignored.
- Optional dump rows: pass --rows DIR to any CLI to dump raw row values to numbered .txt files.

File types:
- *.out: mysql tab dump fixtures with a header row and tab-delimited values (ignored by git via *.out).
- *.tsv: mysql tab dump fixtures that must be preserved/versioned (same format as *.out).
- *.list: pages.list fixtures (comma- or newline-separated names).
- *_expected.csv: expected CSV output from pages_list.py.
- *_expected.txt: expected text output from pages_text.py/pages_content.py.
- *.md: expected Markdown output from pages_content.py (--format markdown).

Fixtures:
- *.out files are small mysql tab dumps with a header row and tab-delimited column values.
- *.tsv files use the same format as *.out.
- *.list files are pages.list entries (one per line or comma-separated) matched against post_title.
- tests/no_pages_list/ and tests/empty_pages_list/ are working directories for missing/empty default pages.list.
- Expected outputs live in tests/*_expected.csv, tests/default_expected.list, tests/pages_text_*_expected.txt, and tests/*.md for Markdown output.

Input fixtures:
- tests/sample.out: valid header and 8 rows; includes duplicate titles (Home), case variation (Contact/contact), and mixed statuses to exercise pick_best.
- tests/malformed.out: valid header with one malformed row missing columns, plus one valid row.
- tests/bad_header.out: invalid header (missing post_content column) to trigger a hard error.
- tests/oversized.out: valid header with one long post_content column value to trigger --bytes skipping.
- tests/alt_header.out: header names out of order to exercise --permit-header.
- tests/duplicate_id.out: valid header with a repeated id to trigger duplicate-id warnings.
- tests/missing_row.out: valid header with a single row to exercise missing focus warnings.
- tests/escapes.out: valid header with backslash-escaped tab/newline to exercise --notab/--nonl.
- tests/sample.list: Home/About/Contact for basic exact matching.
- tests/sample_glitch.list: Home/About/Contact with commas, whitespace, and blanks to test list parsing.
- tests/prefix.list: Con/About to exercise prefix matching and ordering.
- tests/prefix_only.list: Con to exercise --prefix/--noprefix behavior.
- tests/prefix_overlap.list: Con/Contac to exercise longest-prefix labeling.
- tests/dups.list: Home repeated to trigger duplicate-name warnings.
- tests/case.list: Contact to exercise case-sensitive vs case-insensitive matches.
- tests/case_dups.list: Contact/contact to trigger case-insensitive duplicate warnings.
- tests/empty.list: empty list file for --only error handling.
- tests/invalid.list: commas/whitespace only (no names) to trigger --only empty-list error.
- tests/missing_page.list: focus list with one missing entry to trigger missing-page warnings.
- tests/content.out: HTML-heavy content and a row with non-ASCII/zero-width characters for pages_content tests.
- tests/content_counts.tsv: HTML with malformed list/table tags and mixed schemes (missing/blocked/non-HTTP) for CLI warning coverage.
- tests/content.list: HTML/Dirty entries for pages_content CLI tests.
- tests/content_counts.list: Counts entry for content_counts.tsv.
- tests/escapes.list: Escapes entry for escapes.out CLI tests.

Expected outputs:
- tests/default_expected.csv: default run output (focus first, then all rows).
- tests/all_rows_expected.csv: output with empty focus list (all rows, input order).
- tests/details_sample_expected.csv: details output for sample.out with sample.list.
- tests/details_oversized_expected.csv: details output for oversized.out with sample.list.
- tests/details_missing_expected.csv: details output for missing_row.out with missing_page.list.
- tests/pages_text_home_expected.txt: expected cleaned output for Home (sample.out).
- tests/pages_text_about_expected.txt: expected cleaned output for About (sample.out).
- tests/pages_text_contact_expected.txt: expected cleaned output for Contact (sample.out).
- tests/pages_text_dirty_utf_expected.txt: expected cleaned output for Dirty with --utf (content.out).
- tests/pages_text_dirty_raw_expected.txt: expected cleaned output for Dirty with --raw (content.out).
- tests/pages_content_html_expected.txt: expected pages_content output for HTML (default comma delimiter).
- tests/pages_content_dirty_expected.txt: expected pages_content output for Dirty with default removal.
- tests/pages_content_html_tab_expected.txt: expected pages_content output for HTML with tab delimiter.
- tests/pages_content_dirty_replace_expected.txt: expected pages_content output for Dirty with replacement character.
- tests/pages_content_dirty_utf_expected.txt: expected pages_content output for Dirty with --utf.
- tests/pages_content_dirty_raw_expected.txt: expected pages_content output for Dirty with --raw.
- tests/escapes_notab_nonl_expected.txt: expected output for Escapes with --notab/--nonl.
- tests/pages_content_html.md: expected pages_content Markdown output for HTML.
- tests/pages_content_row.md: expected pages_content Markdown output for Dirty.

Unit tests (by module):

pages_db.py unit tests:
- tests/test_pages_db.py covers empty file, bad header, malformed rows (strict vs non-strict), limits, csv-in parsing on a normal fixture, embedded newlines in raw dumps, and CR-only newlines.
- parse_dump covers CRLF and LF newline handling and strict_header=False coverage with header_mismatch stats.
- Coverage includes FileNotFoundError, invalid id/status/date counts, duplicate id count, index helpers, and pick_best.
- parse_dump includes a csv-in test with an escaped delimiter (backslash + tab) and confirms the default split misparses that case.

pages_focus.py unit tests:
- tests/test_pages_focus.py covers load_focus_list dedupe behavior, build_rows_keys normalization, match_entries selection, match_focus_entry selection, and match_label precedence.

pages_cli.py unit tests:
- tests/test_pages_cli.py covers limit validation, common argument parsing, missing-file and unreadable-file errors, parse errors, and strict vs non-strict warning emission via emit_db_warnings.

Test helpers:
- tests/test_pages.py provides the shared CompactRunner and path setup used by the unit tests.

CLI integration tests:

pages_list.py CLI tests (basic and matching):
Base: python3 pages_list.py --input tests/sample.out --pages tests/sample.list
- Defaults: Base -> stdout tests/default_expected.csv.
- Optional output files: Base --output-dir DIR writes pages.csv and pages.list to DIR (stdout is suppressed).
- Exact match: Base --only -> stdout tests/sample_only_expected.csv.
- CSV-in mode: Base --only --csvin -> stdout tests/sample_only_expected.csv.
- Prefix enabled: Base with --pages tests/prefix_only.list --only --prefix -> stdout tests/prefix_only_expected.csv.
- Prefix disabled (details): Base with --pages tests/prefix_only.list --details --noprefix -> stdout tests/prefix_noprefix_expected.csv.
- Case-sensitive default: Base with --pages tests/case.list --only -> stdout tests/case_sensitive_expected.csv.
- Case-insensitive override: Base with --pages tests/case.list --only --nocase -> stdout tests/case_nocase_expected.csv.
- Glitchy list parsing: Base with --pages tests/sample_glitch.list --only -> stdout tests/sample_only_expected.csv.

pages_list.py CLI tests (details, prefix, and overlap):
Base: python3 pages_list.py --input tests/sample.out --pages tests/sample.list --details
- Details mode: Base -> stdout tests/details_sample_expected.csv.
- Prefix + details: Base with --pages tests/prefix.list -> stdout tests/prefix_details_expected.csv.
- Prefix overlap: Base with --pages tests/prefix_overlap.list -> stdout tests/prefix_overlap_expected.csv.

pages_list.py CLI tests (warnings and limits):
Base: python3 pages_list.py --input tests/sample.out --pages tests/sample.list
- Oversized line skip: python3 pages_list.py --input tests/oversized.out --pages tests/sample.list --details -> stdout tests/details_oversized_expected.csv.
- Permit header mismatch: python3 pages_list.py --input tests/alt_header.out --pages tests/sample.list --only --permit-header -> stdout tests/permit_header_expected.csv, stderr contains "Warning: Header error".
- Permit malformed rows: python3 pages_list.py --input tests/malformed.out --pages tests/sample.list --permit-columns -> stdout tests/permit_columns_expected.csv, stderr contains "Info: Malformed row count: 1".
- Permit both: python3 pages_list.py --input tests/alt_header.out --pages tests/sample.list --only --permit -> stdout tests/permit_header_expected.csv, stderr contains "Warning: Header error".
- Duplicate focus names: Base with --pages tests/dups.list --only -> stderr contains "Warning: Duplicate page name skipped: Home".
- Duplicate focus names (nocase): Base with --pages tests/case_dups.list --only --nocase -> stderr contains "Warning: Duplicate page name skipped: contact".
- Duplicate id warning: python3 pages_list.py --input tests/duplicate_id.out --pages tests/sample.list --only -> stderr contains "Info: Duplicate id count: 1".
- Missing focus warning: python3 pages_list.py --input tests/missing_row.out --pages tests/missing_page.list --details -> stderr contains "Warning: Missing page: Missing".
- Line limit: Base --only --lines 2 -> stderr contains "Warning: Line limit reached at line 2."

pages_list.py CLI tests (errors and missing lists):
Base: python3 pages_list.py --input tests/sample.out --pages tests/sample.list
- Malformed row error: python3 pages_list.py --input tests/malformed.out --pages tests/sample.list --details -> stderr contains "Error: Malformed row at line 2 in tests/malformed.out: expected 5 columns, got 4".
- Bad header error: python3 pages_list.py --input tests/bad_header.out --pages tests/sample.list --details -> stderr contains "Error: Header error in tests/bad_header.out:".
- --only with --details: Base with --pages tests/prefix.list --only --details -> stderr contains "Error: --only cannot be used with --details."
- Invalid --lines: Base --only --lines -1 -> stderr contains "Error: --lines must be 0 or a positive integer."
- Invalid --bytes: Base --only --bytes -1 -> stderr contains "Error: --bytes must be 0 or a positive integer."
- Missing pages list file: Base with --pages tests/missing.list --only -> stderr contains "Error: pages list file not found: tests/missing.list".
- Empty pages list file: Base with --pages tests/empty.list --only -> stderr contains "Error: pages list must include at least one page name."
- Invalid pages list file: Base with --pages tests/invalid.list --only -> stderr contains "Error: pages list must include at least one page name."
- Missing default pages list file: (cd tests/no_pages_list && python3 ../pages_list.py --input ../tests/sample.out --only) -> stderr contains "Error: pages list file not found: pages.list".
- Empty default pages list file: (cd tests/empty_pages_list && python3 ../pages_list.py --input ../tests/sample.out --only) -> stderr contains "Error: pages list must include at least one page name."
- Empty pages list file (not --only): Base with --pages tests/empty.list -> stdout tests/all_rows_expected.csv.
- Invalid pages list file (not --only): Base with --pages tests/invalid.list -> stdout tests/all_rows_expected.csv.

pages_text.py CLI tests:
Base (sample): python3 pages_text.py --input tests/sample.out --pages tests/sample.list --output-dir DIR
- Basic extraction: Base -> Home.text, About.text, Contact.text match tests/pages_text_*_expected.txt.
- Optional dump notags: Base --notags writes `<Page>_notags.txt` dump notags alongside output files (existence is checked).
- Output directory creation: Base with DIR=<new_dir> creates the directory and writes expected files.
- Output directory error: Base with DIR=<file_path> exits with "output path is not a directory".

Base (missing): python3 pages_text.py --input tests/missing_row.out --pages tests/missing_page.list --output-dir DIR
- Missing focus warning: Base -> stderr contains "Warning: Missing page: Missing" and does not write Missing.txt.

Base (content): python3 pages_text.py --input tests/content.out --pages tests/content.list --output-dir DIR
- UTF-8 output: Base --utf -> Dirty.text matches tests/pages_text_dirty_utf_expected.txt.
- Raw output: Base --raw -> Dirty.text matches tests/pages_text_dirty_raw_expected.txt.

Base (escapes): python3 pages_text.py --input tests/escapes.out --pages tests/escapes.list --output-dir DIR
- No tabs/newlines: Base --notab --nonl -> Escapes.text matches tests/escapes_notab_nonl_expected.txt.

pages_content.py CLI tests:
Base (sample): python3 pages_content.py --input tests/sample.out --pages tests/sample.list --output-dir DIR
- Basic extraction: Base -> Home.txt, About.txt, Contact.txt match tests/pages_text_*_expected.txt.
- Optional dump notags: Base --notags writes `<Page>_notags.txt` dump notags alongside output files (existence is checked).
- Output directory creation and error cases mirror pages_text.py.

Base (content): python3 pages_content.py --input tests/content.out --pages tests/content.list --output-dir DIR
- HTML fixture: Base -> HTML.txt, Dirty.txt match pages_content expected outputs.
- Table delimiter: Base --table-delim tab uses tabs between table cells.
- Replacement character: Base --replace "?" replaces stripped characters in Dirty.txt.
- Replacement character validation: Base --replace "??" exits with an error.
- Markdown output: Base --format markdown -> HTML.md, Dirty.md match Markdown expected outputs.
- Dual output: Base --format both -> HTML.txt/Dirty.txt and HTML.md/Dirty.md in the same run.
- UTF-8 output: Base --utf -> Dirty.txt matches tests/pages_content_dirty_utf_expected.txt.
- Raw output: Base --raw -> Dirty.txt matches tests/pages_content_dirty_raw_expected.txt.

Base (missing): python3 pages_content.py --input tests/missing_row.out --pages tests/missing_page.list --output-dir DIR
- Missing focus warning: Base -> stderr contains "Warning: Missing page: Missing" and does not write Missing.txt.

Base (escapes): python3 pages_content.py --input tests/escapes.out --pages tests/escapes.list --output-dir DIR
- No tabs/newlines: Base --notab --nonl -> Escapes.txt matches tests/escapes_notab_nonl_expected.txt.

Base (counts): python3 pages_content.py --input tests/content_counts.tsv --pages tests/content_counts.list --output-dir DIR
- Emits warnings for malformed list/table structure and missing/non-HTTP scheme links, plus Info counts for blocks/tags/entities and blocked scheme links.
- Markdown variant: Base --format markdown also warns for non-HTTP scheme images.

pages_text.py unit tests:
- tests/test_pages_text.py covers script/style/comment stripping, entity stripping, MySQL escape decoding, whitespace handling, character filtering, raw-mode preservation, and --notab/--nonl behavior.
- Coverage includes FilterCounts integration (control/zero-width/tab/newline/non-ASCII removals and replacement char counts) through clean_text.

pages_content.py unit tests:
- tests/test_pages_content.py covers links, entities, headings, lists (including nested lists), tables, MySQL escapes, block removal, ASCII output, raw-mode preservation, --notab/--nonl behavior, and Markdown conversions (including adjacency and title escaping).
- Coverage highlights: text output link conversion (including titles and blocked schemes), table delimiter handling, zero-width removal/replacement, Markdown headings/lists/tables (including ordered lists), image/link conversion (including titles and blocked schemes), pre/code handling (including attributes and mixed nesting), and list/table malformed tag warnings.
- Coverage includes SanitizeCounts and FilterCounts integration (blocks/tags/entities removed, conversions, missing/blocked/other scheme counts, and filter removal counts).
- Gaps and problems: no tests for bidi controls or data URIs beyond scheme blocking; Markdown does not emit table header separators; regex parsing can mis-handle `>` inside quoted attributes.

Test issues and gaps (pending):
- Raw dumps with embedded tabs/newlines are expected to error (covered by unit tests).
- No tests for unescaping backslash sequences in column values (not implemented).
- No tests for file size heuristics (not implemented).
- No tests for focus list encoding error policy (currently errors="replace").
- No tests for focus list streaming or large-file performance.
- (Filled) Missing-page warnings are now covered by pages_text_missing/pages_content_missing CLI tests.
- Postponed: performance/scale testing (large fixtures, streaming benchmarks).
- Postponed: shared sanitization refactor between text/content (design alignment needed).
- Postponed: additional filename edge-case tests beyond the current set.
