Test cases for pages_list.py and pages_db.py

Applicability:
- pages_list.py CLI tests validate stdout CSV and stderr warnings/errors; warnings are non-fatal (exit 0) and errors exit 1 with only stderr output.
- pages_db.py unit tests validate parse_dump behavior and index helpers.
- pages_focus.py unit tests validate focus list parsing and matching helpers.
- pages_cli.py unit tests validate CLI helpers (limits, parsing errors, warning emission).
- pages_text.py CLI tests validate output .txt files per focus name.

Usage:
- Run all tests: ./tests/run_tests.sh [--results PATH]
- Run pages_db tests only: python tests/test_pages_db.py
- Run pages_focus tests only: python tests/test_pages_focus.py
- Run pages_cli tests only: python tests/test_pages_cli.py

Fixtures:
- *.out files are small mysql tab dumps with a header row and tab-delimited fields.
- *.list files are focus-name lists (one per line or comma-separated).

Input files:
- tests/sample.out: valid header and 8 rows; includes duplicate titles (Home), case variation (Contact/contact), and mixed statuses to exercise pick_best.
- tests/malformed.out: valid header with one malformed row missing columns, plus one valid row.
- tests/bad_header.out: invalid header (missing post_content column) to trigger a hard error.
- tests/oversized.out: valid header with one long content field to trigger --bytes skipping.
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
- tests/no_pages_list/: directory without pages.list for default-missing error.
- tests/empty_pages_list/: directory with empty pages.list for default-empty error.
- tests/default_expected.csv: default run output (focus first, then all rows).
- tests/all_rows_expected.csv: output with empty focus list (all rows, input order).
- tests/details_sample_expected.csv: details output for sample.out with sample.list.
- tests/details_oversized_expected.csv: details output for oversized.out with sample.list.
- tests/pages_text_home_expected.txt: expected cleaned output for Home (sample.out).
- tests/pages_text_about_expected.txt: expected cleaned output for About (sample.out).
- tests/pages_text_contact_expected.txt: expected cleaned output for Contact (sample.out).

Defaults (no flags):
- Command: python3 pages_list.py --input tests/sample.out --pages tests/sample.list
- Expected stdout: tests/default_expected.csv

Basic exact match (default exact + case-sensitive):
- Command: python3 pages_list.py --input tests/sample.out --pages tests/sample.list --only
- Expected stdout: tests/sample_only_expected.csv

CSV parsing mode (same output on standard dump):
- Command: python3 pages_list.py --input tests/sample.out --pages tests/sample.list --only --csv
- Expected stdout: tests/sample_only_expected.csv

Prefix enabled without details:
- Command: python3 pages_list.py --input tests/sample.out --pages tests/prefix_only.list --only --prefix
- Expected stdout: tests/prefix_only_expected.csv

Prefix disabled override with details:
- Command: python3 pages_list.py --input tests/sample.out --pages tests/prefix_only.list --details --noprefix
- Expected stdout: tests/prefix_noprefix_expected.csv

Case-sensitive default:
- Command: python3 pages_list.py --input tests/sample.out --pages tests/case.list --only
- Expected stdout: tests/case_sensitive_expected.csv

Case-insensitive override:
- Command: python3 pages_list.py --input tests/sample.out --pages tests/case.list --only --nocase
- Expected stdout: tests/case_nocase_expected.csv

Glitchy list parsing (commas + whitespace):
- Command: python3 pages_list.py --input tests/sample.out --pages tests/sample_glitch.list --only
- Expected stdout: tests/sample_only_expected.csv

Prefix + details (defaults to prefix + case-insensitive):
- Command: python3 pages_list.py --input tests/sample.out --pages tests/prefix.list --details
- Expected stdout: tests/prefix_details_expected.csv

Prefix overlap details (longest prefix wins):
- Command: python3 pages_list.py --input tests/sample.out --pages tests/prefix_overlap.list --details
- Expected stdout: tests/prefix_overlap_expected.csv

Details mode with sample fixture:
- Command: python3 pages_list.py --input tests/sample.out --pages tests/sample.list --details
- Expected stdout: tests/details_sample_expected.csv

Malformed row error (details mode):
- Command: python3 pages_list.py --input tests/malformed.out --pages tests/sample.list --details
- Expected stderr: "Error: Malformed row at line 2 in tests/malformed.out: expected 5 columns, got 4"

Bad header (details mode):
- Command: python3 pages_list.py --input tests/bad_header.out --pages tests/sample.list --details
- Expected stderr: "Error: Header error in tests/bad_header.out: ..."

Oversized line skip (details mode, use small --bytes to trigger):
- Command: python3 pages_list.py --input tests/oversized.out --pages tests/sample.list --details
- Expected stdout: tests/details_oversized_expected.csv

pages_text basic extraction:
- Command: python3 pages_text.py --input tests/sample.out --pages tests/sample.list --output-dir <tmp>
- Expected files: Home.txt, About.txt, Contact.txt with the contents in tests/pages_text_*_expected.txt

Duplicate focus names (per-duplicate warning):
- Command: python3 pages_list.py --input tests/sample.out --pages tests/dups.list --only
- Expected stderr: "Warning: Duplicate page name skipped: Home"

Duplicate focus names with --nocase:
- Command: python3 pages_list.py --input tests/sample.out --pages tests/case_dups.list --only --nocase
- Expected stderr: "Warning: Duplicate page name skipped: contact"

Duplicate id warning:
- Command: python3 pages_list.py --input tests/duplicate_id.out --pages tests/sample.list --only
- Expected stderr: "Warning: Duplicate id count: 1"

Line limit (stop early):
- Command: python3 pages_list.py --input tests/sample.out --pages tests/sample.list --only --lines 2
- Expected stderr: "Warning: Line limit reached at line 2."

Missing pages list file:
- Command: python3 pages_list.py --input tests/sample.out --pages tests/missing.list --only
- Expected stderr: "Error: pages list file not found: tests/missing.list"

Empty pages list file:
- Command: python3 pages_list.py --input tests/sample.out --pages tests/empty.list --only
- Expected stderr: "Error: --only requires at least one page name."

--only with --details:
- Command: python3 pages_list.py --input tests/sample.out --pages tests/prefix.list --only --details
- Expected stderr: "Error: --only cannot be used with --details."

Invalid pages list file (no names):
- Command: python3 pages_list.py --input tests/sample.out --pages tests/invalid.list --only
- Expected stderr: "Error: --only requires at least one page name."

Missing default pages list file:
- Command: (cd tests/no_pages_list && python3 ../pages_list.py --input ../tests/sample.out --only)
- Expected stderr: "Error: pages list file not found: pages.list"

Empty default pages list file:
- Command: (cd tests/empty_pages_list && python3 ../pages_list.py --input ../tests/sample.out --only)
- Expected stderr: "Error: --only requires at least one page name."

Empty pages list file (no --only):
- Command: python3 pages_list.py --input tests/sample.out --pages tests/empty.list
- Expected stdout: tests/all_rows_expected.csv

Invalid pages list file (no --only):
- Command: python3 pages_list.py --input tests/sample.out --pages tests/invalid.list
- Expected stdout: tests/all_rows_expected.csv

Duplicate handling:
- Focus list dedupe uses a set of normalized keys (case-sensitive or lowercased); duplicates are skipped with "Duplicate page name skipped" warnings.
- Input rows are indexed by normalized title in a dict of lists (`title_index`); duplicates are resolved with `pick_best` when selecting a focus match.
- Ordered matching uses a list of normalized keys (`focus_keys`); in details mode `match_label` returns the first exact or prefix match by focus list order.
- Not --only output tracks used IDs with a set (`used_ids`) so matched rows are not emitted twice.

Notes:
- Several tests validate stdout content; expected CSV files cover defaults, exact match, prefix variants, and details mode outputs.
- Error cases validate stderr and exit status for warnings/errors.
- A runner script is available at tests/run_tests.sh. By default it writes outputs to tests/results_YYYYMMDD_HHMMSS*.
- Override the output directory with `./tests/run_tests.sh --results tests/results` or `RESULTS=tests/results ./tests/run_tests.sh`.

pages_db.py unit tests:
- tests/test_pages_db.py uses unittest to cover parse_dump behaviors, limits, and index helpers.
- The runner includes this as the "pages_db" test via `python tests/test_pages_db.py`.

pages_focus.py unit tests:
- tests/test_pages_focus.py covers load_focus_list dedupe behavior, build_rows_with_keys normalization, match_focus_entry selection, and match_label precedence.
- The runner includes this as the "pages_focus" test via `python tests/test_pages_focus.py`.

pages_cli.py unit tests:
- tests/test_pages_cli.py covers limit validation, missing-file errors, parse errors, and strict vs non-strict warning emission.
- The runner includes this as the "pages_cli" test via `python tests/test_pages_cli.py`.

Coverage notes:
- parse_dump covers empty file, bad header, malformed rows (strict vs non-strict), limits, and use_csv on a normal fixture.
- Index helpers and pick_best are exercised with the sample.out fixture.
- parse_dump includes a use_csv test with an escaped delimiter (backslash + tab) and confirms the default split misparses that case.
- parse_dump includes a mixed newline test (\r\n, \n\r, \n, \r).
- parse_dump includes strict_header=False coverage and asserts header_mismatch stats.
- parse_dump includes FileNotFoundError coverage.
- parse_dump includes invalid id/status/date count coverage.
- parse_dump includes duplicate id count coverage.
- Gaps: no use_csv backslash-sequence fixture.
- Gaps: no test for stats.skipped_oversized + reached_limit combined, and no content-unescape behavior (currently not implemented).
- pages_list.py adds coverage for defaults (not --only), prefix/noprefix and case/nocase overrides, details-mode output on multiple fixtures, and list parsing with commas/whitespace.
- pages_list.py includes prefix-overlap labeling coverage (longest prefix wins) in details mode.
- pages_list.py adds coverage for invalid list (no names), negative --lines/--bytes, missing/empty list errors, and --only + --details incompatibility.
