#!/usr/bin/env python3
import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

from pages_db import (
    EXPECTED_HEADER,
    ParseError,
    ParseLimits,
    build_title_index,
    format_header_error,
    parse_dump,
    pick_best,
)


@dataclass(frozen=True)
class FocusEntry:
    name: str
    key: str
    key_len: int


def load_focus_list(path: Path, case_sensitive: bool) -> list[FocusEntry]:
    text = path.read_text(encoding="utf-8", errors="replace")
    parts = text.replace(",", "\n").splitlines()
    focus_entries: list[FocusEntry] = []
    seen = set()
    for part in parts:
        name = part.strip()
        if not name:
            continue
        key = name if case_sensitive else name.lower()
        if key in seen:
            print(f"Warning: Duplicate page name skipped: {name}", file=sys.stderr)
            continue
        seen.add(key)
        focus_entries.append(FocusEntry(name=name, key=key, key_len=len(key)))
    return focus_entries


def match_label(row, focus_entries, case_sensitive: bool, use_prefix: bool) -> tuple:
    if not focus_entries:
        return ("none", "")
    title_key = row.title if case_sensitive else row.title.lower()
    for entry in focus_entries:
        if title_key == entry.key:
            return ("exact", entry.name)
    if use_prefix:
        best = None
        for entry in focus_entries:
            if title_key.startswith(entry.key):
                if best is None or entry.key_len > best.key_len:
                    best = entry
        if best is not None:
            return ("prefix", best.name)
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


def warn_count(label: str, count: int, *, path: Path | None = None) -> None:
    if not count:
        return
    if path is None:
        message = f"Warning: {label}: {count}"
    else:
        message = f"Warning: {label}: {count} in {path}"
    print(message, file=sys.stderr)


def warn_if(condition: bool, message: str) -> None:
    if not condition:
        return
    print(f"Warning: {message}", file=sys.stderr)


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

    warn_count("Oversized line count", result.stats.skipped_oversized, path=input_path)
    warn_count("Malformed row count", result.stats.skipped_malformed, path=input_path)
    warn_if(
        result.stats.header_mismatch,
        format_header_error(input_path, result.stats.header_columns, EXPECTED_HEADER),
    )
    warn_count("Invalid id count", result.stats.invalid_id_count)
    warn_count("Duplicate id count", result.stats.duplicate_id_count)
    warn_count("Unknown status count", result.stats.unknown_status_count)
    warn_count("Invalid date count", result.stats.invalid_date_count)
    warn_if(
        result.stats.reached_limit,
        f"Line limit reached at line {result.stats.read_lines}.",
    )
    focus_entries = load_focus_list(pages_path, case_sensitive)
    if args.only and not focus_entries:
        print("Error: --only requires at least one page name.", file=sys.stderr)
        return 1

    output = []
    rows = result.rows
    title_index = build_title_index(rows, case_sensitive=case_sensitive)
    rows_with_keys = []
    if use_prefix:
        rows_with_keys = [
            (row.title if case_sensitive else row.title.lower(), row) for row in rows
        ]

    if focus_entries:
        for entry in focus_entries:
            exact_matches = title_index.get(entry.key, [])
            if exact_matches:
                best = exact_matches[0] if len(exact_matches) == 1 else pick_best(exact_matches)
                output.append(emit_row(entry.name, best, "exact"))
                continue
            if use_prefix:
                prefix_matches = [
                    row for title_key, row in rows_with_keys if title_key.startswith(entry.key)
                ]
                if prefix_matches:
                    best = (
                        prefix_matches[0]
                        if len(prefix_matches) == 1
                        else pick_best(prefix_matches)
                    )
                    output.append(emit_row(entry.name, best, "prefix"))
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
