#!/usr/bin/env python3
import argparse
import html
import re
import sys
import unicodedata
from pathlib import Path

from pages_cli import (
    add_common_args,
    emit_db_warnings,
    error,
    load_focus_entries,
    parse_dump_checked,
    validate_limits,
    warn,
)
from pages_focus import match_entries

ZERO_WIDTH = {"\u200b", "\u200c", "\u200d", "\ufeff"}
ANCHOR_RE = re.compile(
    r'(?is)<a\b[^>]*href=["\']?([^"\'>\s]+)["\']?[^>]*>(.*?)</a>'
)


def _strip_inline_tags(text: str) -> str:
    return re.sub(r"(?s)<[^>]+>", " ", text)


def _convert_anchor(match: re.Match[str]) -> str:
    url = match.group(1).strip()
    inner = match.group(2) or ""
    inner_text = _strip_inline_tags(inner)
    inner_text = html.unescape(inner_text).strip()
    if inner_text and url:
        return f"{inner_text} ({url})"
    if url:
        return url
    return inner_text


def _filter_characters(text: str, replace_char: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    out: list[str] = []
    last_replaced = False
    for ch in normalized:
        if ch == "\n":
            out.append("\n")
            last_replaced = False
            continue
        if ch == "\t":
            out.append("\t")
            last_replaced = False
            continue
        code = ord(ch)
        is_control = code < 32 or code == 127
        is_zero_width = ch in ZERO_WIDTH
        if is_control or is_zero_width or code >= 128:
            if replace_char:
                if not last_replaced:
                    out.append(replace_char)
                    last_replaced = True
            continue
        out.append(ch)
        last_replaced = False
    return "".join(out)


def _normalize_lines(text: str, table_delim: str) -> str:
    lines = text.split("\n")
    out_lines: list[str] = []
    blank = False
    for line in lines:
        if table_delim == "\t":
            parts = line.split("\t")
            parts = [re.sub(r"[ \t]+", " ", part).strip() for part in parts]
            line = "\t".join(parts)
        else:
            line = re.sub(r"[ \t]+", " ", line).strip()
        if table_delim and line.startswith(table_delim):
            line = line[len(table_delim) :]
        if not line:
            if not blank:
                out_lines.append("")
                blank = True
            continue
        blank = False
        out_lines.append(line)
    cleaned = "\n".join(out_lines).strip()
    if cleaned:
        cleaned += "\n"
    return cleaned


def clean_content(text: str, *, table_delim: str, replace_char: str) -> str:
    if not text:
        return ""
    # Decode literal escape sequences from mysql -e output.
    text = text.replace("\\r", "\n").replace("\\n", "\n").replace("\\t", "\t")

    # Remove scripts, styles, and comments to avoid inline code.
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<!--.*?-->", " ", text)

    # Preserve link destinations before stripping tags.
    text = ANCHOR_RE.sub(_convert_anchor, text)

    # Convert structural tags to line breaks or delimiters.
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(
        r"(?i)<h([1-6])[^>]*>",
        lambda m: f"\n{'#' * int(m.group(1))} ",
        text,
    )
    text = re.sub(r"(?i)</h[1-6]>", "\n", text)
    text = re.sub(r"(?i)<li[^>]*>", "- ", text)
    text = re.sub(r"(?i)</li>", "\n", text)
    text = re.sub(r"(?i)</?(ul|ol)[^>]*>", "\n", text)
    text = re.sub(r"\n{2,}- ", "\n- ", text)
    text = re.sub(r"(?i)<tr[^>]*>", "", text)
    text = re.sub(r"(?i)</tr>", "\n", text)
    text = re.sub(r"(?i)<t[dh][^>]*>", table_delim, text)
    text = re.sub(r"(?i)</t[dh]>", "", text)
    text = re.sub(r"(?i)</?(table|thead|tbody|tfoot)[^>]*>", "", text)
    text = re.sub(
        r"(?i)</?(p|div|section|article|header|footer|blockquote|figure|figcaption|form|label|input|textarea|button|pre|code|hr)[^>]*>",
        "\n",
        text,
    )

    # Strip all remaining tags.
    text = re.sub(r"(?s)<[^>]+>", " ", text)

    # Decode entities and normalize line endings.
    text = html.unescape(text).replace("\u00a0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Filter control, zero-width, and non-ASCII characters.
    text = _filter_characters(text, replace_char)

    return _normalize_lines(text, table_delim)


def strip_footer(text: str) -> str:
    if not text:
        return text
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if line.strip().lower() in {"resources", "community"}:
            stripped = "\n".join(lines[:idx]).rstrip()
            return f"{stripped}\n" if stripped else ""
    return text


def safe_filename(name: str) -> str:
    name = name.replace("/", "-")
    name = re.sub(r"\s+", " ", name).strip()
    return f"{name}.txt"


def _validate_replace_char(value: str) -> str | None:
    if not value:
        return None
    if len(value) != 1:
        error("--replace-char must be a single ASCII character.")
        return None
    if ord(value) >= 128:
        error("--replace-char must be ASCII.")
        return None
    if value in {"\n", "\r", "\t"}:
        error("--replace-char cannot be a newline or tab.")
        return None
    return value


def _table_delimiter(name: str) -> str:
    if name == "tab":
        return "\t"
    return ","


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract page content from a mysql tab dump and write per-page .txt files."
    )
    add_common_args(
        parser,
        prefix_default=False,
        case_default=True,
        prefix_help="Enable prefix matching (default: off).",
        case_help="Use case-sensitive matching (default: on).",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory to write .txt files (default: current directory).",
    )
    parser.add_argument(
        "--footer",
        action="store_true",
        help="Keep footer-like sections (Resources/Community) instead of stripping them.",
    )
    parser.add_argument(
        "--table-delim",
        choices=("comma", "tab"),
        default="comma",
        help="Delimiter for table fallback rows (default: comma).",
    )
    parser.add_argument(
        "--replace-char",
        default="",
        help="Replace suspicious characters instead of removing them (ASCII only).",
    )
    args = parser.parse_args()

    if not validate_limits(args.lines, args.max_bytes):
        return 1
    if args.permit:
        args.strict_header = False
        args.strict_columns = False

    replace_char = _validate_replace_char(args.replace_char)
    if replace_char is None and args.replace_char:
        return 1
    table_delim = _table_delimiter(args.table_delim)

    use_prefix = args.use_prefix if args.use_prefix is not None else False
    case_sensitive = args.case_sensitive if args.case_sensitive is not None else True

    pages_path = Path(args.pages)
    focus_entries = load_focus_entries(pages_path, case_sensitive)
    if focus_entries is None:
        return 1
    strict_header = args.strict_header
    strict_columns = args.strict_columns
    input_path = Path(args.input)
    result = parse_dump_checked(
        input_path,
        max_lines=args.lines,
        max_bytes=args.max_bytes,
        use_csv=args.csv,
        include_content=True,
        strict_header=strict_header,
        strict_columns=strict_columns,
    )
    if result is None:
        return 1
    emit_db_warnings(
        result,
        input_path,
        strict_header=strict_header,
        strict_columns=strict_columns,
    )
    if not focus_entries:
        error("pages list must include at least one page name.")
        return 1

    output_dir = Path(args.output_dir)
    if output_dir.exists() and not output_dir.is_dir():
        error(f"output path is not a directory: {output_dir}")
        return 1
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        error(f"output directory could not be created: {output_dir} ({exc})")
        return 1

    rows = result.rows
    for match in match_entries(
        focus_entries, rows, case_sensitive=case_sensitive, use_prefix=use_prefix
    ):
        if match.row is None:
            warn(f"Missing page: {match.entry.name}")
            continue
        cleaned = clean_content(
            match.row.content,
            table_delim=table_delim,
            replace_char=replace_char or "",
        )
        if not args.footer:
            cleaned = strip_footer(cleaned)
        out_path = output_dir / safe_filename(match.entry.name)
        try:
            out_path.write_text(cleaned, encoding="ascii")
        except OSError as exc:
            error(f"output file could not be written: {out_path} ({exc})")
            return 1
        print(f"Wrote {out_path} ({match.row.id}, {match.label})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
