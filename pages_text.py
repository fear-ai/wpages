#!/usr/bin/env python3
import argparse
import html
import re
import sys
import unicodedata
from pathlib import Path

from pages_db import build_title_index
from pages_cli import (
    emit_parse_warnings,
    load_focus_list_checked,
    parse_dump_checked,
    validate_limits,
    warn,
)
from pages_focus import build_rows_with_keys, match_focus_entry


def clean_text(text: str) -> str:
    if not text:
        return ""
    # Decode literal escape sequences from mysql -e output.
    text = text.replace("\\r", "\n").replace("\\n", "\n").replace("\\t", "\t")

    # Remove scripts, styles, and comments to avoid inline code.
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<!--.*?-->", " ", text)

    # Convert common block/line break tags to newlines before stripping tags.
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(
        r"(?i)</?(p|div|section|article|header|footer|h[1-6]|li|ul|ol|table|tbody|tr|td|th|blockquote|figure|figcaption|form|label|input|textarea|button)[^>]*>",
        "\n",
        text,
    )

    # Strip all remaining tags.
    text = re.sub(r"(?s)<[^>]+>", " ", text)

    # Decode HTML entities and normalize whitespace.
    text = html.unescape(text).replace("\u00a0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]

    out_lines = []
    blank = False
    for line in lines:
        if not line:
            if not blank:
                out_lines.append("")
                blank = True
            continue
        blank = False
        out_lines.append(line)

    cleaned = "\n".join(out_lines).strip()
    # Force ASCII output.
    cleaned = (
        unicodedata.normalize("NFKD", cleaned)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    if cleaned:
        cleaned += "\n"
    return cleaned


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract page text from a mysql tab dump and write per-page .txt files."
    )
    parser.add_argument(
        "--input",
        default="db.out",
        help="Path to mysql tab dump (default: db.out).",
    )
    parser.add_argument(
        "--pages",
        default="pages.list",
        help="Comma-separated page names list file (default: pages.list).",
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
        "--prefix",
        dest="use_prefix",
        action="store_true",
        default=None,
        help="Enable prefix matching (default: off).",
    )
    parser.add_argument(
        "--noprefix",
        dest="use_prefix",
        action="store_false",
        help="Disable prefix matching.",
    )
    parser.add_argument(
        "--case",
        dest="case_sensitive",
        action="store_true",
        default=None,
        help="Use case-sensitive matching (default: on).",
    )
    parser.add_argument(
        "--nocase",
        dest="case_sensitive",
        action="store_false",
        help="Use case-insensitive matching.",
    )
    parser.add_argument(
        "--lines",
        type=int,
        default=1000,
        help="Max data lines to read (0 for unlimited).",
    )
    parser.add_argument(
        "--bytes",
        dest="max_bytes",
        type=int,
        default=1_000_000,
        help="Max bytes per data line (0 for unlimited).",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Parse the dump with csv.reader (tab delimiter, backslash escapes).",
    )
    args = parser.parse_args()

    if not validate_limits(args.lines, args.max_bytes):
        return 1

    use_prefix = args.use_prefix if args.use_prefix is not None else False
    case_sensitive = args.case_sensitive if args.case_sensitive is not None else True

    pages_path = Path(args.pages)
    focus_entries = load_focus_list_checked(pages_path, case_sensitive)
    if focus_entries is None:
        return 1
    strict_header = True
    strict_columns = True
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
    emit_parse_warnings(
        result,
        input_path,
        strict_header=strict_header,
        strict_columns=strict_columns,
    )
    if not focus_entries:
        print("Error: pages list must include at least one page name.", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    if output_dir.exists() and not output_dir.is_dir():
        print(f"Error: output path is not a directory: {output_dir}", file=sys.stderr)
        return 1
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = result.rows
    title_index = build_title_index(rows, case_sensitive=case_sensitive)
    rows_with_keys = build_rows_with_keys(rows, case_sensitive) if use_prefix else []

    for entry in focus_entries:
        label, row = match_focus_entry(
            entry,
            title_index=title_index,
            rows_with_keys=rows_with_keys,
            use_prefix=use_prefix,
        )
        if row is None:
            warn(f"Missing page: {entry.name}")
            continue
        cleaned = clean_text(row.content)
        if not args.footer:
            cleaned = strip_footer(cleaned)
        out_path = output_dir / safe_filename(entry.name)
        out_path.write_text(cleaned, encoding="ascii", errors="ignore")
        print(f"Wrote {out_path} ({row.id}, {label})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
