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

Implementation
- Input formats and normalization (pages_db.py, pages_focus.py)
  - db.out uses a header line plus tab-delimited rows; header casing and line endings are normalized.
  - pages.list is split on commas/newlines, entries are trimmed, and internal whitespace is preserved.
  - Duplicate focus names are skipped with warnings during CLI load.
- Parsing and limits (pages_db.py, pages_cli.py)
  - parse_dump is keyword-only and returns ParseResult rows + stats.
  - ParseLimits caps max_lines and max_bytes; oversized lines are skipped and line limits set reached_limit.
  - csv.reader mode is enabled via --csv with tab delimiter, QUOTE_NONE, and escapechar "\\".
  - CLI wrappers report missing/unreadable input or pages.list files; --permit relaxes strict header/column enforcement.
- Validation and stats (pages_db.py, pages_cli.py)
  - Invalid ids, duplicate ids, unknown statuses, and invalid dates are counted.
  - emit_db_warnings reports nonzero counts and limit warnings in CLI workflows.
- Matching and selection (pages_db.py, pages_focus.py, pages_list.py)
  - build_title_index/build_id_index retain lists per key.
  - FocusEntry stores name, normalized key, and key length; exact match is preferred and prefix matching is optional.
  - match_entries centralizes focus matching; match_label chooses the longest prefix when enabled; pick_best selects by status then date.
  - used_ids prevents duplicate emission in not --only output.
- CLI outputs (pages_list.py)
  - Default CSV columns are title/id/status/date; details adds focus and match columns.
  - --details implies prefix matching and case-insensitive matching by default; --only cannot be combined with --details.

Improvements
1) Add progress reporting for long runs (every N lines and matches).
2) Report when --lines truncates input or when oversized lines are skipped outside CLI warnings.
3) Use a prefix index or sorted list for details labeling to reduce O(R x F) scans.
4) Type pages_list emit_row output with a TypedDict or small dataclass for clarity.

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

Pending
- Improvements 1-4 are backlog candidates; no schedule set.

TODO
- None noted.
