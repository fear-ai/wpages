# PList: pages_list.py Behavior and Options

## Purpose
Document the CSV listing behavior and CLI options for `pages_list.py`.

## Behavior Summary
- Reads a MySQL tab dump and emits CSV to stdout.
- Uses focus list entries from the --pages file for matching and labels.
- When --only is set, emits only focus matches.
- When --details is set, includes match labels and uses prefix matching by default.
- If --output-dir is provided, also writes `pages_list.csv` into that directory.

## CLI Options (Ordered Groups)
- Standard options: --input, --output-dir, --lines, --bytes, --csv,
  --permit/--permit-header/--permit-columns.
- Pages options: --pages, --prefix/--noprefix, --case/--nocase.
- Filter options: none (not applicable).
- Dump options: --rows.
- Tool-specific options: --only, --details.
