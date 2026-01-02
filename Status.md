Status for WPages tooling and tests

Introduction
- This file summarizes current state, risks, and next actions. See WDocs.md for document scope and partitioning.

Quick Start
- List pages from a dump: `python3 pages_list.py --input db.out --pages pages.list`
- Extract cleaned text: `python3 pages_text.py --input db.out --pages pages.list --output-dir text`
- Extract structured content (text + markdown): `python3 pages_content.py --input db.out --pages pages.list --output-dir content --format both`

Documents
- Documentation map and partitioning: see WDocs.md.

Environment
- Python 3 is required; scripts use the standard library only.
- CLI scripts run locally, read/write the filesystem, and write results to stdout/stderr.
- Core processing does not require network access; fetch_domains uses wget and needs network access when run.

Current status

Capabilities
- Dump parsing and validation with strict/permit modes, size limits, and line-ending normalization.
- Focus matching with exact/prefix/case controls, dedupe, and best-row selection.
- Text extraction with tag/entity removal, whitespace normalization, character filtering, optional footer stripping, and per-page counts.
- Content extraction with structure-aware conversion, Markdown support (including title escaping), scheme blocking, malformed-structure warnings, and per-page counts.
- Domain probing via fetch_domains for basic HTTP reachability and capture.

Outputs
- Per-page content files in plain text and Markdown for review and reuse.
- Listing artifacts for reruns and triage: pages.csv and pages.list.
- Debug artifacts: row dumps and notags dumps.
- Domain probe artifacts: wget.log, wget.status, index.html, and domains.csv.

Modules
- pages_util.py: shared helpers (safe_filename, footer stripping, decode_mysql_escapes, file I/O guards).
- pages_db.py: dump parsing, header/row validation, size limits, parse stats.
- pages_focus.py: focus list parsing, dedupe, normalization, and matching logic.
- pages_cli.py: shared CLI options, input validation, error/warning emission.
- pages_list.py: list-mode output (pages.csv/pages.list) and match labeling.
- pages_text.py: plain text extraction and character filtering path.
- pages_content.py: structure-aware extraction and Markdown output path.

Open issues

Input parsing and dump fidelity
- Question: Should ASCII-only remain the default output policy? (P:Medium U:Later)
  Choices: (A) Keep ASCII default; (B) default UTF-8; (C) default UTF-8 for markdown only.
  Postpone: wait for dump profiling on non-ASCII frequency and impact.
- Question: Is streaming parsing required for large dumps? (P:Medium U:Later)
  Choices: (A) keep in-memory; (B) stream rows; (C) hybrid with limits.
  Postpone: revisit after measuring dump sizes.
- Question: Should we revisit URL normalization beyond scheme blocking? (P:Low U:Later)
  Choices: (A) keep scheme blocking only; (B) normalize/strip tracking parameters; (C) full URL normalization.
  Postpone: revisit if tracking/canonicalization becomes a requirement.

Pending steps (questions only)
- Question: Shared sanitization refactor scope and sequence? (P:Medium U:Near)
  Choices: (A) extract shared helpers first; (B) refactor pages_text/pages_content directly; (C) delay until validation is expanded.
- Question: Markdown validation scope? (P:Medium U:Near)
  Choices: (A) code fences + inline code only; (B) add tables/links/images; (C) full Markdown lint pass.
- Question: Page meta sidecars and menu/media exports needed? (P:Medium U:Later)
  Choices: (A) defer; (B) export meta + menus + attachments now; (C) export meta only.

Gaps and risks
- Input brittleness with raw dumps; requires mysql -e/--csvin usage discipline.
- Memory scale limits on large dumps until streaming is revisited.

Planned steps and tasks
- Progress reporting: emit periodic counters and explicit truncation warnings for --lines/--bytes.
