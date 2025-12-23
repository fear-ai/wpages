#!/usr/bin/env python3
import argparse
import csv
import re
import sys
from pathlib import Path

from pages_db import ParseError, ParseLimits, build_title_index, parse_dump, pick_best


def load_focus_list(path: Path) -> tuple:
    text = path.read_text(encoding="utf-8", errors="replace")
    parts = re.split(r"[,\n]", text)
    focus_names = []
    seen = set()
    dup_count = 0
    for part in parts:
        name = part.strip()
        if not name:
            continue
        if name in seen:
            dup_count += 1
            print(
                f"Warning: duplicate page name skipped: {name}",
                file=sys.stderr,
            )
            continue
        seen.add(name)
        focus_names.append(name)
    return focus_names, dup_count


def match_label(row, focus_keys, case_sensitive: bool, use_prefix: bool) -> tuple:
    if not focus_keys:
        return ("none", "")
    title_key = row.title if case_sensitive else row.title.lower()
    for name, name_key in focus_keys:
        if title_key == name_key:
            return ("exact", name)
    if use_prefix:
        for name, name_key in focus_keys:
            if title_key.startswith(name_key):
                return ("prefix", name)
    return ("none", "")


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

    if args.lines < 0:
        print("Error: --lines must be 0 or a positive integer.", file=sys.stderr)
        return 1
    if args.max_bytes < 0:
        print("Error: --bytes must be 0 or a positive integer.", file=sys.stderr)
        return 1
    if args.only and args.details:
        print("Error: --only cannot be used with --details.", file=sys.stderr)
        return 1

    use_prefix = args.use_prefix if args.use_prefix is not None else args.details
    case_sensitive = (
        args.case_sensitive if args.case_sensitive is not None else not args.details
    )

    pages_path = Path(args.pages)
    if not pages_path.exists():
        print(f"Error: pages list file not found: {pages_path}", file=sys.stderr)
        return 1
    input_path = Path(args.input)
    try:
        result = parse_dump(
            input_path,
            limits=ParseLimits(max_lines=args.lines, max_bytes=args.max_bytes),
            strict_header=True,
            strict_columns=True,
            use_csv=args.csv,
            include_content=False,
        )
    except FileNotFoundError:
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 1
    except ParseError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if result.stats.skipped_oversized:
        print(
            f"Warning: skipped {result.stats.skipped_oversized} oversized line(s) "
            f"in {input_path}",
            file=sys.stderr,
        )
    if result.stats.skipped_malformed:
        print(
            f"Warning: skipped {result.stats.skipped_malformed} malformed line(s) "
            f"in {input_path}",
            file=sys.stderr,
        )
    if result.stats.reached_limit:
        print(
            f"Warning: stopped after {result.stats.read_lines} line(s) due to --lines limit.",
            file=sys.stderr,
        )
    focus_names, duplicate_count = load_focus_list(pages_path)
    if args.only and not focus_names:
        print("Error: --only requires at least one page name.", file=sys.stderr)
        return 1

    output = []
    rows = result.rows
    title_index = build_title_index(rows, case_sensitive=case_sensitive)
    focus_keys = [
        (name, name if case_sensitive else name.lower()) for name in focus_names
    ]
    rows_with_keys = [
        (row.title if case_sensitive else row.title.lower(), row) for row in rows
    ]

    if focus_names:
        for name, name_key in focus_keys:
            exact_matches = title_index.get(name_key, [])
            if exact_matches:
                best = exact_matches[0] if len(exact_matches) == 1 else pick_best(exact_matches)
                output.append(emit_row(name, best, "exact"))
                continue
            if use_prefix:
                prefix_matches = [
                    row for title_key, row in rows_with_keys if title_key.startswith(name_key)
                ]
                if prefix_matches:
                    best = (
                        prefix_matches[0]
                        if len(prefix_matches) == 1
                        else pick_best(prefix_matches)
                    )
                    output.append(emit_row(name, best, "prefix"))
                    continue
            if args.details:
                output.append(emit_row(name, None, "none"))

    if not args.only:
        used_ids = {row["id"] for row in output if row["id"]}
        for row in rows:
            if row.id in used_ids:
                continue
            if args.details:
                label, focus = match_label(row, focus_keys, case_sensitive, use_prefix)
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
