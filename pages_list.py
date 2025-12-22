#!/usr/bin/env python3
import argparse
import csv
import re
import sys
from pathlib import Path


def load_rows(path: Path) -> list:
    rows = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        header = handle.readline()
        for line in handle:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t", 4)
            if len(parts) != 5:
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
    return rows


def load_focus_list(path: Path) -> list:
    text = path.read_text(encoding="utf-8", errors="replace")
    parts = re.split(r"[,\n]", text)
    return [part.strip() for part in parts if part.strip()]


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


def match_rows(rows: list, name: str, prefix: bool) -> list:
    name_key = name.lower()
    matches = []
    for row in rows:
        title_key = row["title"].lower()
        if prefix:
            if title_key.startswith(name_key):
                matches.append(row)
        else:
            if title_key == name_key:
                matches.append(row)
    return matches


def match_label(row: dict, focus_names: list) -> tuple:
    if not focus_names:
        return ("none", "")
    title_key = row["title"].lower()
    for name in focus_names:
        if title_key == name.lower():
            return ("exact", name)
    for name in focus_names:
        if title_key.startswith(name.lower()):
            return ("prefix", name)
    return ("none", "")


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
    args = parser.parse_args()

    rows = load_rows(Path(args.input))
    pages_path = Path(args.pages)
    if not pages_path.exists():
        print(f"Error: pages list file not found: {pages_path}", file=sys.stderr)
        return 1
    focus_names = load_focus_list(pages_path)
    if args.only and not focus_names:
        print("Error: --only requires at least one page name.", file=sys.stderr)
        return 1

    output = []
    use_prefix = args.details
    if focus_names:
        for name in focus_names:
            exact_matches = match_rows(rows, name, prefix=False)
            if exact_matches:
                best = exact_matches[0] if len(exact_matches) == 1 else pick_best(exact_matches)
                output.append(
                    {
                        "focus": name,
                        "title": best["title"],
                        "id": best["id"],
                        "status": best["status"],
                        "date": best["date"],
                        "match": "exact",
                    }
                )
                continue
            if use_prefix:
                prefix_matches = match_rows(rows, name, prefix=True)
                if prefix_matches:
                    best = prefix_matches[0] if len(prefix_matches) == 1 else pick_best(prefix_matches)
                    output.append(
                        {
                            "focus": name,
                            "title": best["title"],
                            "id": best["id"],
                            "status": best["status"],
                            "date": best["date"],
                            "match": "prefix",
                        }
                    )
                    continue
            if args.details:
                output.append(
                    {
                        "focus": name,
                        "title": "",
                        "id": "",
                        "status": "",
                        "date": "",
                        "match": "none",
                    }
                )

    if not args.only:
        used_ids = {row["id"] for row in output if row["id"]}
        for row in rows:
            if row["id"] in used_ids:
                continue
            if args.details:
                label, focus = match_label(row, focus_names)
                output.append(
                    {
                        "focus": focus,
                        "title": row["title"],
                        "id": row["id"],
                        "status": row["status"],
                        "date": row["date"],
                        "match": label,
                    }
                )
            else:
                output.append(row)

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
