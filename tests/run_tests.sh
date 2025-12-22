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
  date_str="$(date +%Y%m%d)"
  results="${TESTS_DIR}/results_${date_str}"
  if [ -e "$results" ]; then
    i=2
    while [ -e "${results}_$i" ]; do i=$((i+1)); done
    results="${results}_$i"
  fi
fi
mkdir -p "$results"

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

run exact "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/sample.list" \
  --only
check_status exact 0
check_stdout exact "${TESTS_DIR}/sample_only_expected.csv"

run prefix_details "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/prefix.list" \
  --only --details
check_status prefix_details 0
check_stdout prefix_details "${TESTS_DIR}/prefix_details_expected.csv"

run dups "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/dups.list" \
  --only
check_status dups 0
check_stderr_contains dups "Warning: duplicate page name skipped: Home"

run malformed "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/malformed.out" \
  --pages "${TESTS_DIR}/sample.list" \
  --only
check_status malformed 0
check_stderr_contains malformed "Warning: skipped 1 malformed line(s) in ${TESTS_DIR}/malformed.out"

run bad_header "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/bad_header.out" \
  --pages "${TESTS_DIR}/sample.list" \
  --only
check_status bad_header 1
check_stderr_contains bad_header "Error: Unexpected header columns:"

run oversized "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/oversized.out" \
  --pages "${TESTS_DIR}/sample.list" \
  --only --bytes 100
check_status oversized 0
check_stderr_contains oversized "Warning: skipped 1 oversized line(s) in ${TESTS_DIR}/oversized.out"

run lines_limit "$PYTHON_BIN" "${ROOT}/pages_list.py" \
  --input "${TESTS_DIR}/sample.out" \
  --pages "${TESTS_DIR}/sample.list" \
  --only --lines 2
check_status lines_limit 0
check_stderr_contains lines_limit "Warning: stopped after 2 line(s) due to --lines limit."

if [ "$failures" -ne 0 ]; then
  echo "Tests failed: $failures"
  exit 1
fi
echo "Tests passed"
