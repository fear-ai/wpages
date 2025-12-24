Tests for WPages tooling

Applicability:
- pages_list.py CLI tests validate stdout CSV and stderr warnings/errors; warnings are non-fatal (exit 0) and errors exit 1 with only stderr output.
- pages_text.py CLI tests validate output .txt files per focus name.
- pages_db.py unit tests validate parse_dump behavior and index helpers.
- pages_focus.py unit tests validate focus list parsing and matching helpers.
- pages_cli.py unit tests validate CLI helpers (limits, parsing errors, warning emission).

Runner and conventions:
- Run all tests: ./tests/run_tests.sh [--results PATH]
- Run pages_db tests only: python tests/test_pages_db.py
- Run pages_focus tests only: python tests/test_pages_focus.py
- Run pages_cli tests only: python tests/test_pages_cli.py
- The runner writes stdout/stderr/status per test under tests/results_YYYYMMDD_HHMMSS*/; override with --results or RESULTS.
- Diff files are always created for stdout/file comparisons; empty .diff means no differences and non-empty .diff holds the mismatch details.
- Order is the script order in tests/run_tests.sh (basic CLI cases first, error cases later, unit tests last).

Fixtures:
- *.out files are small mysql tab dumps with a header row and tab-delimited column values.
- *.list files are pages.list entries (one per line or comma-separated) matched against post_title.
- tests/no_pages_list/ and tests/empty_pages_list/ are working directories for missing/empty default pages.list.
- Expected outputs live in tests/*_expected.csv and tests/pages_text_*_expected.txt.

Input fixtures:
- tests/sample.out: valid header and 8 rows; includes duplicate titles (Home), case variation (Contact/contact), and mixed statuses to exercise pick_best.
- tests/malformed.out: valid header with one malformed row missing columns, plus one valid row.
- tests/bad_header.out: invalid header (missing post_content column) to trigger a hard error.
- tests/oversized.out: valid header with one long post_content column value to trigger --bytes skipping.
- tests/alt_header.out: header names out of order to exercise --permit-header.
- tests/duplicate_id.out: valid header with a repeated id to trigger duplicate-id warnings.
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

Expected outputs:
- tests/default_expected.csv: default run output (focus first, then all rows).
- tests/all_rows_expected.csv: output with empty focus list (all rows, input order).
- tests/details_sample_expected.csv: details output for sample.out with sample.list.
- tests/details_oversized_expected.csv: details output for oversized.out with sample.list.
- tests/pages_text_home_expected.txt: expected cleaned output for Home (sample.out).
- tests/pages_text_about_expected.txt: expected cleaned output for About (sample.out).
- tests/pages_text_contact_expected.txt: expected cleaned output for Contact (sample.out).

Unit tests (by module):

pages_db.py unit tests:
- tests/test_pages_db.py covers empty file, bad header, malformed rows (strict vs non-strict), limits, and use_csv on a normal fixture.
- parse_dump includes mixed newline handling (\r\n, \n\r, \n, \r) and strict_header=False coverage with header_mismatch stats.
- Coverage includes FileNotFoundError, invalid id/status/date counts, duplicate id count, index helpers, and pick_best.
- parse_dump includes a use_csv test with an escaped delimiter (backslash + tab) and confirms the default split misparses that case.

pages_focus.py unit tests:
- tests/test_pages_focus.py covers load_focus_list dedupe behavior, build_rows_keys normalization, match_focus_entry selection, and match_label precedence.

pages_cli.py unit tests:
- tests/test_pages_cli.py covers limit validation, common argument parsing, missing-file and unreadable-file errors, parse errors, and strict vs non-strict warning emission via emit_db_warnings.

Test helpers:
- tests/test_pages.py provides the shared CompactRunner and path setup used by the unit tests.

CLI integration tests:

pages_list.py CLI tests (basic and matching):
- Defaults: python3 pages_list.py --input tests/sample.out --pages tests/sample.list -> stdout tests/default_expected.csv.
- Exact match: python3 pages_list.py --input tests/sample.out --pages tests/sample.list --only -> stdout tests/sample_only_expected.csv.
- CSV mode: python3 pages_list.py --input tests/sample.out --pages tests/sample.list --only --csv -> stdout tests/sample_only_expected.csv.
- Prefix enabled: python3 pages_list.py --input tests/sample.out --pages tests/prefix_only.list --only --prefix -> stdout tests/prefix_only_expected.csv.
- Prefix disabled (details): python3 pages_list.py --input tests/sample.out --pages tests/prefix_only.list --details --noprefix -> stdout tests/prefix_noprefix_expected.csv.
- Case-sensitive default: python3 pages_list.py --input tests/sample.out --pages tests/case.list --only -> stdout tests/case_sensitive_expected.csv.
- Case-insensitive override: python3 pages_list.py --input tests/sample.out --pages tests/case.list --only --nocase -> stdout tests/case_nocase_expected.csv.
- Glitchy list parsing: python3 pages_list.py --input tests/sample.out --pages tests/sample_glitch.list --only -> stdout tests/sample_only_expected.csv.

pages_list.py CLI tests (details, prefix, and overlap):
- Details mode: python3 pages_list.py --input tests/sample.out --pages tests/sample.list --details -> stdout tests/details_sample_expected.csv.
- Prefix + details: python3 pages_list.py --input tests/sample.out --pages tests/prefix.list --details -> stdout tests/prefix_details_expected.csv.
- Prefix overlap: python3 pages_list.py --input tests/sample.out --pages tests/prefix_overlap.list --details -> stdout tests/prefix_overlap_expected.csv.

pages_list.py CLI tests (warnings and limits):
- Oversized line skip: python3 pages_list.py --input tests/oversized.out --pages tests/sample.list --details -> stdout tests/details_oversized_expected.csv.
- Permit header mismatch: python3 pages_list.py --input tests/alt_header.out --pages tests/sample.list --only --permit-header -> stdout tests/permit_header_expected.csv, stderr contains "Warning: Header error".
- Permit malformed rows: python3 pages_list.py --input tests/malformed.out --pages tests/sample.list --permit-columns -> stdout tests/permit_columns_expected.csv, stderr contains "Warning: Malformed row count: 1".
- Permit both: python3 pages_list.py --input tests/alt_header.out --pages tests/sample.list --only --permit -> stdout tests/permit_header_expected.csv, stderr contains "Warning: Header error".
- Duplicate focus names: python3 pages_list.py --input tests/sample.out --pages tests/dups.list --only -> stderr contains "Warning: Duplicate page name skipped: Home".
- Duplicate focus names (nocase): python3 pages_list.py --input tests/sample.out --pages tests/case_dups.list --only --nocase -> stderr contains "Warning: Duplicate page name skipped: contact".
- Duplicate id warning: python3 pages_list.py --input tests/duplicate_id.out --pages tests/sample.list --only -> stderr contains "Warning: Duplicate id count: 1".
- Line limit: python3 pages_list.py --input tests/sample.out --pages tests/sample.list --only --lines 2 -> stderr contains "Warning: Line limit reached at line 2."

pages_list.py CLI tests (errors and missing lists):
- Malformed row error: python3 pages_list.py --input tests/malformed.out --pages tests/sample.list --details -> stderr contains "Error: Malformed row at line 2 in tests/malformed.out: expected 5 columns, got 4".
- Bad header error: python3 pages_list.py --input tests/bad_header.out --pages tests/sample.list --details -> stderr contains "Error: Header error in tests/bad_header.out:".
- --only with --details: python3 pages_list.py --input tests/sample.out --pages tests/prefix.list --only --details -> stderr contains "Error: --only cannot be used with --details."
- Invalid --lines: python3 pages_list.py --input tests/sample.out --pages tests/sample.list --only --lines -1 -> stderr contains "Error: --lines must be 0 or a positive integer."
- Invalid --bytes: python3 pages_list.py --input tests/sample.out --pages tests/sample.list --only --bytes -1 -> stderr contains "Error: --bytes must be 0 or a positive integer."
- Missing pages list file: python3 pages_list.py --input tests/sample.out --pages tests/missing.list --only -> stderr contains "Error: pages list file not found: tests/missing.list".
- Empty pages list file: python3 pages_list.py --input tests/sample.out --pages tests/empty.list --only -> stderr contains "Error: pages list must include at least one page name."
- Invalid pages list file: python3 pages_list.py --input tests/sample.out --pages tests/invalid.list --only -> stderr contains "Error: pages list must include at least one page name."
- Missing default pages list file: (cd tests/no_pages_list && python3 ../pages_list.py --input ../tests/sample.out --only) -> stderr contains "Error: pages list file not found: pages.list".
- Empty default pages list file: (cd tests/empty_pages_list && python3 ../pages_list.py --input ../tests/sample.out --only) -> stderr contains "Error: pages list must include at least one page name."
- Empty pages list file (not --only): python3 pages_list.py --input tests/sample.out --pages tests/empty.list -> stdout tests/all_rows_expected.csv.
- Invalid pages list file (not --only): python3 pages_list.py --input tests/sample.out --pages tests/invalid.list -> stdout tests/all_rows_expected.csv.

pages_list.py behavior notes:
- Focus list dedupe uses normalized keys; duplicates are skipped with "Duplicate page name skipped" warnings.
- Input rows are indexed by normalized title in a dict of lists (title_index); duplicates are resolved with pick_best when selecting a focus match.
- Ordered matching uses a list of normalized keys (focus_keys); match_label returns the first exact or prefix match by focus list order.
- Not --only output tracks used IDs with a set (used_ids) so matched rows are not emitted twice.

pages_text.py CLI tests:
- Basic extraction: python3 pages_text.py --input tests/sample.out --pages tests/sample.list --output-dir <tmp> -> Home.txt, About.txt, Contact.txt match tests/pages_text_*_expected.txt.

Test issues and gaps (pending):
- No tests for raw dumps with embedded tabs/newlines (unsupported by line-based parsing).
- No tests for unescaping backslash sequences in column values (not implemented).
- No tests for file size heuristics (not implemented).
- No tests for focus list encoding error policy (currently errors="replace").
- No tests for focus list streaming or large-file performance.
- No tests for pages_text warnings when a focus name has no matching row.
