# HStrip: HTML Sanitization and Content Preparation

## Context
Content was exported from a WordPress MySQL dump for web display. We want to reuse
selected pages on a new site. The pipeline should clean and sanitize content to
reduce ambiguity and security risk while preserving usable structure.

Related
- Implemented behavior is documented in PText.md and PContent.md.

## Customer
### Wants
- Safer and more consistent content before manual review and edits.
- Markdown output that preserves structure and some layout.
- Clear diagnostics when input is malformed or unsafe.
- Preserve tables, lists, and basic formatting where possible.

### Needs
- Strong sanitization with explicit rules.
- Traceable warnings and consistent behavior.
- Readable and printable text output.
- Compatibility with WP-CLI/WP code/plugins and the current WP editor import.
- Clear separation between extraction, sanitization, and formatting.
- Preserve unambiguous metadata (HTML and WordPress designators) for later culling.

### Pain Points
- Raw HTML from MySQL may include unsafe tags/attributes or malformed markup.
- Control characters, zero-width characters, and odd whitespace can hide issues.
- WordPress shortcodes and inline styles can be risky or invalid in new targets.
- Tables and lists are fragile; aggressive stripping can destroy structure.

## Design
### Requirements
H/M/L indicates importance/complexity/likelihood. Likelihood means how often we
expect the situation per dump or per page; confirm with `db.out`.

### Core safety and output
- Sanitization (H/H/H).
  - Strip scripts, event handlers, and unsafe URLs.
  - Remove or escape malformed attributes and unterminated tags.
  - Allowlist vs blacklist is TBD based on tooling.
- Output (H/M/H).
  - Readable and printable text output is required.
  - Markdown output is a strong want; HTML output is postponed.
  - Preserve structure signals (headings, lists, tables, links, images) where practical.
  - Keep link destinations visible in text output.
  - Preserve metadata such as HTML version or original source details.
  - Ensure compatibility with WP-CLI/WP code/plugins and the current editor.
- Character set and non-printables (H/M/H).
  - Remove control characters and ambiguous escapes.
  - Detect and report zero-width or invisible characters.
  - Avoid formatting via spaces or tabs; keep layout intent minimal.
  - Default handling is removal of suspicious characters or sequences.
  - Replacement with space or "?" is configurable.
  - Suppress long sequences after 1-2 replacements.
  - Normalize odd CR/LF patterns while preserving intended spacing.
- Whitespace normalization (H/M/H).
  - Collapse repeated blank lines.
  - Preserve whitespace inside code/pre blocks.
  - Treat line breaks inside paragraphs and lists as structural, not layout.
  - Avoid alignment-by-spaces or tabs in final output.

### Structure and media
- Tables and lists (M/H/M).
  - Preserve table and list semantics where possible.
  - Document limitations when structure is degraded.
  - When structure cannot be preserved, use comma, tab, or newline separation.
- Links and images (M/H/H).
  - Validate link schemes; allow http/https/mailto as configured.
  - Decide handling for local or missing images (retain placeholder, drop, warn).
- Tag handling (M/M/H).
  - Use an allowlist of structural tags to preserve headings, lists, tables, and
    code/pre blocks.
  - Treat remaining tags as inline content or strip entirely.
  - Ensure consistent handling for text vs Markdown output.

### Presentation and markup
- Styles (M/H/H).
  - Inline style handling is postponed; strip or allowlist style attributes.
  - Distinguish style attributes vs inline CSS blocks.
- Shortcodes (L/M/L).
  - Identify WordPress shortcodes; preserve, remove, or translate with warnings.
  - Shortcode support is postponed until need is confirmed.
  - Attribute handling (H/M/H).
  - Allowlist attributes for links/images (href, src, alt, title).
  - Strip event handlers and risky attributes by default.
  - Normalize or reject malformed attribute values.
  - Attribute value charset considerations:
    - UTF-8 and full Unicode appear in titles, alt text, and URLs.
    - HTML entities and numeric entities may appear inside attribute values.
    - Percent-encoded URLs are common and may mix with entities.
    - Mixed encodings can appear in a single value (entities plus %xx).
    - MySQL `-e` output can include literal backslashes and escapes.
    - Percent-encoding issues to handle:
      - Unescaped spaces and control characters.
      - Invalid percent escapes (`%` not followed by two hex digits).
      - Double-encoding (`%2520` representing `%20`).
      - Mixed case percent escapes (`%2f` vs `%2F`) complicate comparisons.
      - Inconsistent decoding order with entities and percent-encoding.
  - Attribute parsing challenges:
    - Quoted vs unquoted values; unquoted values cannot include spaces.
    - Whitespace and newlines inside quoted values.
    - `>` inside quoted values can truncate regex-based tag parsing.
    - Unterminated quotes or malformed tags are common in raw exports.
    - Attributes with `=` inside (JSON or query strings) are common.
    - Backticks and control characters can appear in invalid or hostile input.
    - Right-to-left markers can make URLs or filenames misleading.
    - Long data URIs (`data:`) can bloat output.
    - `javascript:` and `data:` URLs require explicit policy decisions.
    - Invalid byte sequences can appear with encoding mismatches.
  - Blocked schemes to drop: `about`, `blob`, `chrome`, `chrome-extension`, `data`,
    `file`, `filesystem`, `javascript`, `moz-extension`, `vbscript`.

### Features
- Sanitized output with strong safety controls.
- Readable/printable text output; Markdown output when feasible.
- Warning and error reporting for malformed or unsafe content.
- Hooks for later enrichment (e.g., style handling, shortcode expansion).

### Design and Implementation Choices
- Separate content extraction from sanitization and formatting.
- Some processing during extraction may be required (escaping, quotes, patterns).
- Emit warnings for suspicious patterns instead of silently fixing.
- Usable and safe results are the goal, not reversibility.
- Prioritize a rapid, solid working implementation.
- Default handling for strongly suspicious sequences is removal.

### Sanitization Tooling Alternatives
- Python stdlib HTMLParser: Pros: no dependencies, predictable behavior. Cons:
  limited sanitization features and verbose rule enforcement.
- html5lib/BeautifulSoup: Pros: tolerant parsing for malformed markup. Cons:
  extra dependency and possible normalization surprises.
- Bleach: Pros: purpose-built sanitizer and clear allowlist controls. Cons:
  dependency and careful configuration for tables/lists.
- Pandoc or external converters: Pros: strong format conversion. Cons:
  external tooling and harder-to-control security details.

## Discussion
### Metadata
- Preserve unambiguous HTML and WordPress designators for later culling.
- Format and storage options: sidecar file, post meta, or inline header block.
- Notes/comments are under review for inline or sidecar representation.
- Decision needed on exact fields, file naming, and encoding.

### Schema and Charset
- Typical WordPress defaults: post_title is TEXT (max 65,535 bytes), post_content
  is LONGTEXT, post_name is varchar(200).
- Charset is usually utf8mb4 (1-4 bytes per code point), so max characters vary.
- Titles are free-form; slug rules apply to post_name, not post_title.
- Verify actual schema and charset with SHOW CREATE TABLE wp_posts and
  SHOW VARIABLES LIKE 'character_set%'.

### Name and Filename Rules
- Matching uses post_title values directly (case-controlled), not the slug.
- WordPress slug functions: sanitize_title, sanitize_title_with_dashes,
  wp_unique_post_slug.
- Python references for conversion: django slugify, python-slugify,
  werkzeug secure_filename, pathvalidate.
- Linux filename limits are typically 255 bytes; invalid byte is NUL and the path
  separator is '/'.
- Windows disallows < > : " / \\ | ? * and reserved names like CON, PRN, AUX,
  NUL, COM1.

### Open Questions
- How strict should sanitization be for tables and lists?
- How should UTF-8 characters be handled in non-HTML output?
- What is the link and image handling policy?
- How should unknown or invalid shortcodes be handled?
- How far should style handling go beyond basic stripping?

### Gaps and Limitations
- No complete policy for links, images, or shortcodes beyond basic scheme blocking.
- Unicode normalization policy beyond ASCII-folding is not fully defined.
- Table/list degradation rules remain a policy choice and vary by content.

### Discussion Guide
- Design: capture requirements and features with decision status and rationale.
- Sanitization tooling: list options, tradeoffs, and decision status.
- Open Questions: record unresolved decisions and required evidence.
- Gaps and Limitations: record current shortcomings and impact.
- Import Paths: record options, readiness, and compatibility risks.

## Pending
- Sample `db.out` to confirm likelihood ratings and adjust H/M/L.
- Inventory tables/lists usage to inform fallback handling.
- Review UTF-8 usage patterns and define acceptable output subset.
- Survey link and image patterns to inform policy.
- Identify shortcodes in use and their relevance.
- Defer query parameter handling (tracking) and IDN/punycode normalization.

## TODO
- Define sanitization rules and apply them to the text output path.
- Define attribute and URL scheme policies (href/src) and implement filtering.
- Add tag allowlist rules for HTML-to-text/Markdown conversion.
- Draft a sidecar metadata format and file naming scheme.
- Add sanitization tool evaluation notes and sample config.
