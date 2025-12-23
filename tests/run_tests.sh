#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TESTS_DIR="${ROOT}/tests"
PYTHON_BIN="${PYTHON_BIN:-python3}"

results_arg=""
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
    --help|-h)
      echo "Usage: $0 [--results PATH]"
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

check_stderr_contains() {
  name="$1"
  expected="$2"
  if ! rg -F "$expected" "${results}/${name}.err" >/dev/null 2>&1; then
    echo "FAIL: $name missing stderr: $expected"
    failures=$((failures + 1))
  fi
}

run defaults "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/sample.list"
check_status defaults 0
check_stdout defaults "${TESTS_DIR}/default_expected.csv"

run exact "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/sample.list" \
  --only
check_status exact 0
check_stdout exact "${TESTS_DIR}/sample_only_expected.csv"

run csv_mode "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/sample.list" \
  --only --csv
check_status csv_mode 0
check_stdout csv_mode "${TESTS_DIR}/sample_only_expected.csv"

run prefix_flag "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/prefix_only.list" \
  --only --prefix
check_status prefix_flag 0
check_stdout prefix_flag "${TESTS_DIR}/prefix_only_expected.csv"

run noprefix_flag "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/prefix_only.list" \
  --details --noprefix
check_status noprefix_flag 0
check_stdout noprefix_flag "${TESTS_DIR}/prefix_noprefix_expected.csv"

run case_sensitive "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/case.list" \
  --only
check_status case_sensitive 0
check_stdout case_sensitive "${TESTS_DIR}/case_sensitive_expected.csv"

run case_nocase "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/case.list" \
  --only --nocase
check_status case_nocase 0
check_stdout case_nocase "${TESTS_DIR}/case_nocase_expected.csv"

run list_glitch "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/sample_glitch.list" \
  --only
check_status list_glitch 0
check_stdout list_glitch "${TESTS_DIR}/sample_only_expected.csv"

run prefix_details "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/prefix.list" \
  --details
check_status prefix_details 0
check_stdout prefix_details "${TESTS_DIR}/prefix_details_expected.csv"

run prefix_overlap "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/prefix_overlap.list" \
  --details
check_status prefix_overlap 0
check_stdout prefix_overlap "${TESTS_DIR}/prefix_overlap_expected.csv"

run details_sample "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/sample.list" \
  --details
check_status details_sample 0
check_stdout details_sample "${TESTS_DIR}/details_sample_expected.csv"

run details_malformed "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/malformed.out" \
  --pages "${TESTS_DIR}/sample.list" \
  --details
check_status details_malformed 1
check_stderr_contains details_malformed "Error: Malformed row at line 2 in ${TESTS_DIR}/malformed.out: expected 5 columns, got 4"

run details_bad_header "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/bad_header.out" \
  --pages "${TESTS_DIR}/sample.list" \
  --details
check_status details_bad_header 1
check_stderr_contains details_bad_header "Error: Header error in ${TESTS_DIR}/bad_header.out:"

run details_oversized "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/oversized.out" \
  --pages "${TESTS_DIR}/sample.list" \
  --details
check_status details_oversized 0
check_stdout details_oversized "${TESTS_DIR}/details_oversized_expected.csv"

run dups "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/dups.list" \
  --only
check_status dups 0
check_stderr_contains dups "Warning: Duplicate page name skipped: Home"

run dups_case "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/case_dups.list" \
  --only --nocase
check_status dups_case 0
check_stderr_contains dups_case "Warning: Duplicate page name skipped: contact"

run duplicate_id "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/duplicate_id.out" \
  --pages "${TESTS_DIR}/sample.list" \
  --only
check_status duplicate_id 0
check_stderr_contains duplicate_id "Warning: Duplicate id count: 1"


run lines_limit "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/sample.list" \
  --only --lines 2
check_status lines_limit 0
check_stderr_contains lines_limit "Warning: Line limit reached at line 2."

run missing_pages "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/missing.list" \
  --only
check_status missing_pages 1
check_stderr_contains missing_pages "Error: pages list file not found: ${TESTS_DIR}/missing.list"

run empty_pages "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/empty.list" \
  --only
check_status empty_pages 1
check_stderr_contains empty_pages "Error: --only requires at least one page name."

run invalid_pages "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/invalid.list" \
  --only
check_status invalid_pages 1
check_stderr_contains invalid_pages "Error: --only requires at least one page name."


run empty_pages_default "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/empty.list"
check_status empty_pages_default 0
check_stdout empty_pages_default "${TESTS_DIR}/all_rows_expected.csv"

run invalid_pages_default "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/invalid.list"
check_status invalid_pages_default 0
check_stdout invalid_pages_default "${TESTS_DIR}/all_rows_expected.csv"

run bad_lines "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/sample.list" \
  --only --lines -1
check_status bad_lines 1
check_stderr_contains bad_lines "Error: --lines must be 0 or a positive integer."

run bad_bytes "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/sample.list" \
  --only --bytes -1
check_status bad_bytes 1
check_stderr_contains bad_bytes "Error: --bytes must be 0 or a positive integer."

run only_details "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/prefix.list" \
  --only --details
check_status only_details 1
check_stderr_contains only_details "Error: --only cannot be used with --details."

run missing_default_pages bash -c "cd '${missing_pages_dir}' \
  && '${PYTHON_BIN}' '${ROOT}/pages_list.py' --input '${TESTS_DIR}/sample.out' --only"
check_status missing_default_pages 1
check_stderr_contains missing_default_pages "Error: pages list file not found: pages.list"

run empty_default_pages bash -c "cd '${empty_pages_dir}' \
  && '${PYTHON_BIN}' '${ROOT}/pages_list.py' --input '${TESTS_DIR}/sample.out' --only"
check_status empty_default_pages 1
check_stderr_contains empty_default_pages "Error: --only requires at least one page name."

run pages_db "$PYTHON_BIN" "${TESTS_DIR}/test_pages_db.py"
check_status pages_db 0

if [ "$failures" -ne 0 ]; then
  echo "Tests failed: $failures"
  exit 1
fi
echo "Tests passed"
