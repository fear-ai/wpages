WordPress database dump obtained via
mysql -p -e "SELECT ID, post_title, post_content, post_status, post_date FROM wp_posts WHERE post_type='page' ORDER BY ID;"
Results saved in a text file, db.out by default. List pages with pages_list.py and save contents to individual files with pages_text.py.

Vision:
- Provide a lightweight, dependency-free workflow to explore WordPress pages and extract text with predictable matching.

Goals:
- Make page discovery fast and repeatable from a known dump format.
- Keep matching behavior explicit (exact vs prefix, case-sensitive vs insensitive).
- Make large dumps manageable with limits and warnings.

Pain points:
- Raw mysql dumps can include literal tabs/newlines that break simple parsing.
- Large post_content values make files heavy and slow to scan.
- Duplicate titles and overlapping prefixes complicate selection.

Requirements:
- Expect mysql -e tab output; prefer escaping to avoid literal tabs/newlines.
- Use --csv when dumps include backslash-escaped tabs/newlines; avoid --raw output.
- pages.list accepts comma- or newline-separated names; whitespace is trimmed per entry. The CLI does not accept inline page lists; use --pages PATH.
- Normalization: parsing normalizes header casing and line endings (CR/LF), but does not normalize column values or unescape backslash sequences. Matching normalizes focus names and titles consistently (case-sensitive or lowercased) for dedupe, indexing, prefix checks, and details labeling.
- Line endings: parsing treats LF as the line break (newline="\\n"), trims trailing CR/LF, and strips leading CR on lines to tolerate LFCR. CR-only files are not supported; use LF or CRLF.
- Strict parsing is the default; use --permit, --permit-header, or --permit-columns to continue past header mismatches or malformed rows.
- Use --rows DIR to dump rows (raw row values) to numbered .txt files for debugging.

CLI options (ordered groups):
- Standard options (all tools): --input, --output-dir (writers only), --lines, --bytes, --csv, --permit/--permit-header/--permit-columns.
- Pages options (all tools): --pages, --prefix/--noprefix, --case/--nocase.
- Filter options (text/content only): --replace, --raw, --utf, --notab, --nonl.
- Dump options: --rows DIR (dump rows). --notags is supported only by pages_text.py/pages_content.py because only those tools strip HTML.
- Tool-specific options:
  - pages_list.py: --only, --details. Output is written to stdout; if --output-dir is provided, pages_list.csv is also written there.
  - pages_text.py: --footer.
  - pages_content.py: --footer, --format, --table-delim.

Terminology:
- Column: database structure element (SQL/MySQL); column name is the header label (e.g., post_title).
- Row: a record; column value is the data within a row/column intersection (prefer "column value" over "field" or "cell").
- Page title: WordPress UI title stored in post_title. Page name (in this tooling) is the pages.list entry that is matched against post_title; it is not a slug.
- Label: match classification in details output (exact/prefix/none).

Duplicates:
- Instances:
  - Duplicate names in pages.list are skipped with a warning (exact or case-insensitive depending on matching mode).
  - Overlapping focus names with prefix matching can map multiple names to the same page.
  - Dump rows can repeat the same ID (data issues or multiple exports) and will appear in non-focus output unless the ID was already emitted from the focus pass.
  - Multiple rows can share the same title but different IDs; focus matching selects one "best" row, but the non-focus pass will include the other IDs.
- Causes:
  - Prefix and case-insensitive matching widen the hit set.
  - Prefix overlaps are resolved by longest prefix first; ties fall back to focus list order.
  - The script treats focus names as independent, so it does not enforce unique IDs.

Performance:
- Input scale: db.out is a header line plus tab-delimited rows (R); pages.list is read into memory as a list of names (F).
- Data structures: exact matching uses a normalized title index; prefix matching scans a precomputed list of normalized title keys; details labeling scans focus names for each row; used IDs prevent duplicate emission in not --only output.
- Complexity: exact matching is O(R + F); prefix matching is O(F x R) in the worst case; details labeling adds O(R x F) when enabled; not --only adds a second pass over rows.
- Memory: rows are stored in memory; include_content keeps full post_content in memory, while list-only paths drop content to reduce footprint.
- Input format impacts: raw dumps with literal tabs/newlines can mis-split rows; use mysql -e output and limits when scale is unknown.

Mitigations (usage and data selection):
- Use SQL to filter the dump: restrict by post_type, post_status, date ranges, or specific IDs.
- Keep pages.list small and exact for targeted extraction; avoid prefix unless needed.
- Prefer `--noprefix` and `--case` for narrow searches; use `--details` only when exploring.
- Use `--lines` and `--bytes` to cap work on unknown or large dumps.
- Clean pages.list to remove duplicates and reduce overlap between focus names.

Testing and validation:
- Test guidance and fixtures are documented in tests/TESTS.md.

Sanitization policies and considerations are in `HStrip.md`.
