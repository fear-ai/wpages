Status for WPages tooling and tests
 
  Files
  - WPages.md documents the WordPress page dump workflow and tradeoffs.
  - Status.md tracks implementation notes, behaviors, and concerns.
  - tests/TESTS.md documents fixture-based CLI tests and runner usage.
 
  Environment
  - Python 3 is required; scripts use the standard library only.
 
  Implemented behaviors (pages_db.py)
  - parse_dump is keyword-only and returns ParseResult rows + stats.
  - Input errors: missing paths raise FileNotFoundError; empty files raise ParseError("Empty input file <path>").
  - Header normalization strips CR/LF and lowercases column names before validation; mismatches set stats.header_mismatch and stats.header_columns, and strict_header raises a header error with path.
  - Row validation: strict_columns defaults to True; malformed rows raise ParseError with line number + path; when False, malformed rows are skipped and counted.
  - Limits: max_lines applies to data lines only and sets stats.reached_limit; max_bytes skips oversized lines and increments stats.skipped_oversized.
  - Parsing mode: split-by-tab is the default; csv.reader mode is enabled via --csv and uses tab delimiter, QUOTE_NONE, and escapechar "\\".
  - Row data: fields are strings (id, title, content, status, date); include_content defaults to True, otherwise content is empty.
  - Data normalization strips CR/LF on each data line; field values are otherwise unnormalized.
  - Value validation counts invalid ids, duplicate ids, unknown statuses, and invalid dates (stats.invalid_id_count, stats.duplicate_id_count, stats.unknown_status_count, stats.invalid_date_count).
  - Indexes and matching: build_title_index/build_id_index retain lists per key; status_rank follows KNOWN_STATUSES order (publish, future, pending, draft, private, inherit, auto-draft, trash) then unknowns; pick_best uses status_rank then date string comparison.
 
  Concerns and pending limitations
  - Strict header/columns: current pages_list.py always uses strict_header=True and strict_columns=True, so header mismatch and malformed row warnings are unreachable; decide whether to remove those warnings or add flags for warning-only parsing.
  - ID duplicates: current behavior reports duplicate id count but does not dedupe; decide whether an explicit dedupe flag is ever needed.
  - Raw dumps: current line-based parsing cannot handle literal tabs/newlines; --csv only handles backslash-escaped output on a single line. Decide whether to require mysql -e (no --raw) or build a parser that can handle embedded newlines.
  - Validation enforcement: current id/status/date validation is count-only; decide whether to enforce numeric ids, allowed statuses, and date parsing, and whether violations are errors or warnings.
  - Unescaping: current parser does not unescape backslash sequences in title/status/date/content; decide where unescaping belongs and define the accepted escape set.
  - Warning policy: current parser returns stats only, while pages_list.py emits warnings; decide on shared thresholds and error vs warning behavior for oversized or malformed rows.
  - File size heuristic: not implemented; decide whether to compare path.stat().st_size to max_lines * max_bytes and whether to warn or abort.
  - Quickstart (pages_db.py): parse_dump(Path("db.out")) returns rows + stats; use ParseLimits for caps and build_title_index/build_id_index for lookups.
  - Guardrails (pages_db.py): require mysql -e tab output with backslash escapes, keep strict_header/strict_columns enabled, and set max_lines/max_bytes for large dumps.
  - Warning formatter: current warnings use local helpers in pages_list.py; decide whether to centralize formatting or keep per-command wording.
  - Focus list whitespace: current parsing splits on commas/newlines, trims each entry, and preserves internal whitespace; decide whether to normalize internal whitespace.
  - Focus list size: current parsing loads the full file into memory; decide whether streaming is needed for large lists.
  - Focus list encoding: current parsing uses errors="replace"; decide whether strict or ignore is preferable for malformed bytes.
