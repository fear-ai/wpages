#!/usr/bin/env python3
import argparse
import re
from pathlib import Path

from pages_cli import (
    add_common_args,
    add_filter_args,
    emit_db_warnings,
    error,
    load_focus_entries,
    parse_dump_checked,
    resolve_filter_args,
    validate_limits,
    warn,
)
from pages_util import decode_mysql_escapes, filter_characters, safe_filename, strip_footer
from pages_focus import match_entries


def clean_text(
    text: str,
    *,
    replace_char: str = " ",
    keep_newlines: bool = True,
    ascii_only: bool = True,
    raw: bool = False,
    keep_tabs: bool = False,
) -> str:
    if not text:
        return ""
    # Decode literal escape sequences from mysql -e output.
    text = decode_mysql_escapes(text)

    # Remove scripts, styles, and comments to avoid inline code.
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<!--.*?-->", " ", text)

    # Strip all remaining tags.
    text = re.sub(r"(?s)<[^>]+>", " ", text)

    # Strip HTML entities and normalize whitespace.
    text = re.sub(r"&[A-Za-z0-9#]+;", " ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not raw:
        text = filter_characters(
            text,
            replace_char,
            keep_tabs=keep_tabs,
            keep_newlines=keep_newlines,
            ascii_only=ascii_only,
        )
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
    if cleaned:
        cleaned += "\n"
    return cleaned


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract page text from a mysql tab dump and write per-page .txt files."
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
    add_filter_args(parser)
    add_common_args(
        parser,
        prefix_default=False,
        case_default=True,
        prefix_help="Enable prefix matching (default: off).",
        case_help="Use case-sensitive matching (default: on).",
    )
    args = parser.parse_args()

    if not validate_limits(args.lines, args.max_bytes):
        return 1
    if args.permit:
        args.strict_header = False
        args.strict_columns = False

    use_prefix = args.use_prefix if args.use_prefix is not None else False
    case_sensitive = args.case_sensitive if args.case_sensitive is not None else True

    filter_args = resolve_filter_args(args, keep_tabs_default=False)
    if filter_args is None:
        return 1
    replace_char, ascii_only, keep_tabs, keep_newlines, raw = filter_args
    output_encoding = "utf-8" if raw or not ascii_only else "ascii"
    output_errors = "ignore" if output_encoding == "ascii" else "strict"

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
        cleaned = clean_text(
            match.row.content,
            replace_char=replace_char,
            keep_newlines=keep_newlines,
            ascii_only=ascii_only,
            raw=raw,
            keep_tabs=keep_tabs,
        )
        if not args.footer:
            cleaned = strip_footer(cleaned)
        out_path = output_dir / safe_filename(match.entry.name)
        try:
            out_path.write_text(
                cleaned,
                encoding=output_encoding,
                errors=output_errors,
            )
        except OSError as exc:
            error(f"output file could not be written: {out_path} ({exc})")
            return 1
        print(f"Wrote {out_path} ({match.row.id}, {match.label})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
