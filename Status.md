Status for WPages tooling and tests
 
  Scope
  - WPages.md documents the WordPress page dump workflow and known tradeoffs.
  - tests/TESTS.md documents fixture-based tests for pages_list.py and the runner.
 
  Current implementation snapshot
  - pages_list.py lists pages from a mysql tab dump, supports focus list matching, and emits CSV output.
  - pages_text.py extracts and cleans text for a fixed list of page IDs and writes per-page .txt files.
  - tests/run_tests.sh runs seven fixture-driven tests; two validate stdout CSV, five validate warnings/errors.
 
  Session status
  - WPages.md and tests/TESTS.md are consistent with the current CLI flags and warnings.
  - Tests were last run after earlier changes; the runner output format was updated afterward and has not been re-run.
  - Repo status in ~/Work/WP/wpages was clean after updating .gitignore; untracked data files are ignored.
 
  Design and implementation notes
  - Parsing is currently duplicated across pages_list.py and pages_text.py (tab split, header handling).
  - pages_list.py enforces header validation, line/byte caps, and warning output; pages_text.py does not yet.
  - pages_list.py uses exact matches by default; --details implies prefix matching and case-insensitive comparisons.
  - Duplicate focus names are skipped with per-name warnings; duplicate IDs are not yet deduped in output.
 
  Alternatives discussed
  - Shared parser module (pages_db.py) to centralize header validation, limits, and warning behavior.
  - Single combined CLI with subcommands (list/extract) vs. keeping two scripts and sharing internals.
  - Optional presets (targeted/explore) vs. explicit flags (prefix/case/only/details).

