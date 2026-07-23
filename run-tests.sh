#!/usr/bin/env bash
# All tests. No API keys, no network, no generation.
#
# Two failure modes this script is shaped around, both of which already happened:
#
# 1. Piping to `tail` masks the exit status, so a runner reports green over a
#    failing test. Every check below captures the real status explicitly.
# 2. Enumerating test files by hand silently omits any test file nobody
#    remembered to add. `compose-spread` shipped two test files that ran nowhere
#    for weeks. So this DISCOVERS test files instead of listing them, and a new
#    test file is picked up the moment it exists.
set -uo pipefail
fail=0
found=0

run() {  # run <label> <dir> <cmd...>
  echo "=== $1 ==="
  local out status
  out=$( cd "$2" && "${@:3}" 2>&1 ); status=$?
  echo "$out" | tail -4
  [ $status -ne 0 ] && { echo "  ^^ FAILED (exit $status)"; fail=1; }
  return 0
}

cd "$(dirname "$0")"

run "engine" "engine" python3 -m unittest discover -s tests -q

# Every skill that has a tests/ directory, discovered rather than listed.
for tf in skills/*/tests/test*.py; do
  [ -e "$tf" ] || continue
  found=$((found + 1))
  skill=$(dirname "$(dirname "$tf")")
  run "$skill/$(basename "$tf")" "$skill" python3 "tests/$(basename "$tf")"
done

echo
echo "discovered $found skill test file(s)"
if [ $fail -eq 0 ]; then echo "ALL GREEN"; else echo "FAILURES ABOVE"; fi
exit $fail
