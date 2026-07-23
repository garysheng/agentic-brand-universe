#!/usr/bin/env bash
# All tests. No API keys, no network, no generation.
# NOTE: piping to tail masks the exit status, so every check below captures the
# real status explicitly. A runner that reports green over a failing test is worse
# than no runner. This one did exactly that once.
set -uo pipefail
fail=0

run() {  # run <label> <dir> <cmd...>
  echo "=== $1 ==="
  local out status
  out=$( cd "$2" && "${@:3}" 2>&1 ); status=$?
  echo "$out" | tail -4
  [ $status -ne 0 ] && { echo "  ^^ FAILED (exit $status)"; fail=1; }
  return 0
}

run "engine" "engine" python3 -m unittest discover -s tests -q
run "skills/lint-universe" "skills/lint-universe" python3 tests/test_lint.py
run "skills/compose" "skills/compose" python3 tests/test_compose.py
run "skills/cover" "skills/cover" python3 tests/test_cover_scripts.py
run "skills/lock-references" "skills/lock-references" python3 tests/test_chain_matrix.py

echo
if [ $fail -eq 0 ]; then echo "ALL GREEN"; else echo "FAILURES ABOVE"; fi
exit $fail
