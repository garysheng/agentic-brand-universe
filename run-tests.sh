#!/usr/bin/env bash
# All tests. No API keys, no network, no generation.
#
# Three failure modes this script is shaped around, all of which already happened:
#
# 1. Piping to `tail` masks the exit status, so a runner reports green over a
#    failing test. Every check below captures the real status explicitly.
# 2. Enumerating test files by hand silently omits any test file nobody
#    remembered to add. `compose-spread` shipped two test files that ran nowhere
#    for weeks. So this DISCOVERS test files instead of listing them.
# 3. Showing only the last few lines of output hides the result line whenever a
#    suite prints anything after unittest's summary, which made the reported total
#    silently exclude a whole 22-test suite. So the count is PARSED, not eyeballed,
#    and any suite that produces no parseable count is called out rather than
#    quietly contributing zero.
set -uo pipefail
fail=0
files=0
total=0

run() {  # run <label> <dir> <cmd...>
  local out status n
  out=$( cd "$2" && "${@:3}" 2>&1 ); status=$?
  # grep -oE, not sed: BSD sed (macOS) does not support \? in a basic regex, so the
  # pattern silently matched nothing and every suite reported a count of zero.
  n=$(printf '%s\n' "$out" | grep -oE '^Ran [0-9]+ test' | grep -oE '[0-9]+' | tail -1)
  if [ -z "$n" ]; then
    echo "=== $1 === NO TEST COUNT PARSED (did the suite run?)"
    printf '%s\n' "$out" | tail -4
    fail=1
    return 0
  fi
  total=$((total + n))
  if [ $status -ne 0 ]; then
    echo "=== $1 === $n tests, FAILED (exit $status)"
    printf '%s\n' "$out" | tail -12
    fail=1
  else
    echo "=== $1 === $n tests OK"
  fi
  return 0
}

cd "$(dirname "$0")"

run "engine" "engine" python3 -m unittest discover -s tests -q

# Every skill that has a tests/ directory, discovered rather than listed.
for tf in skills/*/tests/test*.py; do
  [ -e "$tf" ] || continue
  files=$((files + 1))
  skill=$(dirname "$(dirname "$tf")")
  run "$skill/$(basename "$tf")" "$skill" python3 "tests/$(basename "$tf")"
done

# The derived docs. Prose rots silently while the thing it describes keeps moving, so
# staleness is a FAILING TEST rather than something a reader discovers months later.
# (This is also covered by engine/tests/test_docsfile.py; it runs here too so the fix
# is printed in the runner's own output instead of buried in a traceback.)
docs_out=$( cd engine && python3 -m agenticstory.cli build-docs --check 2>&1 ); docs_status=$?
if [ $docs_status -ne 0 ]; then
  echo "=== docs === STALE"
  printf '%s\n' "$docs_out"
  echo "  fix: (cd engine && python3 -m agenticstory.cli build-docs) then commit the result"
  fail=1
else
  echo "=== docs === generated blocks current"
fi

echo
echo "$files skill test file(s) discovered, $total tests total"
if [ $fail -eq 0 ]; then echo "ALL GREEN"; else echo "FAILURES ABOVE"; fi
exit $fail
