WordPress import formats and options (findings)

Scope
- This document summarizes practical import formats/methods for WordPress and how WPages outputs can be used or converted.
- WPages extracts content from MySQL dumps; it does not generate a WordPress import file by itself.

Import formats and methods (full set)
- WXR (WordPress eXtended RSS, XML): core export/import path via Tools -> Export/Import. Best for full fidelity (authors, pages, posts, attachments, metadata).
- Admin editor (manual): paste HTML or Markdown into the block editor; suitable for small sets or one-off pages.
- WP-CLI / REST API (programmatic): create pages via scripts using content files (HTML or Markdown converted to HTML); useful when the site is reachable but WXR is not available.
- CSV/XML via plugins: third-party importers map a CSV or XML schema into pages; capability varies and is plugin-specific.
- Direct database insert (not recommended): high risk, difficult to keep GUIDs, slugs, meta, and relationships consistent.

Note: HTML Importer 2 is not a candidate for this workflow.

Site structure and layout (what must be reconstructed)
- Hierarchy: parent/child relationships between pages (post_parent).
- Order: menu order and display order (menu_order, nav menu relationships).
- Templates: per-page templates (postmeta like _wp_page_template) and theme-level templates.
- Blocks and layout: block comments in post_content (block editor), page builder shortcodes, and inline styles.
- Media: attachments (post_type=attachment) and their meta; URLs in content must align with uploads.
- Menus and navigation: menu definitions and menu items are stored separately (nav_menu_item posts + term relationships + meta) and are not implied by page content.

When export/plugins are unavailable: MySQL-dump driven workflow
- Goal: produce human-readable, editable artifacts that preserve structure cues even if a full WP import is impossible.
- Outputs from WPages are ideal for this stage:
  - Plain text (.txt): quick review and editing; lowest structural fidelity.
  - Markdown (.md): headings/lists/links/tables preserved; best for human editing and later conversion.
  - CSV/TSV summaries: index of pages, IDs, status, dates, and matching diagnostics.
  - Directory structure: one file per page, named by a safe filename or title, optionally grouped by hierarchy.

Recommended metadata to preserve from a MySQL dump
- Required for reconstruction: id, title, status, date, post_name (slug), post_parent, menu_order.
- Strongly recommended: post_type, guid (original URL), template name, excerpt, and any important custom fields.
- Suggested storage: YAML front matter in Markdown or a sidecar JSON/YAML per page file.

Example (front matter, minimal)
---
id: 123
title: "About"
status: publish
date: 2020-01-05
slug: about
parent: 0
menu_order: 3
---

Structure and layout recovery from MySQL
- Hierarchy: derive parent/child relationships from post_parent and mirror as folders or a sitemap list.
- Menus: reconstruct from nav_menu_item posts and their meta; otherwise document manual menu recreation.
- Templates: capture _wp_page_template and store alongside content for re-application.
- Blocks/shortcodes: preserve raw block markup or shortcode syntax in Markdown when possible to keep layout cues.
- Media: capture attachments separately and map old URLs to new uploads; otherwise preserve URLs for manual replacement.

Mapping WPages outputs into import paths
- Markdown-first pipeline (recommended for dumps without WXR):
  1) Extract Markdown via pages_content.py --format markdown.
  2) Preserve metadata (front matter or sidecar).
  3) Convert Markdown to HTML with a consistent toolchain.
  4) Import via WXR generation, WP-CLI, REST API, or manual paste.
- Text-first pipeline (lowest effort):
  1) Extract text via pages_text.py or pages_content.py (text).
  2) Manually rewrite in the editor; use the text as a checklist/reference.

Considerations and tradeoffs
- WXR is verbose but most complete; it is the safest path for large batches.
- CSV/XML importers require a specific schema; choose one plugin and document its required fields.
- Markdown is not a native import format; treat it as an intermediate that becomes HTML or WXR.
- Theme/layout fidelity is limited when only content is available; expect manual rework for menus, blocks, and templates.
- Sanitization and scheme blocking should be applied before import to avoid unsafe output.

Recommendations
- Prefer WXR whenever feasible; keep a Markdown artifact as a review/edit format.
- When WXR is unavailable, use Markdown + front matter and build a structured import pipeline from it.
- Document the chosen importer (if any) and the expected schema in this repo so the workflow stays repeatable.

How imports are performed (specifics)
- WXR (XML) via Admin UI:
  - In WordPress Admin, go to Tools -> Import -> WordPress.
  - Install/activate the WordPress Importer if prompted.
  - Upload the WXR XML file, map authors, and choose whether to import attachments.
- WXR (XML) via WP-CLI:
  - Run `wp import <file>.xml --authors=create|skip|<mapping.csv>` to import the WXR.
  - This uses the same WordPress Importer logic in a CLI workflow.
- HTML via REST API:
  - Send a POST to `/wp/v2/pages` with `title`, `content` (HTML), and `status`.
  - Use this when you have HTML output but no WXR tooling.
- HTML via WP-CLI (direct page creation):
  - Create pages with `wp post create` and pass `--post_type=page` plus `--post_title` and `--post_content` (from the HTML file).
  - Use this for scripted imports when WXR is not available.

Open questions
- Should WPages generate a minimal WXR or a structured JSON/YAML manifest?
- Which CSV/XML importer, if any, should be the standard in this workflow?
- How much menu/template reconstruction should be automated from MySQL?

Import plugins (current candidates)
- WP All Import:
  - CSV/XML importer that maps fields into WordPress content.
  - HTML can be imported by placing it in the content field during mapping.
  - Suitable for large batch imports and repeatable workflows.
- WP Ultimate CSV Importer:
  - CSV/XML importer with support for HTML in post content fields.
  - Useful when working from structured CSV/TSV outputs.

Plugin selection notes
- Both are actively maintained and support recent WordPress versions.
- Plugin schemas differ; choose one and document its required field mapping to avoid drift.

Compatibility analysis (current WPages outputs)
- .text (pages_text.py output):
  - Plain text only; best for review and manual edit.
  - Import path: paste into editor or map into CSV as content (no structure).
  - Limitation: WordPress will not reconstruct headings/lists/links as blocks.
- .txt (pages_content.py text mode):
  - Structured-ish text (headings/lists/links rendered inline) but still plain text.
  - Import path: paste into editor or map into CSV as content.
  - Limitation: structure is human-readable, not machine-reconstructible.
- .md (pages_content.py markdown mode):
  - Best human-editable representation with structure preserved.
  - Import path: convert to HTML, then import via WXR/CSV/REST/WP-CLI, or use a Markdown plugin.
  - Limitation: core WordPress does not ingest Markdown directly.

CSV import scenarios
- Expected structure (typical): title, content, status, date, slug, parent, menu_order, author, excerpt, template, and optional custom fields.
- HTML-in-CSV is discouraged: it is brittle, hard to audit, and inherits all HTML sanitation and structure problems already identified. It also increases escaping/quoting risk and makes diffs/reviews painful.
- For hierarchy/menu reconstruction, CSV must include parent identifiers or slugs that can be resolved during import.

Feasibility of generating CSV from WPages outputs
- We already produce `pages.csv` (title, id, status, date, content_bytes) but it does not include content.
- A new export step could combine:
  - titles + metadata from `pages_list.py`
  - content from `.md` (converted to HTML) or `.txt`/`.text` for plain-text imports
  - optional front matter (slug, parent, menu_order, template) if available from the dump
- This is feasible but requires choosing:
  - target importer (WP All Import vs WP Ultimate CSV Importer)
  - CSV field schema and escaping rules
  - whether to include raw HTML vs Markdown-to-HTML conversion

PAGE.meta sidecar files (recommended)
- Create a per-page metadata file (e.g., `Title.meta` or `Title.meta.json`) alongside `.text/.txt/.md`.
- Purpose: preserve and extend structured data without embedding it in HTML or CSV.
- Suggested fields from the MySQL dump:
  - id, title, status, date, post_name (slug), post_parent, menu_order
  - guid (original URL), post_type, excerpt, template (`_wp_page_template`)
  - any custom fields required for the target site
- Suggested computed/inferred fields:
  - content_bytes, content_hash, word_count (from text/markdown)
  - inferred parent (from title prefixes or site map), inferred slug (if post_name missing)
  - source file paths (.out line index, original filename)
- Formats:
  - JSON (machine-friendly) or YAML (human-friendly); keep keys stable for tooling.
- Benefits:
  - Keeps content files clean and human-editable.
  - Allows future generation of WXR/CSV/REST imports without re-parsing MySQL dumps.
