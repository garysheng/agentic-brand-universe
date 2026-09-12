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

# Every PROVIDER that has a tests/ directory. Added 2026-08-06: `providers/` was not
# discovered at all, so providers/*/prompt_guards.py -- the chokepoint every single render
# passes through, and the declared single home of the standing rules -- had zero tests and
# two byte-identical copies nobody was comparing.
for tf in providers/*/tests/test*.py; do
  [ -e "$tf" ] || continue
  files=$((files + 1))
  prov=$(dirname "$(dirname "$tf")")
  # DISCOVER, never execute the file. Executing it runs whatever `if __name__ ==
  # "__main__": unittest.main()` block the author left mid-file, so any class defined
  # BELOW that block is silently never collected: the file passes, the count looks
  # plausible, and the new tests simply do not exist as far as this suite is
  # concerned. Six guard tests were invisible that way on 2026-08-09 while passing in
  # isolation. `discover` collects the module regardless, which the engine line above
  # already does.
  run "$prov/$(basename "$tf")" "$prov" python3 -m unittest discover -s tests -q
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

# --- A TEST THAT NEVER RAN IS WORSE THAN NO TEST, because the suite reports OK either way.
#
# Earned 2026-09-12. Five tests were appended to skills/explore/tests/test_explore.py, which
# carries `if __name__ == "__main__": unittest.main()` partway down the file. Python runs top to
# bottom, so main() fired before the new class was defined: the tests never collected, the file
# reported "Ran 4 tests ... OK", and this runner added 4 to the total and printed green. The only
# reason it was caught is that the count was expected to be 9.
#
# The count check above cannot see this. It asks whether a suite produced a number, not whether
# the number covers every test in the file. So the shape gets refused directly: no test file may
# define anything after its main() guard, which is the one arrangement that hides tests.
echo
guard_fail=0
while IFS= read -r f; do
  g=$(grep -n '^if __name__ == "__main__":' "$f" | head -1 | cut -d: -f1)
  [ -z "$g" ] && continue
  # anything that looks like a definition after the guard line
  after=$(awk -v g="$g" 'NR>g && /^(class|def) /' "$f")
  if [ -n "$after" ]; then
    echo "=== test-guard === $f DEFINES CODE AFTER ITS main() GUARD; those tests never run:"
    printf '%s\n' "$after" | sed 's/^/      /'
    echo "      fix: move the \`if __name__ == \"__main__\"\` block to the END of the file"
    guard_fail=1
  fi
done < <(find skills providers engine -name "test_*.py" -not -path "*/__pycache__/*" 2>/dev/null)
if [ $guard_fail -eq 0 ]; then
  echo "=== test-guard === no test file hides tests after its main() guard"
else
  fail=1
fi

echo
echo "$files skill test file(s) discovered, $total tests total"
if [ $fail -eq 0 ]; then echo "ALL GREEN"; else echo "FAILURES ABOVE"; fi
exit $fail
