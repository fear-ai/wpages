# PList: pages_list.py Behavior and Options

## Purpose
Document the CSV listing behavior and CLI options for `pages_list.py`.

Related
- Workflow overview and shared CLI grouping: WPages.md.
- Content extraction behavior: PText.md and PContent.md.

## Behavior Summary
- Reads a MySQL tab dump and emits CSV to stdout (unless --output-dir is used).
- Uses focus list entries from the --pages file for matching and labels.
- When --only is set, emits only focus matches.
- Without --only, emits focus matches first, then all remaining rows.
- When --details is set, includes match labels and uses prefix matching by default.
- If --output-dir is provided, writes `pages.csv` and `pages.list` into that directory and suppresses stdout.

## Output
- Default CSV columns: title,id,status,date,content_bytes.
- With --details: title,id,status,date,match,focus,content_bytes.
- content_bytes is the UTF-8 byte length of post_content as parsed from the dump.
- pages.list contains titles only (one per line) in the same order as the CSV output, skipping blank titles.

## CLI Options (Ordered Groups)
- Standard options: --input, --output-dir, --lines, --bytes, --csvin,
  --permit/--permit-header/--permit-columns.
- Pages options: --pages, --prefix/--noprefix, --case/--nocase.
- Filter options: none (not applicable).
- Dump options: --rows.
- Tool-specific options: --only, --details.
