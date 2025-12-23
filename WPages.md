WordPress database dump obtained via
mysql -p -e "SELECT ID, post_title, post_content, post_status, post_date FROM wp_posts WHERE post_type='page' ORDER BY ID;"
Results saved in a text file, db.out by default. List Pages with pages_list.py and save contents to individual files with pages_text.py
Note: pages_list.py expects default mysql -e output where tabs/newlines inside fields are escaped. If you use --raw or have literal tabs, the simple split can misparse; switch to a csv.reader with `delimiter="\t"`, `quoting=csv.QUOTE_NONE`, and `escapechar="\\"`, or avoid --raw.
Normalization: parsing normalizes header casing and line endings (CR/LF), but does not normalize field content or unescape backslash sequences.

Duplicates:
- Instances:
  - Duplicate names in pages.list (exact string repeats) produce repeated focus output.
  - Overlapping focus names with prefix matching can map multiple names to the same page.
  - Dump rows can repeat the same ID (data issues or multiple exports) and will appear in non-focus output.
  - Multiple rows can share the same title but different IDs; focus matching selects one "best" row, but the non-focus pass will include all rows.
- Causes:
  - Prefix and case-insensitive matching widen the hit set.
  - Focus list ordering influences which prefix hit is labeled first.
  - The script treats focus names as independent, so it does not enforce unique IDs.
- Approaches:
  - Skip duplicate focus names (implemented; emits a warning per duplicate).
  - Dedupe by ID when emitting output, with a policy (keep first, keep best, or aggregate focus names).
  - Prefer exact over prefix and skip prefix hits for IDs already matched exactly.
  - Aggregate focus names for the same ID into a single output row (requires output format changes).

Performance:
- Matching cost:
  - Exact matching is O(F x R) because each focus name scans all rows.
  - Prefix matching is also O(F x R) but with more string work per comparison.
  - Details mode adds O(R x F) for labeling each row against all focus names.
- IO and memory:
  - The script loads all rows into memory; large dumps can be heavy without limits.
  - Large post_content fields cause huge lines; `--bytes` protects against that.
- Searches and ordering:
  - `--only` reduces output volume but does not reduce the initial scans.
  - Prefix checks run only after an exact miss per focus name, but still scan all rows for that name.
  - The non-focus pass scans all rows again when `--only` is not set.

Fixes (implementation changes):
- Data structures:
  - Build a normalized title index: title -> list of rows, and a separate ID index to dedupe quickly.
  - Precompute normalized focus names once per run (case-sensitive or not).
- Algorithms:
  - For exact matches, use the title index to reduce work to O(R + F).
  - For details labeling, use a title index for exact, then a prefix index or a sorted list for prefix scans.
  - Add a de-duplication policy for IDs in focus output (skip, warn, or aggregate).
- Progress reporting:
  - Add a `--progress` flag to report every N lines read and N matches found.
  - Report when `--lines` truncates input or when oversized lines are skipped.

Mitigations (usage and data selection):
- Use SQL to filter the dump: restrict by post_type, post_status, date ranges, or specific IDs.
- Keep pages.list small and exact for targeted extraction; avoid prefix unless needed.
- Prefer `--noprefix` and `--case` for narrow searches; use `--details` only when exploring.
- Use `--lines` and `--bytes` to cap work on unknown or large dumps.
- Clean pages.list to remove duplicates and reduce overlap between focus names.
