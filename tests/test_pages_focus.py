import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from test_pages import TESTS_DIR, run_main

from pages_db import build_title_index, parse_dump
from pages_focus import (
    FocusEntry,
    build_rows_with_keys,
    load_focus_list,
    match_focus_entry,
    match_label,
)

class TestPagesFocus(unittest.TestCase):
    def test_load_focus_list_dedupe_nocase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pages.list"
            path.write_text("Home, home\nAbout\n", encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                entries = load_focus_list(path, case_sensitive=False)
            self.assertEqual([entry.name for entry in entries], ["Home", "About"])
            self.assertEqual([entry.key for entry in entries], ["home", "about"])
            self.assertIn("Duplicate page name skipped", stderr.getvalue())

    def test_load_focus_list_case_sensitive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pages.list"
            path.write_text("Home\nhome\n", encoding="utf-8")
            entries = load_focus_list(path, case_sensitive=True)
            self.assertEqual([entry.name for entry in entries], ["Home", "home"])
            self.assertEqual([entry.key for entry in entries], ["Home", "home"])

    def test_build_rows_with_keys_case_insensitive(self) -> None:
        rows = parse_dump(TESTS_DIR / "sample.out").rows
        rows_with_keys = build_rows_with_keys(rows, case_sensitive=False)
        self.assertEqual(len(rows_with_keys), len(rows))
        self.assertEqual(rows_with_keys[0][0], "home")
        self.assertEqual(rows_with_keys[0][1].title, "Home")

    def test_match_focus_entry_exact_picks_best(self) -> None:
        rows = parse_dump(TESTS_DIR / "sample.out").rows
        title_index = build_title_index(rows, case_sensitive=True)
        rows_with_keys = build_rows_with_keys(rows, case_sensitive=True)
        entry = FocusEntry(name="Home", key="Home", key_len=4)
        label, row = match_focus_entry(
            entry, title_index=title_index, rows_with_keys=rows_with_keys, use_prefix=False
        )
        self.assertEqual(label, "exact")
        self.assertIsNotNone(row)
        self.assertEqual(row.id, "1")

    def test_match_focus_entry_prefix_picks_best(self) -> None:
        rows = parse_dump(TESTS_DIR / "sample.out").rows
        title_index = build_title_index(rows, case_sensitive=False)
        rows_with_keys = build_rows_with_keys(rows, case_sensitive=False)
        entry = FocusEntry(name="Con", key="con", key_len=3)
        label, row = match_focus_entry(
            entry, title_index=title_index, rows_with_keys=rows_with_keys, use_prefix=True
        )
        self.assertEqual(label, "prefix")
        self.assertIsNotNone(row)
        self.assertEqual(row.id, "6")

    def test_match_label_exact_over_prefix(self) -> None:
        rows = parse_dump(TESTS_DIR / "sample.out").rows
        row = next(r for r in rows if r.title == "Contact")
        entries = [
            FocusEntry(name="Con", key="Con", key_len=3),
            FocusEntry(name="Contact", key="Contact", key_len=7),
        ]
        label, focus = match_label(row, entries, case_sensitive=True, use_prefix=True)
        self.assertEqual(label, "exact")
        self.assertEqual(focus, "Contact")

    def test_match_label_longest_prefix(self) -> None:
        rows = parse_dump(TESTS_DIR / "sample.out").rows
        row = next(r for r in rows if r.title == "Contact")
        entries = [
            FocusEntry(name="Con", key="Con", key_len=3),
            FocusEntry(name="Contac", key="Contac", key_len=6),
        ]
        label, focus = match_label(row, entries, case_sensitive=True, use_prefix=True)
        self.assertEqual(label, "prefix")
        self.assertEqual(focus, "Contac")


if __name__ == "__main__":
    run_main()
