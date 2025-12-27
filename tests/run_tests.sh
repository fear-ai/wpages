#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TESTS_DIR="${ROOT}/tests"
PYTHON_BIN="${PYTHON_BIN:-python3}"

results_arg=""
group="all"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --results)
      if [ "$#" -lt 2 ]; then
        echo "Error: --results requires a path." >&2
        exit 2
      fi
      results_arg="$2"
      shift 2
      ;;
    --results=*)
      results_arg="${1#--results=}"
      shift
      ;;
    --group)
      if [ "$#" -lt 2 ]; then
        echo "Error: --group requires a value." >&2
        exit 2
      fi
      group="$2"
      shift 2
      ;;
    --group=*)
      group="${1#--group=}"
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [--results PATH] [--group all|cli|list|text|content|unit]"
      exit 0
      ;;
    *)
      echo "Error: unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [ -n "$results_arg" ]; then
  results="$results_arg"
elif [ -n "${RESULTS:-}" ]; then
  results="$RESULTS"
else
  date_str="$(date +%Y%m%d_%H%M%S)"
  results="${TESTS_DIR}/results_${date_str}"
fi
mkdir -p "$results"
missing_pages_dir="${results}/work_missing_pages"
empty_pages_dir="${results}/work_empty_pages"
mkdir -p "$missing_pages_dir" "$empty_pages_dir"
: > "${empty_pages_dir}/pages.list"

failures=0

run() {
  name="$1"
  shift
  stdout="${results}/${name}.out"
  stderr="${results}/${name}.err"
  set +e
  "$@" >"$stdout" 2>"$stderr"
  status=$?
  set -e
  echo "Test: $name -> $status"
  echo "$status" > "${results}/${name}.status"
}

check_status() {
  name="$1"
  expected="$2"
  actual="$(cat "${results}/${name}.status")"
  if [ "$actual" -ne "$expected" ]; then
    echo "FAIL: $name status $actual (expected $expected)"
    failures=$((failures + 1))
  fi
}

check_stdout() {
  name="$1"
  expected="$2"
  diff -u "$expected" "${results}/${name}.out" > "${results}/${name}.diff"
  if [ -s "${results}/${name}.diff" ]; then
    echo "FAIL: $name stdout mismatch (see ${results}/${name}.diff)"
    failures=$((failures + 1))
  fi
}

check_file() {
  name="$1"
  actual="$2"
  expected="$3"
  diff -u "$expected" "$actual" > "${results}/${name}_$(basename "$expected").diff"
  if [ -s "${results}/${name}_$(basename "$expected").diff" ]; then
    echo "FAIL: $name file mismatch for $actual (see ${results}/${name}_$(basename "$expected").diff)"
    failures=$((failures + 1))
  fi
}

check_file_missing() {
  name="$1"
  path="$2"
  if [ -e "$path" ]; then
    echo "FAIL: $name expected no file at $path"
    failures=$((failures + 1))
  fi
}

check_stderr_contains() {
  name="$1"
  expected="$2"
  if ! rg -F "$expected" "${results}/${name}.err" >/dev/null 2>&1; then
    echo "FAIL: $name missing stderr: $expected"
    failures=$((failures + 1))
  fi
}

run_list() {
  run defaults "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/sample.out"     --pages "${TESTS_DIR}/sample.list"
  check_status defaults 0
  check_stdout defaults "${TESTS_DIR}/default_expected.csv"

  run exact "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/sample.out"     --pages "${TESTS_DIR}/sample.list"     --only
  check_status exact 0
  check_stdout exact "${TESTS_DIR}/sample_only_expected.csv"

  run csv_mode "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/sample.out"     --pages "${TESTS_DIR}/sample.list"     --only --csv
  check_status csv_mode 0
  check_stdout csv_mode "${TESTS_DIR}/sample_only_expected.csv"

  run prefix_flag "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/sample.out"     --pages "${TESTS_DIR}/prefix_only.list"     --only --prefix
  check_status prefix_flag 0
  check_stdout prefix_flag "${TESTS_DIR}/prefix_only_expected.csv"

  run noprefix_flag "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/sample.out"     --pages "${TESTS_DIR}/prefix_only.list"     --details --noprefix
  check_status noprefix_flag 0
  check_stdout noprefix_flag "${TESTS_DIR}/prefix_noprefix_expected.csv"

  run case_sensitive "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/sample.out"     --pages "${TESTS_DIR}/case.list"     --only
  check_status case_sensitive 0
  check_stdout case_sensitive "${TESTS_DIR}/case_sensitive_expected.csv"

  run case_nocase "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/sample.out"     --pages "${TESTS_DIR}/case.list"     --only --nocase
  check_status case_nocase 0
  check_stdout case_nocase "${TESTS_DIR}/case_nocase_expected.csv"

  run list_glitch "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/sample.out"     --pages "${TESTS_DIR}/sample_glitch.list"     --only
  check_status list_glitch 0
  check_stdout list_glitch "${TESTS_DIR}/sample_only_expected.csv"

  run details_sample "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/sample.out"     --pages "${TESTS_DIR}/sample.list"     --details
  check_status details_sample 0
  check_stdout details_sample "${TESTS_DIR}/details_sample_expected.csv"

  run prefix_details "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/sample.out"     --pages "${TESTS_DIR}/prefix.list"     --details
  check_status prefix_details 0
  check_stdout prefix_details "${TESTS_DIR}/prefix_details_expected.csv"

  run prefix_overlap "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/sample.out"     --pages "${TESTS_DIR}/prefix_overlap.list"     --details
  check_status prefix_overlap 0
  check_stdout prefix_overlap "${TESTS_DIR}/prefix_overlap_expected.csv"

  run details_missing "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/missing_row.out"     --pages "${TESTS_DIR}/missing_page.list"     --details
  check_status details_missing 0
  check_stdout details_missing "${TESTS_DIR}/details_missing_expected.csv"
  check_stderr_contains details_missing "Warning: Missing page: Missing"

  run details_oversized "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/oversized.out"     --pages "${TESTS_DIR}/sample.list"     --details
  check_status details_oversized 0
  check_stdout details_oversized "${TESTS_DIR}/details_oversized_expected.csv"

  run permit_header "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/alt_header.out"     --pages "${TESTS_DIR}/sample.list"     --only --permit-header
  check_status permit_header 0
  check_stdout permit_header "${TESTS_DIR}/permit_header_expected.csv"
  check_stderr_contains permit_header "Warning: Header error"

  run permit_columns "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/malformed.out"     --pages "${TESTS_DIR}/sample.list"     --permit-columns
  check_status permit_columns 0
  check_stdout permit_columns "${TESTS_DIR}/permit_columns_expected.csv"
  check_stderr_contains permit_columns "Warning: Malformed row count: 1"

  run permit_both "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/alt_header.out"     --pages "${TESTS_DIR}/sample.list"     --only --permit
  check_status permit_both 0
  check_stdout permit_both "${TESTS_DIR}/permit_header_expected.csv"
  check_stderr_contains permit_both "Warning: Header error"

  run dups "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/sample.out"     --pages "${TESTS_DIR}/dups.list"     --only
  check_status dups 0
  check_stderr_contains dups "Warning: Duplicate page name skipped: Home"

  run dups_case "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/sample.out"     --pages "${TESTS_DIR}/case_dups.list"     --only --nocase
  check_status dups_case 0
  check_stderr_contains dups_case "Warning: Duplicate page name skipped: contact"

  run duplicate_id "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/duplicate_id.out"     --pages "${TESTS_DIR}/sample.list"     --only
  check_status duplicate_id 0
  check_stderr_contains duplicate_id "Warning: Duplicate id count: 1"

  run lines_limit "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/sample.out"     --pages "${TESTS_DIR}/sample.list"     --only --lines 2
  check_status lines_limit 0
  check_stderr_contains lines_limit "Warning: Line limit reached at line 2."

  run details_malformed "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/malformed.out"     --pages "${TESTS_DIR}/sample.list"     --details
  check_status details_malformed 1
  check_stderr_contains details_malformed "Error: Malformed row at line 2 in ${TESTS_DIR}/malformed.out: expected 5 columns, got 4"

  run details_bad_header "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/bad_header.out"     --pages "${TESTS_DIR}/sample.list"     --details
  check_status details_bad_header 1
  check_stderr_contains details_bad_header "Error: Header error in ${TESTS_DIR}/bad_header.out:"

  run only_details "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/sample.out"     --pages "${TESTS_DIR}/prefix.list"     --only --details
  check_status only_details 1
  check_stderr_contains only_details "Error: --only cannot be used with --details."

  run bad_lines "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/sample.out"     --pages "${TESTS_DIR}/sample.list"     --only --lines -1
  check_status bad_lines 1
  check_stderr_contains bad_lines "Error: --lines must be 0 or a positive integer."

  run bad_bytes "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/sample.out"     --pages "${TESTS_DIR}/sample.list"     --only --bytes -1
  check_status bad_bytes 1
  check_stderr_contains bad_bytes "Error: --bytes must be 0 or a positive integer."

  run missing_pages "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/sample.out"     --pages "${TESTS_DIR}/missing.list"     --only
  check_status missing_pages 1
  check_stderr_contains missing_pages "Error: pages list file not found: ${TESTS_DIR}/missing.list"

  run empty_pages "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/sample.out"     --pages "${TESTS_DIR}/empty.list"     --only
  check_status empty_pages 1
  check_stderr_contains empty_pages "Error: pages list must include at least one page name."

  run invalid_pages "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/sample.out"     --pages "${TESTS_DIR}/invalid.list"     --only
  check_status invalid_pages 1
  check_stderr_contains invalid_pages "Error: pages list must include at least one page name."

  run missing_default_pages bash -c "cd '${missing_pages_dir}'     && '${PYTHON_BIN}' '${ROOT}/pages_list.py' --input '${TESTS_DIR}/sample.out' --only"
  check_status missing_default_pages 1
  check_stderr_contains missing_default_pages "Error: pages list file not found: pages.list"

  run empty_default_pages bash -c "cd '${empty_pages_dir}'     && '${PYTHON_BIN}' '${ROOT}/pages_list.py' --input '${TESTS_DIR}/sample.out' --only"
  check_status empty_default_pages 1
  check_stderr_contains empty_default_pages "Error: pages list must include at least one page name."

  run empty_pages_default "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/sample.out"     --pages "${TESTS_DIR}/empty.list"
  check_status empty_pages_default 0
  check_stdout empty_pages_default "${TESTS_DIR}/all_rows_expected.csv"

  run invalid_pages_default "$PYTHON_BIN" "${ROOT}/pages_list.py"     --input "${TESTS_DIR}/sample.out"     --pages "${TESTS_DIR}/invalid.list"
  check_status invalid_pages_default 0
  check_stdout invalid_pages_default "${TESTS_DIR}/all_rows_expected.csv"
}

run_text() {
  pages_text_dir="${results}/pages_text"
  run pages_text_basic "$PYTHON_BIN" "${ROOT}/pages_text.py" \
    --input "${TESTS_DIR}/sample.out" \
    --pages "${TESTS_DIR}/sample.list" \
    --output-dir "$pages_text_dir"
  check_status pages_text_basic 0
  check_file pages_text_basic "${pages_text_dir}/Home.txt" "${TESTS_DIR}/pages_text_home_expected.txt"
  check_file pages_text_basic "${pages_text_dir}/About.txt" "${TESTS_DIR}/pages_text_about_expected.txt"
  check_file pages_text_basic "${pages_text_dir}/Contact.txt" "${TESTS_DIR}/pages_text_contact_expected.txt"

  pages_text_nested="${results}/pages_text_nested/inner"
  run pages_text_output_dir_nested "$PYTHON_BIN" "${ROOT}/pages_text.py" \
    --input "${TESTS_DIR}/sample.out" \
    --pages "${TESTS_DIR}/sample.list" \
    --output-dir "$pages_text_nested"
  check_status pages_text_output_dir_nested 0
  check_file pages_text_output_dir_nested "${pages_text_nested}/Home.txt" "${TESTS_DIR}/pages_text_home_expected.txt"
  check_file pages_text_output_dir_nested "${pages_text_nested}/About.txt" "${TESTS_DIR}/pages_text_about_expected.txt"
  check_file pages_text_output_dir_nested "${pages_text_nested}/Contact.txt" "${TESTS_DIR}/pages_text_contact_expected.txt"

  pages_text_file="${results}/pages_text_output_dir.txt"
  : > "$pages_text_file"
  run pages_text_output_dir_file "$PYTHON_BIN" "${ROOT}/pages_text.py" \
    --input "${TESTS_DIR}/sample.out" \
    --pages "${TESTS_DIR}/sample.list" \
    --output-dir "$pages_text_file"
  check_status pages_text_output_dir_file 1
  check_stderr_contains pages_text_output_dir_file \
    "Error: output path is not a directory: ${pages_text_file}"

  pages_text_missing_dir="${results}/pages_text_missing"
  run pages_text_missing "$PYTHON_BIN" "${ROOT}/pages_text.py" \
    --input "${TESTS_DIR}/missing_row.out" \
    --pages "${TESTS_DIR}/missing_page.list" \
    --output-dir "$pages_text_missing_dir"
  check_status pages_text_missing 0
  check_file pages_text_missing "${pages_text_missing_dir}/Home.txt" "${TESTS_DIR}/pages_text_home_expected.txt"
  check_file_missing pages_text_missing "${pages_text_missing_dir}/Missing.txt"
  check_stderr_contains pages_text_missing "Warning: Missing page: Missing"

  pages_text_utf_dir="${results}/pages_text_utf"
  run pages_text_utf "$PYTHON_BIN" "${ROOT}/pages_text.py" \
    --input "${TESTS_DIR}/content.out" \
    --pages "${TESTS_DIR}/content.list" \
    --output-dir "$pages_text_utf_dir" \
    --utf
  check_status pages_text_utf 0
  check_file pages_text_utf "${pages_text_utf_dir}/Dirty.txt" "${TESTS_DIR}/pages_text_dirty_utf_expected.txt"

  pages_text_raw_dir="${results}/pages_text_raw"
  run pages_text_raw "$PYTHON_BIN" "${ROOT}/pages_text.py" \
    --input "${TESTS_DIR}/content.out" \
    --pages "${TESTS_DIR}/content.list" \
    --output-dir "$pages_text_raw_dir" \
    --raw
  check_status pages_text_raw 0
  check_file pages_text_raw "${pages_text_raw_dir}/Dirty.txt" "${TESTS_DIR}/pages_text_dirty_raw_expected.txt"

  pages_text_notab_nonl_dir="${results}/pages_text_notab_nonl"
  run pages_text_notab_nonl "$PYTHON_BIN" "${ROOT}/pages_text.py" \
    --input "${TESTS_DIR}/escapes.out" \
    --pages "${TESTS_DIR}/escapes.list" \
    --output-dir "$pages_text_notab_nonl_dir" \
    --notab \
    --nonl
  check_status pages_text_notab_nonl 0
  check_file pages_text_notab_nonl "${pages_text_notab_nonl_dir}/Escapes.txt" "${TESTS_DIR}/escapes_notab_nonl_expected.txt"
}

run_content() {
  pages_content_dir="${results}/pages_content"
  run pages_content_basic "$PYTHON_BIN" "${ROOT}/pages_content.py" \
    --input "${TESTS_DIR}/sample.out" \
    --pages "${TESTS_DIR}/sample.list" \
    --output-dir "$pages_content_dir"
  check_status pages_content_basic 0
  check_file pages_content_basic "${pages_content_dir}/Home.txt" "${TESTS_DIR}/pages_text_home_expected.txt"
  check_file pages_content_basic "${pages_content_dir}/About.txt" "${TESTS_DIR}/pages_text_about_expected.txt"
  check_file pages_content_basic "${pages_content_dir}/Contact.txt" "${TESTS_DIR}/pages_text_contact_expected.txt"

  pages_content_nested="${results}/pages_content_nested/inner"
  run pages_content_output_dir_nested "$PYTHON_BIN" "${ROOT}/pages_content.py" \
    --input "${TESTS_DIR}/sample.out" \
    --pages "${TESTS_DIR}/sample.list" \
    --output-dir "$pages_content_nested"
  check_status pages_content_output_dir_nested 0
  check_file pages_content_output_dir_nested "${pages_content_nested}/Home.txt" "${TESTS_DIR}/pages_text_home_expected.txt"
  check_file pages_content_output_dir_nested "${pages_content_nested}/About.txt" "${TESTS_DIR}/pages_text_about_expected.txt"
  check_file pages_content_output_dir_nested "${pages_content_nested}/Contact.txt" "${TESTS_DIR}/pages_text_contact_expected.txt"

  pages_content_file="${results}/pages_content_output_dir.txt"
  : > "$pages_content_file"
  run pages_content_output_dir_file "$PYTHON_BIN" "${ROOT}/pages_content.py" \
    --input "${TESTS_DIR}/sample.out" \
    --pages "${TESTS_DIR}/sample.list" \
    --output-dir "$pages_content_file"
  check_status pages_content_output_dir_file 1
  check_stderr_contains pages_content_output_dir_file \
    "Error: output path is not a directory: ${pages_content_file}"

  pages_content_missing_dir="${results}/pages_content_missing"
  run pages_content_missing "$PYTHON_BIN" "${ROOT}/pages_content.py" \
    --input "${TESTS_DIR}/missing_row.out" \
    --pages "${TESTS_DIR}/missing_page.list" \
    --output-dir "$pages_content_missing_dir"
  check_status pages_content_missing 0
  check_file pages_content_missing "${pages_content_missing_dir}/Home.txt" "${TESTS_DIR}/pages_text_home_expected.txt"
  check_file_missing pages_content_missing "${pages_content_missing_dir}/Missing.txt"
  check_stderr_contains pages_content_missing "Warning: Missing page: Missing"

  pages_content_html_dir="${results}/pages_content_html_default"
  run pages_content_html_default "$PYTHON_BIN" "${ROOT}/pages_content.py" \
    --input "${TESTS_DIR}/content.out" \
    --pages "${TESTS_DIR}/content.list" \
    --output-dir "$pages_content_html_dir"
  check_status pages_content_html_default 0
  check_file pages_content_html_default "${pages_content_html_dir}/HTML.txt" "${TESTS_DIR}/pages_content_html_expected.txt"
  check_file pages_content_html_default "${pages_content_html_dir}/Dirty.txt" "${TESTS_DIR}/pages_content_dirty_expected.txt"

  pages_content_tab_dir="${results}/pages_content_html_tab"
  run pages_content_html_tab "$PYTHON_BIN" "${ROOT}/pages_content.py" \
    --input "${TESTS_DIR}/content.out" \
    --pages "${TESTS_DIR}/content.list" \
    --output-dir "$pages_content_tab_dir" \
    --table-delim tab
  check_status pages_content_html_tab 0
  check_file pages_content_html_tab "${pages_content_tab_dir}/HTML.txt" "${TESTS_DIR}/pages_content_html_tab_expected.txt"
  check_file pages_content_html_tab "${pages_content_tab_dir}/Dirty.txt" "${TESTS_DIR}/pages_content_dirty_expected.txt"

  pages_content_replace_dir="${results}/pages_content_replace"
  run pages_content_replace_char "$PYTHON_BIN" "${ROOT}/pages_content.py" \
    --input "${TESTS_DIR}/content.out" \
    --pages "${TESTS_DIR}/content.list" \
    --output-dir "$pages_content_replace_dir" \
    --replace "?"
  check_status pages_content_replace_char 0
  check_file pages_content_replace_char "${pages_content_replace_dir}/HTML.txt" "${TESTS_DIR}/pages_content_html_expected.txt"
  check_file pages_content_replace_char "${pages_content_replace_dir}/Dirty.txt" "${TESTS_DIR}/pages_content_dirty_replace_expected.txt"

  pages_content_bad_replace_dir="${results}/pages_content_bad_replace"
  run pages_content_replace_char_bad "$PYTHON_BIN" "${ROOT}/pages_content.py" \
    --input "${TESTS_DIR}/content.out" \
    --pages "${TESTS_DIR}/content.list" \
    --output-dir "$pages_content_bad_replace_dir" \
    --replace "??"
  check_status pages_content_replace_char_bad 1
  check_stderr_contains pages_content_replace_char_bad \
    "Error: --replace must be a single ASCII character."

  pages_content_md_dir="${results}/pages_content_markdown"
  run pages_content_markdown "$PYTHON_BIN" "${ROOT}/pages_content.py" \
    --input "${TESTS_DIR}/content.out" \
    --pages "${TESTS_DIR}/content.list" \
    --output-dir "$pages_content_md_dir" \
    --format markdown
  check_status pages_content_markdown 0
  check_file pages_content_markdown "${pages_content_md_dir}/HTML.md" "${TESTS_DIR}/pages_content_html.md"
  check_file pages_content_markdown "${pages_content_md_dir}/Dirty.md" "${TESTS_DIR}/pages_content_row.md"

  pages_content_utf_dir="${results}/pages_content_utf"
  run pages_content_utf "$PYTHON_BIN" "${ROOT}/pages_content.py" \
    --input "${TESTS_DIR}/content.out" \
    --pages "${TESTS_DIR}/content.list" \
    --output-dir "$pages_content_utf_dir" \
    --utf
  check_status pages_content_utf 0
  check_file pages_content_utf "${pages_content_utf_dir}/Dirty.txt" "${TESTS_DIR}/pages_content_dirty_utf_expected.txt"

  pages_content_raw_dir="${results}/pages_content_raw"
  run pages_content_raw "$PYTHON_BIN" "${ROOT}/pages_content.py" \
    --input "${TESTS_DIR}/content.out" \
    --pages "${TESTS_DIR}/content.list" \
    --output-dir "$pages_content_raw_dir" \
    --raw
  check_status pages_content_raw 0
  check_file pages_content_raw "${pages_content_raw_dir}/Dirty.txt" "${TESTS_DIR}/pages_content_dirty_raw_expected.txt"

  pages_content_notab_nonl_dir="${results}/pages_content_notab_nonl"
  run pages_content_notab_nonl "$PYTHON_BIN" "${ROOT}/pages_content.py" \
    --input "${TESTS_DIR}/escapes.out" \
    --pages "${TESTS_DIR}/escapes.list" \
    --output-dir "$pages_content_notab_nonl_dir" \
    --notab \
    --nonl
  check_status pages_content_notab_nonl 0
  check_file pages_content_notab_nonl "${pages_content_notab_nonl_dir}/Escapes.txt" "${TESTS_DIR}/escapes_notab_nonl_expected.txt"
}

run_unit() {
  run pages_db "$PYTHON_BIN" "${TESTS_DIR}/test_pages_db.py"
  check_status pages_db 0

  run pages_focus "$PYTHON_BIN" "${TESTS_DIR}/test_pages_focus.py"
  check_status pages_focus 0

  run pages_cli "$PYTHON_BIN" "${TESTS_DIR}/test_pages_cli.py"
  check_status pages_cli 0

  run pages_text "$PYTHON_BIN" "${TESTS_DIR}/test_pages_text.py"
  check_status pages_text 0

  run pages_util "$PYTHON_BIN" "${TESTS_DIR}/test_pages_util.py"
  check_status pages_util 0

  run pages_content "$PYTHON_BIN" "${TESTS_DIR}/test_pages_content.py"
  check_status pages_content 0
}

case "$group" in
  all)
    run_unit
    run_list
    run_text
    run_content
    ;;
  cli)
    run_list
    run_text
    run_content
    ;;
  list)
    run_list
    ;;
  text)
    run_text
    ;;
  content)
    run_content
    ;;
  unit)
    run_unit
    ;;
  *)
    echo "Error: unknown group: $group" >&2
    exit 2
    ;;
esac
if [ "$failures" -ne 0 ]; then
  echo "Tests failed: $failures"
  exit 1
fi
echo "Tests passed"
