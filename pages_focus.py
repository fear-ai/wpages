#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple, TypeAlias
from pages_db import Row, pick_best


class RowKey(NamedTuple):
    key: str
    row: Row


RowsWithKeys: TypeAlias = list[RowKey]
# RowsWithKeys pairs a normalized title key with its Row for prefix matching.

@dataclass(frozen=True)
class FocusEntry:
    name: str
    key: str
    key_len: int


@dataclass(frozen=True)
class FocusListResult:
    entries: list[FocusEntry]
    duplicates: list[str]


def load_focus_list(path: Path, case_sensitive: bool) -> FocusListResult:
    text = path.read_text(encoding="utf-8", errors="replace")
    parts = text.replace(",", "\n").splitlines()
    focus_entries: list[FocusEntry] = []
    duplicates: list[str] = []
    seen = set()
    for part in parts:
        name = part.strip()
        if not name:
            continue
        key = name if case_sensitive else name.lower()
        if key in seen:
            duplicates.append(name)
            continue
        seen.add(key)
        focus_entries.append(FocusEntry(name=name, key=key, key_len=len(key)))
    return FocusListResult(entries=focus_entries, duplicates=duplicates)




def build_rows_keys(rows: list[Row], case_sensitive: bool) -> RowsWithKeys:
    return [
        RowKey(row.title if case_sensitive else row.title.lower(), row) for row in rows
    ]


def match_focus_entry(
    entry: FocusEntry,
    *,
    title_index: dict[str, list[Row]],
    rows_with_keys: RowsWithKeys,
    use_prefix: bool,
) -> tuple[str, Row | None]:
    exact_matches = title_index.get(entry.key, [])
    if exact_matches:
        best = exact_matches[0] if len(exact_matches) == 1 else pick_best(exact_matches)
        return ("exact", best)
    if use_prefix:
        prefix_matches = [
            item.row for item in rows_with_keys if item.key.startswith(entry.key)
        ]
        if prefix_matches:
            best = (
                prefix_matches[0]
                if len(prefix_matches) == 1
                else pick_best(prefix_matches)
            )
            return ("prefix", best)
    return ("none", None)


def match_label(
    row: Row, focus_entries: list[FocusEntry], case_sensitive: bool, use_prefix: bool
) -> tuple[str, str]:
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
