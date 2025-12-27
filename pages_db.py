#!/usr/bin/env python3
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

EXPECTED_HEADER = ["id", "post_title", "post_content", "post_status", "post_date"]
KNOWN_STATUSES = (
    "publish",
    "future",
    "pending",
    "draft",
    "private",
    "inherit",
    "auto-draft",
    "trash",
)
DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d")


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
    header_mismatch: bool = False
    header_columns: list[str] = field(default_factory=list)
    invalid_id_count: int = 0
    duplicate_id_count: int = 0
    unknown_status_count: int = 0
    invalid_date_count: int = 0


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
    seen_ids: set[str] = set()
    with path.open("r", encoding="utf-8", errors="replace", newline="\n") as handle:
        header = handle.readline()
        if not header:
            raise ParseError(f"Empty input file {path}")
        header = header.lstrip("\r")
        header_cols = [col.strip().lower() for col in header.rstrip("\r\n").split("\t")]
        stats.header_columns = header_cols
        mismatch = header_cols != EXPECTED_HEADER
        stats.header_mismatch = mismatch
        if strict_header and mismatch:
            raise ParseError(format_header_error(path, header_cols, EXPECTED_HEADER))

        for line_no, line in enumerate(handle, start=2):
            line = line.rstrip("\r\n")
            if line.startswith("\r"):
                line = line.lstrip("\r")
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
                    raise ParseError(format_row_error(path, line_no, 5, len(parts)))
                stats.skipped_malformed += 1
                continue

            post_id, title, content, status, post_date = parts
            _validate_id(post_id, stats)
            if post_id:
                if post_id in seen_ids:
                    stats.duplicate_id_count += 1
                else:
                    seen_ids.add(post_id)
            _validate_status(status, stats)
            _validate_date(post_date, stats)
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


def format_header_error(path: Path, actual: list[str], expected: list[str]) -> str:
    return f"Header error in {path}: {actual!r} (expected {expected!r})"


def format_row_error(path: Path, line_no: int, expected: int, got: int) -> str:
    return (
        f"Malformed row at line {line_no} in {path}: expected {expected} columns, "
        f"got {got}"
    )


def _validate_id(value: str, stats: ParseStats) -> None:
    if not value.isdigit() or int(value) <= 0:
        stats.invalid_id_count += 1


def _validate_status(value: str, stats: ParseStats) -> None:
    if value.lower() not in KNOWN_STATUSES:
        stats.unknown_status_count += 1


def _validate_date(value: str, stats: ParseStats) -> None:
    for fmt in DATE_FORMATS:
        try:
            datetime.strptime(value, fmt)
            return
        except ValueError:
            continue
    stats.invalid_date_count += 1


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
    status_key = status.lower()
    if status_key in KNOWN_STATUSES:
        return KNOWN_STATUSES.index(status_key)
    return len(KNOWN_STATUSES)


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
