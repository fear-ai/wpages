#!/usr/bin/env python3
import argparse
import re
from collections.abc import Callable
from pathlib import Path

from pages_cli import (
    add_common_args,
    add_dump_args,
    add_filter_args,
    emit_db_warnings,
    error,
    info_page_count,
    load_focus_entries,
    parse_dump_check,
    resolve_filter_args,
    validate_limits,
    warn,
)
from pages_util import (
    FilterCounts,
    SanitizeCounts,
    decode_mysql_escapes,
    filter_characters,
    make_dump_notags_sink,
    prepare_output_dir,
    write_text_check,
    safe_filename,
    strip_footer,
)
from pages_focus import match_entries


def clean_text(
    text: str,
    *,
    replace_char: str = " ",
    keep_newlines: bool = True,
    ascii_only: bool = True,
    raw: bool = False,
    keep_tabs: bool = False,
    counts: SanitizeCounts | None = None,
    filter_counts: FilterCounts | None = None,
    notags_sink: Callable[[str], None] | None = None,
) -> str:
    if not text:
        return ""
    # Decode literal escape sequences from mysql -e output.
    text = decode_mysql_escapes(text)

    # Remove scripts, styles, and comments to avoid inline code.
    text, blocks_rm = re.subn(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
    if counts is not None:
        counts.blocks_rm += blocks_rm
    text, comments_rm = re.subn(r"(?s)<!--.*?-->", " ", text)
    if counts is not None:
        counts.comments_rm += comments_rm

    # Strip all remaining tags.
    text, tags_rm = re.subn(r"(?s)<[^>]+>", " ", text)
    if counts is not None:
        counts.tags_rm += tags_rm
    if notags_sink is not None:
        notags_sink(text)

    # Strip HTML entities and normalize whitespace.
    text, entities_rm = re.subn(r"&[A-Za-z0-9#]+;", " ", text)
    if counts is not None:
        counts.entities_rm += entities_rm
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not raw:
        text = filter_characters(
            text,
            replace_char,
            keep_tabs=keep_tabs,
            keep_newlines=keep_newlines,
            ascii_only=ascii_only,
            counts=filter_counts,
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
    parser.set_defaults(output_dir=".")
    parser.add_argument(
        "--footer",
        action="store_true",
        help="Keep footer-like sections (Resources/Community) instead of stripping them.",
    )
    add_dump_args(parser, include_notags=True)
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
    dump_rows_dir = Path(args.dump_rows) if args.dump_rows else None
    result = parse_dump_check(
        input_path,
        max_lines=args.lines,
        max_bytes=args.max_bytes,
        use_csv=args.csvin,
        include_content=True,
        strict_header=strict_header,
        strict_columns=strict_columns,
        dump_rows_dir=dump_rows_dir,
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
    try:
        prepare_output_dir(output_dir)
    except OSError as exc:
        error(str(exc))
        return 1

    rows = result.rows
    for match in match_entries(
        focus_entries, rows, case_sensitive=case_sensitive, use_prefix=use_prefix
    ):
        if match.row is None:
            warn(f"Missing page: {match.entry.name}")
            continue
        sanitize_counts = SanitizeCounts()
        filter_counts = FilterCounts()
        notags_path = (
            output_dir / safe_filename(match.entry.name, "_notags.txt")
            if args.notags
            else None
        )
        try:
            cleaned = clean_text(
                match.row.content,
                replace_char=replace_char,
                keep_newlines=keep_newlines,
                ascii_only=ascii_only,
                raw=raw,
                keep_tabs=keep_tabs,
                counts=sanitize_counts,
                filter_counts=filter_counts,
                notags_sink=(
                    None
                    if notags_path is None
                    else make_dump_notags_sink(
                        notags_path,
                        encoding=output_encoding,
                        errors=output_errors,
                    )
                ),
            )
        except OSError as exc:
            error(str(exc))
            return 1
        if not args.footer:
            cleaned = strip_footer(cleaned)
        out_path = output_dir / safe_filename(match.entry.name)
        try:
            write_text_check(
                out_path,
                cleaned,
                encoding=output_encoding,
                errors=output_errors,
                label="output",
            )
        except OSError as exc:
            error(str(exc))
            return 1
        print(f"Wrote {out_path} ({match.row.id}, {match.label})")
        info_page_count("Blocks removed", sanitize_counts.blocks_rm, match.entry.name)
        info_page_count(
            "Comments removed", sanitize_counts.comments_rm, match.entry.name
        )
        info_page_count("Tags removed", sanitize_counts.tags_rm, match.entry.name)
        info_page_count(
            "Entities removed", sanitize_counts.entities_rm, match.entry.name
        )
        info_page_count(
            "Control chars removed", filter_counts.re_control, match.entry.name
        )
        info_page_count("Zero-width removed", filter_counts.re_zero, match.entry.name)
        info_page_count("Tabs removed", filter_counts.re_tab, match.entry.name)
        info_page_count("Newlines removed", filter_counts.re_nl, match.entry.name)
        info_page_count(
            "Non-ASCII removed", filter_counts.re_non_ascii, match.entry.name
        )
        info_page_count(
            "Replacement chars", filter_counts.rep_chars, match.entry.name
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
