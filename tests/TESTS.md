Test cases for pages_list.py and pages_db.py

Applicability:
- pages_list.py CLI tests validate stdout CSV and stderr warnings/errors.
- pages_db.py unit tests validate parse_dump behavior and index helpers.

Usage:
- Run all tests: ./tests/run_tests.sh [--results PATH]
- Run pages_db tests only: python -m unittest tests.test_pages_db

Fixtures:
- *.out files are small mysql tab dumps with a header row and tab-delimited fields.
- *.list files are focus-name lists (one per line or comma-separated).

Input files:
- tests/sample.out: valid header and 8 rows; includes duplicate titles (Home), case variation (Contact/contact), and mixed statuses to exercise pick_best.
- tests/malformed.out: valid header with one malformed row missing columns, plus one valid row.
- tests/bad_header.out: invalid header (missing post_content column) to trigger a hard error.
- tests/oversized.out: valid header with one long content field to trigger --bytes skipping.
- tests/sample.list: Home/About/Contact for basic exact matching.
- tests/prefix.list: Con/About to exercise prefix matching and ordering.
- tests/dups.list: Home repeated to trigger duplicate-name warnings.

Basic exact match (default exact + case-sensitive):
- Command: python3 pages_list.py --input tests/sample.out --pages tests/sample.list --only
- Expected stdout: tests/sample_only_expected.csv

Prefix + details (defaults to prefix + case-insensitive):
- Command: python3 pages_list.py --input tests/sample.out --pages tests/prefix.list --only --details
- Expected stdout: tests/prefix_details_expected.csv

Duplicate focus names (per-duplicate warning):
- Command: python3 pages_list.py --input tests/sample.out --pages tests/dups.list --only
- Expected stderr: "Warning: duplicate page name skipped: Home"

Malformed line skip (bad columns):
- Command: python3 pages_list.py --input tests/malformed.out --pages tests/sample.list --only
- Expected stderr: "Warning: skipped 1 malformed line(s) in tests/malformed.out"

Bad header (wrong columns):
- Command: python3 pages_list.py --input tests/bad_header.out --pages tests/sample.list --only
- Expected stderr: "Error: Unexpected header columns: ..."

Oversized line skip (use small --bytes to trigger):
- Command: python3 pages_list.py --input tests/oversized.out --pages tests/sample.list --only --bytes 100
- Expected stderr: "Warning: skipped 1 oversized line(s) in tests/oversized.out"

Line limit (stop early):
- Command: python3 pages_list.py --input tests/sample.out --pages tests/sample.list --only --lines 2
- Expected stderr: "Warning: stopped after 2 line(s) due to --lines limit."

Notes:
- Only two tests validate stdout content, so only two expected CSV files exist.
- The other five cases validate stderr and exit status for warnings/errors.
- A runner script is available at tests/run_tests.sh. By default it writes outputs to tests/results_YYYYMMDD*.
- Override the output directory with `./tests/run_tests.sh --results tests/results` or `RESULTS=tests/results ./tests/run_tests.sh`.

pages_db.py unit tests:
- tests/test_pages_db.py uses unittest to cover parse_dump behaviors, limits, and index helpers.
- The runner includes this as the "pages_db" test via `python -m unittest tests.test_pages_db`.

Coverage notes:
- parse_dump covers empty file, bad header, malformed rows (strict vs non-strict), limits, and use_csv on a normal fixture.
- Index helpers and pick_best are exercised with the sample.out fixture.
- Gaps: no explicit CRLF fixture, no FileNotFound test, no strict_header=False path, and no use_csv escape-case fixture.
- Gaps: no test for stats.skipped_oversized + reached_limit combined, and no content-unescape behavior (currently not implemented).
