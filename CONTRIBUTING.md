# Contributing to Agentic Brand Universe

**Branch into `develop`, never into `master`.** That is the one rule with teeth, and the
reason is specific to how this repo ships: the repo IS the plugin marketplace
(`.claude-plugin/marketplace.json` declares `source: "."`), and Claude Code's marketplace
source format is `{"source": "github", "repo": "..."}` with no ref field, so an install
always tracks the DEFAULT BRANCH. Verified 2026-09-12 by reading an installed marketplace
record.

So `master` is not a development branch. Every commit on it is a release to everybody who
runs `/plugin update`.

```
develop   ← your pull request lands here, CI runs, things can be wrong for a while
master    ← what every user installs. Only a release merges here, and it carries a tag.
```

## Filing a gap instead of fixing one

Use the **Framework gap** issue template. Its bar is one sentence: you can name the next
invocation that needs the thing. `X is missing, and the next invocation that needs X is Y.`
A gap with no named next invocation is speculation, and if you cannot write "Still open
because" you are deferring work rather than filing a gap.

There were 1,391 lines of these in a markdown file until 2026-09-12. They are issues now,
under the `gap` label, carrying their original `G` ids in their titles.

## What a pull request needs

1. **`./run-tests.sh` green.** CI runs it on every PR, including `build-docs --check`, so a
   change that adds a skill, a CLI verb, a form or a provider must ALSO commit the
   regenerated docs. The fix is one command, never a prose edit:
   `(cd engine && python3 -m agenticstory.cli build-docs)`.
2. **Tests in the same commit as the behaviour change.** If you must split, tests go first.
   A change that genuinely cannot be tested says so in the commit body rather than skipping
   it silently.
3. **Prove the test bites.** Revert the behaviour and confirm the test fails. A test written
   against code that already passes proves only that it compiles. Assert that your mutation
   actually applied, because a patch that silently fails to match reports SURVIVED and sends
   you rewriting a test that was fine.
4. **Never hand-edit inside a `BEGIN GENERATED` fence.** The generator owns those blocks and
   `--check` fails the suite when they drift.
5. **Any observable change goes in `SPEC.md` in the same commit**, in the section a reader
   would look in, with what it does, when it applies, and the defect that earned it. Not a
   changelog line. This has failed twice in this repo's history, which is why it is a rule:
   the code change is the interesting part and the spec text feels like paperwork, and the
   paperwork is the only thing a user of the framework can actually read.
6. **One line in `SAVE-LOG.md`**, under about 80 words. Shape:
   `- <date> v<version> — <what changed>. <the defect that earned it>.` Anyone who needs the
   reasoning opens the commit.

## What this framework is opinionated about

Read these before proposing a design; they are the house positions and a PR that fights them
will get a long comment rather than a merge.

- **Never delete or weaken a check to make a run go green.** A check failing against
  reasonable behaviour is either finding a real defect or is itself wrong, and both are worth
  the hour. Widening a gate is sometimes right, and it ships with mutation tests proving the
  gate still bites.
- **A refusal at the moment of misuse beats a doc explaining the right way.** Anything that
  depends on having read something earlier and remembered it fails on a long session.
- **Deterministic output is drawn in CODE, never prompted.** Anything whose correctness is a
  number is a generator.
- **Every generated asset carries its provenance** recording model, exact prompt and every
  input by path. DECLARED is not PASSED: when a record could state either what canon says or
  what the run did, it must say which.
- **Never rewrite a historical record.** `.recipe.json` files and dated attestations state
  what actually ran, under the name it had then. Change live instructions; leave attestations
  alone, even when they point at something since deleted.
- **Abstract from the SECOND instance.** One occurrence gets the direct fix. If you cannot
  name the second caller, it is too early.

## Releasing (maintainers)

`./release.sh <version>` does all of it and refuses rather than half-shipping. See its
`--help`. In short: the suite must be green, docs regenerated, `SAVE-LOG.md` must carry a
line for the version, then it merges `develop` into `master`, tags, pushes both, and cuts a
GitHub release. A version bump that never reaches the remote is indistinguishable from no
work at all, so the script verifies delivery at the end and tells you whose move it is.
