#!/usr/bin/env python3
import argparse
import html
import re
import unicodedata
from collections import OrderedDict
from pathlib import Path


TARGETS = OrderedDict(
    [
        ("Home", "4059"),
        ("Buy", "135"),
        ("Mine", "196"),
        ("Trade", "73"),
        ("Wallets", "5948"),
        ("Nodes", "87"),
        ("Zero Node", "220"),
        ("Zero Node JS API", "6091"),
        ("News", "38"),
        ("About", "36"),
        ("Contact", "40"),
        ("Zero Currency", "45"),
        ("WZER", "5585"),
        ("Swap", "5738"),
    ]
)


def load_rows(path: Path) -> dict:
    rows = {}
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
            rows[post_id] = {
                "title": title,
                "content": content,
                "status": status,
                "post_date": post_date,
            }
    return rows


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
        "--output-dir",
        default=".",
        help="Directory to write .txt files (default: current directory).",
    )
    parser.add_argument(
        "--footer",
        action="store_true",
        help="Keep footer-like sections (Resources/Community) instead of stripping them.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    rows = load_rows(input_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    for out_name, post_id in TARGETS.items():
        row = rows.get(post_id)
        if not row:
            print(f"Missing ID {post_id} for {out_name}")
            continue
        cleaned = clean_text(row["content"])
        if not args.footer:
            cleaned = strip_footer(cleaned)
        out_path = output_dir / safe_filename(out_name)
        out_path.write_text(cleaned, encoding="ascii", errors="ignore")
        print(f"Wrote {out_path} ({post_id})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
