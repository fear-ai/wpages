#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv


EXPECTED_HEADER = ["id", "post_title", "post_content", "post_status", "post_date"]


class ParseError(ValueError):
    pass


@dataclass(frozen=True)
class Row:
    id: str
    title: str
    content: str
    status: str
    date: str


@dataclass(frozen=True)
class ParseLimits:
    max_lines: int = 0
    max_bytes: int = 0


@dataclass
class ParseStats:
    read_lines: int = 0
    skipped_malformed: int = 0
    skipped_oversized: int = 0
    reached_limit: bool = False


@dataclass(frozen=True)
class ParseResult:
    rows: list[Row]
    stats: ParseStats


def parse_dump(
    path: Path,
    *,
    limits: ParseLimits | None = None,
    strict_header: bool = True,
    strict_columns: bool = True,
    use_csv: bool = False,
    include_content: bool = True,
) -> ParseResult:
    if limits is None:
        limits = ParseLimits()

    stats = ParseStats()
    rows: list[Row] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        header = handle.readline()
        if not header:
            raise ParseError(f"Empty input file {path}")
        header_cols = [col.strip().lower() for col in header.rstrip("\r\n").split("\t")]
        if strict_header and header_cols != EXPECTED_HEADER:
            raise ParseError(
                f"Unexpected header columns in {path}: {header_cols!r} "
                f"(expected {EXPECTED_HEADER!r})"
            )

        for line_no, line in enumerate(handle, start=2):
            line = line.rstrip("\r\n")
            if not line:
                continue
            if limits.max_lines and stats.read_lines >= limits.max_lines:
                stats.reached_limit = True
                break
            stats.read_lines += 1
            if limits.max_bytes:
                line_size = len(line.encode("utf-8"))
                if line_size > limits.max_bytes:
                    stats.skipped_oversized += 1
                    continue

            if use_csv:
                reader = csv.reader(
                    [line],
                    delimiter="\t",
                    quoting=csv.QUOTE_NONE,
                    escapechar="\\",
                )
                parts = next(reader)
            else:
                parts = line.split("\t", 4)

            if len(parts) != 5:
                if strict_columns:
                    raise ParseError(
                        f"Malformed row at line {line_no} in {path}: expected 5 columns, "
                        f"got {len(parts)}"
                    )
                stats.skipped_malformed += 1
                continue

            post_id, title, content, status, post_date = parts
            if not include_content:
                content = ""
            rows.append(
                Row(
                    id=post_id,
                    title=title,
                    content=content,
                    status=status,
                    date=post_date,
                )
            )
    return ParseResult(rows=rows, stats=stats)


def build_title_index(rows: list[Row], *, case_sensitive: bool = True) -> dict[str, list[Row]]:
    index: dict[str, list[Row]] = {}
    for row in rows:
        key = row.title if case_sensitive else row.title.lower()
        index.setdefault(key, []).append(row)
    return index


def build_id_index(rows: list[Row]) -> dict[str, list[Row]]:
    index: dict[str, list[Row]] = {}
    for row in rows:
        index.setdefault(row.id, []).append(row)
    return index


def status_rank(status: str) -> int:
    order = {
        "publish": 0,
        "draft": 1,
        "private": 2,
    }
    return order.get(status.lower(), 3)


def pick_best(matches: list[Row]) -> Row | None:
    best = None
    for row in matches:
        if best is None:
            best = row
            continue
        row_rank = status_rank(row.status)
        best_rank = status_rank(best.status)
        if row_rank < best_rank:
            best = row
            continue
        if row_rank == best_rank and row.date > best.date:
            best = row
    return best
