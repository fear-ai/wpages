# PFilename: Filename Safety Policy and Options

## Purpose
Define filename safety requirements, tradeoffs, and implementation options for
WPages outputs. This doc focuses on sanitizing user-provided page titles into
filesystem-safe filenames across platforms.

## Wants
- Safe on Windows and POSIX (Linux/macOS) by default.
- Stable and deterministic (same input -> same output).
- Readable where possible (not pure hashes unless needed).
- Low dependency footprint (stdlib preferred), but allow optional stronger
  sanitizer when dependencies are acceptable.
- Clear handling of Unicode, length limits, and collisions.

## Challenges
- Invalid characters differ by platform; Windows is the strictest.
- Reserved device names on Windows (CON, PRN, AUX, NUL, COM1-9, LPT1-9).
- Trailing dots/spaces are invalid on Windows.
- Length limits are usually byte-based; UTF-8 length matters.
- Path traversal and path separators must be neutralized.
- Empty results after sanitization need a fallback name.
- Collisions may occur after normalization.

## Current State (WPages)
- `pages_util.safe_filename` implements Option A (internal sanitizer).
- ASCII-only output via NFKD + drop non-ASCII.
- Invalid characters replaced with `-`; runs of whitespace collapsed.
- Leading/trailing spaces and dots trimmed.
- Reserved Windows names get `_1` suffix; collisions use `_N` suffix when
  an `existing` set is supplied.
- 255-byte cap with extension preserved (ASCII, so 255 chars).

## Options and Existing Approaches

### Werkzeug `secure_filename`
- Produces ASCII-only filenames for portability.
- Strips or normalizes unsafe characters and path traversal.
- Prevents Windows device names.
- May return empty strings; caller must handle uniqueness or fallback.

### pathvalidate `sanitize_filename`
- Explicit invalid character set, including OS-specific rules.
- Handles reserved names and provides handlers for replacement.
- Enforces a max byte length with truncation.
- Supports platform targeting (Windows, POSIX, universal).

### Django `slugify`
- URL slug generator, not a filesystem sanitizer.
- Converts to ASCII by default (optional Unicode), lowercases, strips
  non-alphanumerics, and collapses whitespace to dashes.

### python-slugify
- URL slug generator with rich options (allow_unicode, max_length, separator,
  entity handling). Not a full filesystem sanitizer.

### stdlib `os.path`
- Path manipulation helpers only. No sanitization of characters or names.

## Likely Policy Directions

### Option A: Minimal internal sanitizer (no deps)
- Replace path separators and invalid characters with '-'.
- Strip leading/trailing whitespace and dots.
- Normalize runs of whitespace to single spaces or dashes.
- Optional ASCII-folding.
- Enforce a conservative max length (bytes).
- Avoid Windows reserved names by suffixing or prefixing.

### Option B: Full sanitizer via pathvalidate (optional dependency)
- Use pathvalidate for strict cross-platform compliance.
- Keep a minimal internal fallback if dependency is unavailable.

### Option C: Slug-only names
- Use slugify and treat filename as a URL slug.
- Simple and readable but lossy, and not guaranteed filesystem-safe.

## Recommendation
### Chosen (Option A)
- Hardened internal sanitizer (no dependencies).
- Windows-safe rules (superset of POSIX).
- ASCII-only output (NFKD + drop non-ASCII).
- Invalid characters replaced with `-`.
- Collapse whitespace to single spaces; trim leading/trailing spaces and dots.
- Reserved names (CON/PRN/AUX/NUL/COM1-9/LPT1-9) get a `_1` suffix.
- Collision handling via `_N` suffix (if an `existing` set is supplied).
- Byte length cap: 255 bytes (ASCII, so 255 chars); extension preserved.
- Empty results fall back to `page` (or `page_N` when suffixing).

### Future Options
- Optional pathvalidate integration for strict policies.
- Configurable Unicode policy (keep vs ASCII-fold) if needed later.
- Alternative collision policies (hash, overwrite).

## Open Questions
- What max length do we want (bytes) for filenames?
- Unicode policy default: keep or ASCII-fold? (currently ASCII-only)
- Collision policy: overwrite, numeric suffix, or short hash? (currently `_N`)
- Should the extension be sanitized separately or enforced by caller?

## References
```
https://werkzeug.palletsprojects.com/en/stable/utils/
https://pathvalidate.readthedocs.io/en/latest/pages/reference/function.html
https://docs.djangoproject.com/en/5.1/ref/utils/
https://github.com/un33k/python-slugify
https://docs.python.org/3.12/library/os.path.html
```
