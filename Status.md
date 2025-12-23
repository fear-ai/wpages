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
  - Header normalization strips CR/LF and lowercases column names before validation; mismatches set stats.header_mismatch and stats.header_columns, and strict_header raises with path.
  - Row validation: strict_columns defaults to True; malformed rows raise ParseError with line number + path; when False, malformed rows are skipped and counted.
  - Limits: max_lines applies to data lines only and sets stats.reached_limit; max_bytes skips oversized lines and increments stats.skipped_oversized.
  - Parsing mode: split-by-tab is the default; csv.reader mode is enabled via use_csv and uses tab delimiter, QUOTE_NONE, and escapechar "\\".
  - Row data: fields are strings (id, title, content, status, date); include_content defaults to True, otherwise content is empty.
  - Data normalization strips CR/LF on each data line; field values are otherwise unnormalized.
  - Indexes and matching: build_title_index/build_id_index retain lists per key; status_rank orders publish/draft/private before unknowns; pick_best uses status_rank then date string comparison.
 
  Concerns and pending limitations
  - Raw dumps with literal tabs/newlines are not supported by line-based parsing; use_csv only handles backslash-escaped output on a single line. Decide whether to require mysql -e (no --raw) or build a parser that can handle embedded newlines.
  - No validation of id/status/date formats beyond column counts. Decide whether to enforce numeric ids, allowed statuses, and date parsing, and whether violations are errors or warnings.
  - parse_dump does not unescape backslash sequences in title/status/date/content. Decide if unescaping belongs in the parser or in per-command cleaning, and define the accepted escape set.
  - parse_dump only returns stats; it does not emit warnings. Decide on a standard warning policy and thresholds (skip vs error) for oversized or malformed rows.
  - File size heuristics comparing path.stat().st_size to max_lines * max_bytes are not implemented. Decide on the heuristic and whether it triggers warnings or aborts.
  - Performance depends on caller matching strategy; repeated scans can be P*F. Decide when to build title/id indices and whether to omit content in list-only paths to reduce memory.
  - Quickstart (pages_db.py): parse_dump(Path("db.out")) returns rows + stats; use ParseLimits for caps and build_title_index/build_id_index for lookups.
  - Guardrails (pages_db.py): require mysql -e tab output with backslash escapes, keep strict_header/strict_columns enabled, and set max_lines/max_bytes for large dumps.
  - Remaining test gaps: pages_list non- --only output labeling in --details mode.
