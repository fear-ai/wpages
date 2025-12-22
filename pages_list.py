#!/usr/bin/env python3
import argparse
import csv
import re
import sys
from pathlib import Path


EXPECTED_HEADER = ["id", "post_title", "post_content", "post_status", "post_date"]


def load_rows(path: Path, max_lines: int, max_bytes: int) -> list:
    rows = []
    bad_count = 0
    oversized_count = 0
    line_count = 0
    reached_limit = False
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        header = handle.readline()
        if not header:
            raise ValueError("Empty input file (missing header).")
        header_cols = [col.strip().lower() for col in header.rstrip("\n").split("\t")]
        if header_cols != EXPECTED_HEADER:
            raise ValueError(
                f"Unexpected header columns: {header_cols!r} (expected {EXPECTED_HEADER!r})"
            )
        for line_no, line in enumerate(handle, start=2):
            line = line.rstrip("\n")
            if not line:
                continue
            if max_lines and line_count >= max_lines:
                reached_limit = True
                break
            line_count += 1
            if max_bytes:
                line_size = len(line.encode("utf-8"))
                if line_size > max_bytes:
                    oversized_count += 1
                    continue
            parts = line.split("\t", 4)
            if len(parts) != 5:
                bad_count += 1
                continue
            post_id, title, content, status, post_date = parts
            rows.append(
                {
                    "id": post_id,
                    "title": title,
                    "status": status,
                    "date": post_date,
                }
            )
    if bad_count:
        message = f"Warning: skipped {bad_count} malformed line(s) in {path}"
        print(message, file=sys.stderr)
    if oversized_count:
        message = f"Warning: skipped {oversized_count} oversized line(s) in {path}"
        print(message, file=sys.stderr)
    if reached_limit:
        print(
            f"Warning: stopped after {line_count} line(s) due to --lines limit.",
            file=sys.stderr,
        )
    return rows


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


def status_rank(status: str) -> int:
    order = {
        "publish": 0,
        "draft": 1,
        "private": 2,
    }
    return order.get(status.lower(), 3)


def pick_best(matches: list) -> dict:
    best = None
    for row in matches:
        if best is None:
            best = row
            continue
        row_rank = status_rank(row["status"])
        best_rank = status_rank(best["status"])
        if row_rank < best_rank:
            best = row
            continue
        if row_rank == best_rank and row["date"] > best["date"]:
            best = row
    return best


def match_rows(rows: list, name: str, prefix: bool, case_sensitive: bool) -> list:
    name_key = name if case_sensitive else name.lower()
    matches = []
    for row in rows:
        title_key = row["title"] if case_sensitive else row["title"].lower()
        if prefix:
            if title_key.startswith(name_key):
                matches.append(row)
        else:
            if title_key == name_key:
                matches.append(row)
    return matches


def match_label(row: dict, focus_names: list, case_sensitive: bool) -> tuple:
    if not focus_names:
        return ("none", "")
    title_key = row["title"] if case_sensitive else row["title"].lower()
    for name in focus_names:
        name_key = name if case_sensitive else name.lower()
        if title_key == name_key:
            return ("exact", name)
    for name in focus_names:
        name_key = name if case_sensitive else name.lower()
        if title_key.startswith(name_key):
            return ("prefix", name)
    return ("none", "")


def emit_row(focus: str, row: dict, match: str) -> dict:
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
        "title": row["title"],
        "id": row["id"],
        "status": row["status"],
        "date": row["date"],
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
    args = parser.parse_args()

    if args.lines < 0:
        print("Error: --lines must be 0 or a positive integer.", file=sys.stderr)
        return 1
    if args.max_bytes < 0:
        print("Error: --bytes must be 0 or a positive integer.", file=sys.stderr)
        return 1

    use_prefix = args.use_prefix if args.use_prefix is not None else args.details
    case_sensitive = (
        args.case_sensitive if args.case_sensitive is not None else not args.details
    )

    pages_path = Path(args.pages)
    if not pages_path.exists():
        print(f"Error: pages list file not found: {pages_path}", file=sys.stderr)
        return 1
    try:
        rows = load_rows(Path(args.input), args.lines, args.max_bytes)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    focus_names, duplicate_count = load_focus_list(pages_path)
    if args.only and not focus_names:
        print("Error: --only requires at least one page name.", file=sys.stderr)
        return 1

    output = []
    if focus_names:
        for name in focus_names:
            exact_matches = match_rows(
                rows, name, prefix=False, case_sensitive=case_sensitive
            )
            if exact_matches:
                best = exact_matches[0] if len(exact_matches) == 1 else pick_best(exact_matches)
                output.append(emit_row(name, best, "exact"))
                continue
            if use_prefix:
                prefix_matches = match_rows(
                    rows, name, prefix=True, case_sensitive=case_sensitive
                )
                if prefix_matches:
                    best = prefix_matches[0] if len(prefix_matches) == 1 else pick_best(prefix_matches)
                    output.append(emit_row(name, best, "prefix"))
                    continue
            if args.details:
                output.append(emit_row(name, None, "none"))

    if not args.only:
        used_ids = {row["id"] for row in output if row["id"]}
        for row in rows:
            if row["id"] in used_ids:
                continue
            if args.details:
                label, focus = match_label(
                    row, focus_names, case_sensitive=case_sensitive
                )
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
