WordPress database dump obtained via
mysql -p -e "SELECT ID, post_title, post_content, post_status, post_date FROM wp_posts WHERE post_type='page' ORDER BY ID;"
Results saved in a text file, db.out by default. List Pages with pages_list.py and save contents to individual files with pages_text.py
Note: pages_list.py expects default mysql -e output where tabs/newlines inside column values are escaped. If you use --raw or have literal tabs, the simple split can misparse; use `--csv` to switch to csv.reader with `delimiter="\t"`, `quoting=csv.QUOTE_NONE`, and `escapechar="\\"`, or avoid --raw.
Normalization: parsing normalizes header casing and line endings (CR/LF), but does not normalize column values or unescape backslash sequences. Matching normalizes focus names and titles consistently (case-sensitive or lowercased) for dedupe, indexing, prefix checks, and details labeling.
pages.list can be comma- or newline-separated; whitespace is trimmed per entry.

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
- Approaches:
  - Dedupe by ID when emitting output, with a policy (keep first, keep best, or aggregate focus names).
  - Prefer exact over prefix and skip prefix hits for IDs already matched exactly.
  - Aggregate focus names for the same ID into a single output row (requires output format changes).

Performance:
- Matching cost:
  - Exact matching is O(R + F) due to the title index; prefix matching still scans rows per focus name.
  - Prefix matching is also O(F x R) but with more string work per comparison.
  - Details mode adds O(R x F) for labeling each row against all focus names.
- Repeated scans can be P x F if callers re-parse or re-scan rows; prefer building indices once and reuse them when possible.
- IO and memory:
  - The script loads all rows into memory; large dumps can be heavy without limits.
  - Large post_content column values cause huge lines; `--bytes` protects against that.
  - Excluding content (list-only paths) reduces memory pressure and speeds up parsing.
- Validation cost:
  - Date checks use datetime.strptime for calendar correctness; regex is faster but only validates shape.
- Searches and ordering:
  - `--only` reduces output volume but does not reduce the initial scans.
  - Prefix checks run only after an exact miss per focus name, but still scan all rows for that name.
  - The non-focus pass scans all rows again when `--only` is not set.

Implementation notes:
- Data structures:
  - Use a normalized title index: title -> list of rows for exact matches.
  - Precompute normalized focus names once per run (case-sensitive or not).
  - Track used IDs from focus matches to avoid re-emitting those rows in not --only output.
- Algorithms:
  - Exact matches use the title index to reduce work to O(R + F).

Potential improvements:
- For details labeling, use a prefix index or sorted list to avoid O(R x F) scans.
- Add a de-duplication policy for IDs in focus output (skip, warn, or aggregate).
- Add a `--progress` flag to report every N lines read and N matches found.
- Report when `--lines` truncates input or when oversized lines are skipped.

Mitigations (usage and data selection):
- Use SQL to filter the dump: restrict by post_type, post_status, date ranges, or specific IDs.
- Keep pages.list small and exact for targeted extraction; avoid prefix unless needed.
- Prefer `--noprefix` and `--case` for narrow searches; use `--details` only when exploring.
- Use `--lines` and `--bytes` to cap work on unknown or large dumps.
- Clean pages.list to remove duplicates and reduce overlap between focus names.
