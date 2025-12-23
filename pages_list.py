#!/usr/bin/env python3
import argparse
import csv
import sys
from pathlib import Path

from pages_db import build_title_index
from pages_cli import (
    emit_parse_warnings,
    load_focus_list_checked,
    parse_dump_checked,
    validate_limits,
)
from pages_focus import build_rows_with_keys, match_focus_entry, match_label


def emit_row(focus: str, row, match: str) -> dict:
    if row is None:
        return {
            "focus": focus,
            "title": "",
            "id": "",
            "status": "",
            "date": "",
            "match": match or "none",
        }
    return {
        "focus": focus or "",
        "title": row.title,
        "id": row.id,
        "status": row.status,
        "date": row.date,
        "match": match or "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List pages from a mysql tab dump, optionally focusing on names from a list."
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
        "--only",
        action="store_true",
        help="Only output pages listed in the pages list file.",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Use prefix matching and include match details in CSV output.",
    )
    parser.add_argument(
        "--prefix",
        dest="use_prefix",
        action="store_true",
        default=None,
        help="Enable prefix matching (default: off unless --details).",
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
        help="Use case-sensitive matching (default: on unless --details).",
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
    if args.only and args.details:
        print("Error: --only cannot be used with --details.", file=sys.stderr)
        return 1

    use_prefix = args.use_prefix if args.use_prefix is not None else args.details
    case_sensitive = (
        args.case_sensitive if args.case_sensitive is not None else not args.details
    )

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
        include_content=False,
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
    if args.only and not focus_entries:
        print("Error: --only requires at least one page name.", file=sys.stderr)
        return 1

    output = []
    rows = result.rows
    title_index = build_title_index(rows, case_sensitive=case_sensitive)
    rows_with_keys = build_rows_with_keys(rows, case_sensitive) if use_prefix else []

    if focus_entries:
        for entry in focus_entries:
            label, best = match_focus_entry(
                entry,
                title_index=title_index,
                rows_with_keys=rows_with_keys,
                use_prefix=use_prefix,
            )
            if best is not None:
                output.append(emit_row(entry.name, best, label))
                continue
            if args.details:
                output.append(emit_row(entry.name, None, "none"))

    if not args.only:
        used_ids = {row["id"] for row in output if row["id"]}
        for row in rows:
            if row.id in used_ids:
                continue
            if args.details:
                label, focus = match_label(row, focus_entries, case_sensitive, use_prefix)
                output.append(emit_row(focus, row, label))
            else:
                output.append(emit_row("", row, ""))

    writer = csv.writer(sys.stdout, lineterminator="\n")
    if args.details:
        for row in output:
            writer.writerow(
                [
                    row["focus"],
                    row["title"],
                    row["id"],
                    row["status"],
                    row["date"],
                    row["match"],
                ]
            )
    else:
        for row in output:
            writer.writerow([row["title"], row["id"], row["status"], row["date"]])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
