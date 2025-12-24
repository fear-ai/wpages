#!/usr/bin/env python3
from __future__ import annotations

import argparse
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


def error(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)


def warn_if(condition: bool, message: str) -> None:
    if not condition:
        return
    warn(message)


def add_common_args(
    parser: argparse.ArgumentParser,
    *,
    prefix_default: bool | None,
    case_default: bool | None,
    prefix_help: str,
    case_help: str,
) -> None:
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
        "--prefix",
        dest="use_prefix",
        action="store_true",
        default=prefix_default,
        help=prefix_help,
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
        default=case_default,
        help=case_help,
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
    parser.add_argument(
        "--permit",
        action="store_true",
        default=False,
        help="Allow header mismatch and malformed rows (equivalent to --permit-header --permit-columns).",
    )
    parser.add_argument(
        "--permit-header",
        dest="strict_header",
        action="store_false",
        default=True,
        help="Allow header column names to differ from expected names (default: strict).",
    )
    parser.add_argument(
        "--permit-columns",
        dest="strict_columns",
        action="store_false",
        default=True,
        help="Allow malformed rows; skip and count them (default: strict).",
    )


def validate_limits(lines: int, max_bytes: int) -> bool:
    if lines < 0:
        error("--lines must be 0 or a positive integer.")
        return False
    if max_bytes < 0:
        error("--bytes must be 0 or a positive integer.")
        return False
    return True


def load_focus_entries(path: Path, case_sensitive: bool) -> list[FocusEntry] | None:
    if not path.exists():
        error(f"pages list file not found: {path}")
        return None
    try:
        result = load_focus_list(path, case_sensitive)
    except OSError as exc:
        error(f"pages list could not be read: {path} ({exc})")
        return None
    for name in result.duplicates:
        warn(f"Duplicate page name skipped: {name}")
    return result.entries


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
        error(f"input file not found: {input_path}")
        return None
    except OSError as exc:
        error(f"input file could not be read: {input_path} ({exc})")
        return None
    except ParseError as exc:
        error(str(exc))
        return None


def emit_db_warnings(
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
