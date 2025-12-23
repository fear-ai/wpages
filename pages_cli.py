#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

from pages_db import (
    EXPECTED_HEADER,
    ParseError,
    ParseLimits,
    ParseResult,
    format_header_error,
    parse_dump,
)
from pages_focus import FocusEntry, load_focus_list


def warn_count(label: str, count: int, *, path: Path | None = None) -> None:
    if not count:
        return
    if path is None:
        message = f"Warning: {label}: {count}"
    else:
        message = f"Warning: {label}: {count} in {path}"
    print(message, file=sys.stderr)


def warn(message: str) -> None:
    print(f"Warning: {message}", file=sys.stderr)


def warn_if(condition: bool, message: str) -> None:
    if not condition:
        return
    warn(message)


def validate_limits(lines: int, max_bytes: int) -> bool:
    if lines < 0:
        print("Error: --lines must be 0 or a positive integer.", file=sys.stderr)
        return False
    if max_bytes < 0:
        print("Error: --bytes must be 0 or a positive integer.", file=sys.stderr)
        return False
    return True


def load_focus_list_checked(
    path: Path, case_sensitive: bool
) -> list[FocusEntry] | None:
    if not path.exists():
        print(f"Error: pages list file not found: {path}", file=sys.stderr)
        return None
    return load_focus_list(path, case_sensitive)


def parse_dump_checked(
    input_path: Path,
    *,
    max_lines: int,
    max_bytes: int,
    use_csv: bool,
    include_content: bool,
    strict_header: bool = True,
    strict_columns: bool = True,
) -> ParseResult | None:
    limits = ParseLimits(max_lines=max_lines, max_bytes=max_bytes)
    try:
        return parse_dump(
            input_path,
            limits=limits,
            strict_header=strict_header,
            strict_columns=strict_columns,
            use_csv=use_csv,
            include_content=include_content,
        )
    except FileNotFoundError:
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return None
    except ParseError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return None


def emit_parse_warnings(
    result: ParseResult,
    input_path: Path,
    *,
    strict_header: bool,
    strict_columns: bool,
) -> None:
    warn_count("Oversized line count", result.stats.skipped_oversized, path=input_path)
    if not strict_columns:
        warn_count("Malformed row count", result.stats.skipped_malformed, path=input_path)
    if not strict_header:
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
