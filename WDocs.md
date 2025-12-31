WDocs: Documentation map and partitioning

1) Documents
1.1) WPages.md
- Workflow overview and operating assumptions. Includes dump format expectations, CLI option groupings, matching model, normalization rules, and performance guidance.
- Excludes deep sanitization policy, import/export SQL, and module‑level implementation detail.

1.2) Status.md
- Implementation state, risks, pending decisions, and next steps.
- Captures what is done vs deferred and why; excludes how‑to usage, SQL recipes, and detailed sanitization rules.

1.3) HStrip.md
- Sanitization policy and rationale. Contains HTML handling rules, link scheme policy, character filtering philosophy, security tradeoffs, and known limitations.
- Excludes CLI flag listings and test fixture catalogs.

1.4) PList.md
- pages_list behavior and output schema. Defines CSV column order, details mode semantics, pages.list behavior, and output file generation.
- Excludes sanitization rules and content extraction details.

1.5) PText.md
- pages_text behavior and pipeline details. Covers cleaning order, options, edge cases, output conventions, counts, and tests relevant to the text path.
- Excludes general workflow and import/export guidance.

1.6) PContent.md
- pages_content behavior and pipeline details. Covers text/Markdown conversion rules, tag handling, structure warnings, scheme blocking, and output conventions.
- Excludes parsing/SQL details and global workflow guidance.

1.7) PFilename.md
- safe_filename rules and filename constraints. Documents normalization, Windows safety, length limits, collision handling, and tests.

1.8) WImport.md
- Import strategies and compatibility. Covers WXR/REST/CSV/HTML paths, limitations of HTML, plugin considerations, and metadata sidecars.
- Excludes SQL export recipes and tool internals.

1.9) WExport.md
- Export SQL specs. Contains field order, row type definitions, single‑line SELECT statements, and command‑line usage.
- Excludes import workflows and sanitization policy.

1.10) tests/TESTS.md
- Test scope and execution. Lists fixtures, expected outputs, runner usage, and coverage notes.
- Excludes feature explanations and policy rationale.

2) Cross‑cutting components and references
2.1) CLI options
- WPages.md groups shared CLI options and defaults.
- PList.md, PText.md, and PContent.md own tool‑specific flags.

2.2) Sanitization
- HStrip.md is the policy source of truth.
- PText.md and PContent.md document implemented behavior.
- WPages.md only points to these; it does not restate rules.

2.3) Import/export
- WExport.md defines dump fields and SQL; WImport.md defines import paths and constraints.
- Changes in WExport.md enable additional import capabilities documented in WImport.md.

2.4) Tests
- tests/TESTS.md is the single test guide.
- WPages.md and Status.md may link to it but should not restate details.

2.5) Program descriptions
- PList.md, PText.md, and PContent.md are the canonical program behavior docs and should be kept in sync with code changes.
*** End Patchователь
