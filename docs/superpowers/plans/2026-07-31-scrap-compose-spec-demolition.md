# Scrap `compose.py` — SPEC Demolition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the unproven slot-model composer from ABU and stop the SPEC asserting an architecture the repo contradicts, without yet authoring the replacement.

**Architecture:** Demolition only. Delete the `compose` cluster; rewrite SPEC §4.8, §4.9 and §4.10 down to honest stubs that record what was retired and why; mark §14's Managed Agents claim aspirational. The positive four-leg model (golden works + a PROMPT for the console + incremental evals + an END eval) is deliberately NOT written as normative here. It waits until the second composer is built and Gary is happy with it.

**Tech Stack:** Markdown, Python (deletions only), bash.

## Global Constraints

- **Repo:** `~/Documents/github-repos/agentic-brand-universe` (plugin `0.65.0`, `SPEC_VERSION = "0.16"`). This is the canonical checkout, and the one `gary-sheng-art-universe/assert.sh` points at. There is a second, stale checkout at `~/.claude/plugins/marketplaces/agentic-brand-universe` (plugin `0.57.0`) — **do not edit it**; Task 5 addresses it.
- **Do NOT touch `skills/compose-spread/`.** Its `assemble_prompt.py` (949 lines) is the proven compiler carrying every SPEC §4.6 normative guard. Deleting `compose` is what makes it unambiguously the only one.
- **Do NOT touch `skills/compose-spec/` or `skills/judge-slot/`.** Verified independent.
- **`skills/lint-universe/` IS coupled and IS in scope** (corrected 2026-07-31, mid-execution). An earlier version of this plan called it "verified independent" on the strength of grepping its `SKILL.md` for `compose.py|work.json|form.json`. That was the wrong file and the wrong string: the coupling lives in `scripts/lint.py` and is to the **slot schema**, not to `compose.py` by name. `lint.py:45-46` holds the `EMITTERS` table and `lint.py:584-719` is a 136-line section that lints the retired model (`slots`, `type: deterministic`, `emitter`, `generators`, `for=`). Task 2 removes it. Gary ruled "finish the job" when the gate caught this.
- **`skills/explanatory-plate/` SURVIVES and must not be deleted.** It is standalone-runnable (`plate.py` has its own `__main__` taking a spec path), it has no `SKILL.md` because it is a library rather than a skill, and `docs/ARCHITECTURE.md:5` states every diagram in that document was emitted by it. It loses only its `EMITTERS` registration, which it does not need.
- **Never rewrite `SAVE-LOG.md` history.** It is append-only. Add an entry; do not edit prior ones.
- **`run-tests.sh` discovers test files**, so deleting `skills/compose/tests/` drops its 91 tests automatically. Expect the total to fall by 91 and everything else to stay green.
- **Blast radius is the whole cluster, not one file.** `add-work` and `add-form` author `work.json` and `form.json` documents, and `compose.py` is the only thing that ever consumed them. Deleting the executor alone would leave two skills that produce artifacts nothing can run, which is worse than either keeping or removing both. The cluster is therefore: `skills/compose/`, `skills/add-form/`, `skills/add-work/`, `skills/brand-card/`, `forms/scrolling-diorama/`.

---

## File Structure

| Path | Action |
|---|---|
| `skills/compose/` | Delete. 896-line `compose.py`, 91 tests, 84-line SKILL.md, zero works. |
| `skills/add-form/` | Delete. Authors `form.json` for an executor that no longer exists. |
| `skills/add-work/` | Delete. Authors `work.json` for the same. |
| `skills/brand-card/` | Delete **in Task 2**, with the lint reference that points at it. |
| `skills/lint-universe/scripts/lint.py` | Task 2: drop the `EMITTERS` table (45-46) and the form section (584-719). |
| `skills/lint-universe/tests/test_lint.py` | Task 2: drop the tests covering the removed checks. |
| `skills/explanatory-plate/` | **KEEP.** Standalone-runnable; emitted every diagram in `docs/ARCHITECTURE.md`. |
| `forms/scrolling-diorama/` | Delete. The one form, never worked. |
| `SPEC.md` §4.8, §4.9, §4.10 | Rewrite to demolition stubs. |
| `SPEC.md` §14 | Mark aspirational. |
| `engine/agenticstory/__init__.py` | `SPEC_VERSION` 0.16 → 0.17. |
| `.claude-plugin/plugin.json` | version 0.65.0 → 0.66.0. |
| `SAVE-LOG.md` | Append one entry. |

---

### Task 1: Delete the compose cluster

**Files:**
- Delete: `skills/compose/`, `skills/add-form/`, `skills/add-work/`, `forms/scrolling-diorama/` (NOT `brand-card` — that is Task 2)

**Interfaces:**
- Consumes: nothing.
- Produces: a repo where `assemble_prompt.py` is the only prompt compiler.

- [ ] **Step 1: Confirm the baseline test count**

Run: `./run-tests.sh 2>&1 | tail -2`

BASELINE is already measured: **655 tests, ALL GREEN**. The runner prints `16 skill test file(s) discovered, 655 tests total` then `ALL GREEN` — it does NOT print `ALL GREEN — <N> tests`. Confirm you see 655 and green. If not, stop and report.

- [ ] **Step 2: Confirm the only inbound references are the two already known**

Run:

```bash
grep -rn "import compose\|from compose\|skills/compose/scripts\|brand_card\|brand-card/scripts" \
  --include="*.py" --include="*.sh" engine/ skills/ forms/ registry/ 2>/dev/null \
  | grep -v "compose-spread\|compose-spec"
```

**Expected: exactly two lines**, both known and both handled:

1. `skills/compose/scripts/compose.py:258` — a self-reference inside the cluster being deleted. Goes away with it.
2. `skills/lint-universe/scripts/lint.py:45` — the `EMITTERS["brand-card"]` entry. **Task 2 removes it.** Leave it alone in this task.

Any THIRD line is an unknown importer: stop and report rather than deleting. (An earlier run of this task expected zero lines and correctly refused to proceed when it found these two. They are now expected.)

- [ ] **Step 3: Delete the cluster**

```bash
git rm -r --quiet skills/compose skills/add-form skills/add-work forms/scrolling-diorama
git status --short | head -20
```

**`skills/brand-card/` is deliberately NOT deleted here.** `lint.py` still points at `brand-card/scripts/card.py`, so removing it now would leave the repo in a state where a live, protected file references a deleted script, and lint's own tests would go red through no fault of this task. Task 2 deletes `brand-card` and removes that reference in the same commit.

- [ ] **Step 4: Prove the suite is still green and dropped exactly 91 tests**

Run: `./run-tests.sh 2>&1 | tail -3`

The runner prints two lines, e.g. `16 skill test file(s) discovered, 655 tests total` then `ALL GREEN`. Expected here: **564 tests total** (655 minus compose's 91) and `ALL GREEN`. Any other number, or any failure, means the deletion touched something it should not have: restore with `git checkout -- .` and report rather than continuing.

- [ ] **Step 5: Prove exactly one prompt compiler remains**

```bash
grep -rln "def compile_slot\|def assemble\|def build(" --include="*.py" skills/ | sort
```

Expected: only `skills/compose-spread/scripts/assemble_prompt.py`.

- [ ] **Step 6: Commit**

```bash
git commit -m "Scrap the slot-model composer core: 896 lines, 91 tests, zero works

compose.py was the most-tested unrun code in the repo. No work.json ever
existed, no work/ or recipes/ directory was ever written, and forms/ held one
form nobody worked. It also grew its own 30-line compile_slot rather than
calling compose-spread/assemble_prompt.py, which is the exact fork failure this
framework already diagnosed and fixed once when it retired the Nation of Fire
compiler, and which compose-spread's own SKILL.md forbids in a section titled
'never fork this'.

add-form and add-work go with it. They author documents that only compose.py
consumed, so keeping them would leave skills producing artifacts nothing can run.

brand-card is deleted in Task 2 instead, together with the lint-universe
reference that points at it.

assemble_prompt.py is untouched and is now unambiguously the only compiler."
```

---

### Task 2: Delete `brand-card` and retire lint-universe's form/slot checks

**Files:**
- Delete: `skills/brand-card/`
- Modify: `skills/lint-universe/scripts/lint.py`
- Modify: `skills/lint-universe/tests/test_lint.py`

**Interfaces:**
- Consumes: Task 1's deletions.
- Produces: a linter that no longer checks a retired model, and no dangling emitter reference.

`lint-universe` lints the slot model Task 1 just removed the executor for. This task removes that section. It is a live, proven skill with 69 tests, so the surgery is bounded precisely and the remaining tests must stay green.

**`skills/explanatory-plate/` MUST SURVIVE.** It is the second entry in the `EMITTERS` table, but unlike `brand-card` it is standalone-runnable and `docs/ARCHITECTURE.md:5` says every diagram in that document was emitted by it. Remove its registration, keep the skill.

- [ ] **Step 1: Record the pre-surgery state**

```bash
./run-tests.sh 2>&1 | tail -2
grep -c "def test" skills/lint-universe/tests/test_lint.py
```

Expected: `564 tests total`, `ALL GREEN`, and `69` lint tests.

- [ ] **Step 2: Read the section you are removing, all of it**

Read `skills/lint-universe/scripts/lint.py` lines 580 to 729. The form section opens at line 584 with `# ---- projections` and runs to line 719; `def main()` begins at 720. Line 613 carries a standing instruction that any non-form rule belongs ABOVE that line, which is your guarantee that the section is self-contained.

**Verify that guarantee rather than trusting it.** Before deleting, confirm nothing below line 584 defines or mutates a name used above it. If anything does, report instead of deleting.

- [ ] **Step 3: Remove the `EMITTERS` table**

Delete lines 45-46 of `skills/lint-universe/scripts/lint.py`:

```python
    EMITTERS = {"brand-card": SKILLS/"brand-card/scripts/card.py",
                "explanatory-plate": SKILLS/"explanatory-plate/scripts/plate.py"}
```

Also remove the now-unused `SKILLS = pathlib.Path(__file__).resolve().parents[2]` on line 44 **only if nothing else in the file uses `SKILLS`**. Grep first; if it has another use, leave it.

- [ ] **Step 4: Remove the form/projection section**

Delete `lint.py` lines 584 through 719 inclusive (from `# ---- projections` up to but NOT including `def main()`).

- [ ] **Step 5: Delete `brand-card`**

```bash
git rm -r --quiet skills/brand-card
```

- [ ] **Step 6: Remove the tests that covered the deleted checks**

In `skills/lint-universe/tests/test_lint.py`, delete every test whose subject is a removed check. Candidates identified by grep: `TestFormsLayout` (3 tests, entirely form-layout), and the subset of `TestLinter` (22 tests) asserting `SLOT-NO-EMITTER`, `EMITTER-UNKNOWN`, `EMITTER-MISSING`, `SLOT-NO-GENERATOR` or `NO-FORMS`.

**Determine the exact set by reading, not by grep count.** `TestLinter` also covers checks that survive; delete only the tests whose assertions name a removed error code, and keep the rest. `TestGoldenProvenance` and `TestSpecPin` each matched the grep on a single incidental line and are almost certainly NOT form tests: read them and keep them unless their subject really is the removed model.

Report the exact list of deleted test names and the count.

- [ ] **Step 7: Prove the remaining suite is green**

```bash
./run-tests.sh 2>&1 | tail -2
grep -c "def test" skills/lint-universe/tests/test_lint.py
```

Expected: `ALL GREEN`, a total of `564 minus <the number of lint tests you deleted>`, and a lint test count of `69 minus <same>`. The two must agree. If the suite is red, the section was not self-contained: report what broke rather than patching around it.

- [ ] **Step 8: Prove explanatory-plate still works**

```bash
ls skills/explanatory-plate/scripts/plate.py && echo "SURVIVES"
python3 -m unittest discover -s skills/explanatory-plate/tests -v 2>&1 | tail -3
```

Expected: `SURVIVES` and its tests green.

- [ ] **Step 9: Commit**

```bash
git add -A skills/lint-universe skills/brand-card
git commit -m "Retire lint-universe's form/slot checks, and brand-card with them

lint-universe was called independent of the retired model on the strength of
grepping its SKILL.md. The coupling was in scripts/lint.py all along, and it was
to the slot schema rather than to compose.py by name: a 136-line section linting
slots, deterministic emitters and generators, plus an EMITTERS table pointing at
brand-card. A linter for a model with no executor is a gate on nothing.

explanatory-plate survives. It was the table's other entry, but it is
standalone-runnable and every diagram in docs/ARCHITECTURE.md came out of it.
It loses a registration it never needed."
```

---

### Task 3: Rewrite SPEC §4.8, §4.9 and §4.10

**Files:**
- Modify: `SPEC.md` (§4.8 at line ~611 through the end of §4.10 at ~999, i.e. everything up to `## 5. Evolution & versioning`)

**Interfaces:**
- Consumes: nothing.
- Produces: three stub sections that record the retirement. Later work replaces them with the four-leg model.

The concept of a **form** survives. What is retired is one specific encoding of it: `surface` / `requires` / `slots` / `generators` / `invariants` / `emits`, plus a single universal composer that executes them.

- [ ] **Step 1: Replace §4.8's opening and body**

Find the line `### 4.8 Form (what makes a work the KIND of thing it is)` and replace everything from it up to (not including) `### 4.9 Work (canon given form)` with:

```markdown
### 4.8 Form (RETIRED ENCODING, v0.17)

**Canon is the matter. A form is what shapes it. A work (§4.9) is canon given form.** That much
holds and is not in question.

**What is retired is the ENCODING, not the concept.** From v0.6 to v0.16 this section specified a
form as `surface` / `requires` / `slots` / `generators` / `invariants` / `emits`, executed by a
single universal composer (§4.10). That model was authored from one imagined example and never ran:
across the whole framework's life it produced **zero works**. No `work.json` was ever written, no
`work/` or `recipes/` directory ever existed, and the one form in the registry
(`scrolling-diorama`) was never worked. It shipped 91 unit tests and nothing made.

Meanwhile the pipeline that has produced more than a hundred illustrated books
(`make-a-book` → `render-book` → `compose-spread`) was never described by this section at all, and
was not even called a composer. The naming had the authority backwards: the proven thing was
unnamed and the unnamed thing was proven.

**The diagnosis, stated plainly so it is not repeated.** A slot schema caps a work at the
imagination of whoever authored the form, frozen at the worst possible moment. The failure was not
in the details of the encoding; it was in specifying a SHAPE where the standard should specify a
STANDARD.

**The replacement is deliberately not written here yet.** A second composer is being built for real
(`garysheng-art-series`, in the `gary-sheng-art` universe). When it is finished and judged good,
the shared surface between it and the book composer becomes this section. Writing the replacement
now, from one instance, is precisely the mistake that produced the retired model. Abstract from the
second instance, not the first.

Until then, a form is whatever a proven composer needs it to be, and no universe is asked to
conform to a schema this section cannot yet justify.
```

- [ ] **Step 2: Replace §4.9**

Replace everything from `### 4.9 Work (canon given form)` up to (not including) `### 4.10 The Composer, the Compiler, and the Gate` with:

```markdown
### 4.9 Work (RETIRED ENCODING, v0.17)

A **work** is one instance of a form, and that idea survives. Retired with §4.8 is its encoding: a
`work.json` binding ids to a form's required kinds and filling its declared slots.

Nothing was lost by deleting it, because nothing was ever expressed in it.

**One consequence worth stating.** The v0.6 changelog claimed the narrative fields (`logline`,
`spine`, `refrain`, `beats`) had moved out of `Story Spec` "into the storybook form's slot schema,
where they always belonged," with `Story Spec` retained only as a back-compat alias. That migration
was recorded as done and never happened: no storybook form was ever authored, so `Story Spec`
remained the live primitive that every book actually uses. It is not an alias and never became one.
Treat §4.3 as canonical for stories.
```

- [ ] **Step 3: Replace §4.10**

Replace everything from `### 4.10 The Composer, the Compiler, and the Gate` up to (not including) `## 5. Evolution & versioning` with:

```markdown
### 4.10 The Composer, the Compiler, and the Gate (v0.17)

The three-part split still holds and is the most durable thing this section ever said:

| Part | Nature | Answers |
|---|---|---|
| **Composer** | agentic, generative | *What should exist?* |
| **Compiler** | deterministic | *What exact prompt does this one slot become?* |
| **Gate** | verifying | *Is what came back actually right?* |

**What changed in v0.17 is the article.** This section said "THE Composer", singular, and a
universal executor was built to be it. The correction: **a composer is per-form.** Each kind of work
plans differently, and a storybook, a diptych series and a deck have genuinely different plans. What
they share is not the plan; it is everything underneath it.

**The compiler is shared and there is exactly one.** It is
`skills/compose-spread/scripts/assemble_prompt.py`, which carries every §4.6 normative guard
(uncast-character refusal, anchor-style guard, single-image guard, `registerAnchor` auto, altLooks,
dropSheets, auto-disambiguation, `guardedNegatives`). The retired composer forked it rather than
calling it, and the fork's 30-line `compile_slot` had none of those guards. That is the second time
this framework has grown two disjoint compilers, and the first time cost real books. There is one
compiler. Do not write a second.

**The gate is a role, not a service** (see `judge-slot`), and it fails closed: a slot whose judged
invariants could not be checked is UNJUDGED, never PASS.

**What belongs under a composer rather than inside one** is still being drawn, and is the open
question this section will answer once two composers exist to compare. The candidates, all of which
the retired executor implemented and none of which are form-specific: durable per-slot state,
resumability, recipes and drift-checking, provider adapters, and plan-time feasibility refusal
(which is not form machinery at all, but simply the first incremental eval).
```

- [ ] **Step 4: Verify no dangling cross-references to the retired schema**

```bash
grep -n "emits\"\|\"slots\"\|producibleAspects\|maxRolls" SPEC.md | head -20
```

Expected: any remaining hits are inside §4.10's prose or historical changelog blocks, not presented as a live contract. Fix any that read as normative.

- [ ] **Step 5: Commit**

```bash
git add SPEC.md
git commit -m "SPEC v0.17: retire the form/work slot encoding and the singular composer

The concept of a form survives; the encoding does not. Records the diagnosis
(a slot schema specifies a shape where the standard should specify a standard),
corrects 'THE Composer' to a per-form composer over one shared compiler, and
notes that the v0.6 claim about narrative fields moving into the storybook
form's slot schema never actually happened, so Story Spec is still live.

The replacement model is deliberately not written yet. It waits on a second
proven composer, because authoring it from one instance is what produced the
model being retired."
```

---

### Task 4: Mark §14 aspirational, bump versions, log

**Files:**
- Modify: `SPEC.md` §14 (line ~1246)
- Modify: `engine/agenticstory/__init__.py` (`SPEC_VERSION`)
- Modify: `.claude-plugin/plugin.json` (`version`)
- Modify: `SAVE-LOG.md` (append)

**Interfaces:**
- Consumes: Tasks 1, 2 and 3.
- Produces: a shippable, honestly-versioned repo.

- [ ] **Step 1: Mark §14 aspirational**

Find `## 14. Why this runtime is Managed Agents (v0.6)` and insert immediately after its heading, before the existing paragraph:

```markdown
> **STATUS, v0.17: ASPIRATIONAL, NOT DESCRIPTIVE.** Nothing in this framework runs on Managed
> Agents. The composer this section argues for was deleted in v0.17 having never run, and the
> pipeline that does the work (`make-a-book`) runs locally. The argument below about the SHAPE of
> the workload is still believed to be correct, and hosted execution remains the intended
> direction. It is recorded here as a claim about where this is going, not a description of how it
> works today. A reader deciding what to build on should treat local execution as the only reality.
>
> The one real body of Managed Agents work lives outside this repo, in `garysheng-books/scripts/`
> (`ma_session.py`, `ma_render_helper.py`, `render-narration-on-ma.py`), and is book-shaped rather
> than framework-shaped. Bringing it in is a live option, not a done thing.
```

- [ ] **Step 2: Bump `SPEC_VERSION`**

In `engine/agenticstory/__init__.py`, change `SPEC_VERSION = "0.16"` to `SPEC_VERSION = "0.17"`.

- [ ] **Step 3: Bump the plugin version**

In `.claude-plugin/plugin.json`, change `"version": "0.65.0"` to `"version": "0.66.0"`.

- [ ] **Step 4: Confirm no universe is broken by the spec bump**

```bash
for u in ~/Documents/github-repos/*/universe.json ~/Documents/github-repos/*/*/universe.json; do
  [ -e "$u" ] || continue
  python3 -c "import json,sys; d=json.load(open('$u')); print(f\"{d.get('name','?'):<24} conformsTo {d.get('spec',{}).get('version','?')}\")"
done
```

Expected: universes pin 0.13 and similar older versions. That is correct and expected — this bump does not require any universe to migrate, because it only removes a schema none of them used. Record the output in the SAVE-LOG entry.

- [ ] **Step 5: Run the suite one more time**

Run: `./run-tests.sh 2>&1 | tail -3`
Expected: `ALL GREEN — <BASELINE minus 91> tests`

- [ ] **Step 6: Append the SAVE-LOG entry**

Append to `SAVE-LOG.md` (never edit an existing entry):

```markdown
## 2026-07-31 — scrapped the slot-model composer (SPEC v0.17, plugin 0.66.0)

Deleted `skills/compose/` (896 lines, 91 tests, ZERO works), and with it `add-form`, `add-work`,
`brand-card` and `forms/scrolling-diorama`, which authored or emitted documents only it consumed.
No `work.json` ever existed in the framework's life; no `work/` or `recipes/` directory was ever
written. It was the most-tested unrun code in the repo, and it had grown its own 30-line
`compile_slot` instead of calling `compose-spread/assemble_prompt.py` — the same disjoint-compiler
failure this framework diagnosed and fixed when it retired the Nation of Fire fork, and which
`compose-spread`'s SKILL.md forbids in a section titled "never fork this". There is now exactly one
compiler.

SPEC §4.8 and §4.9 retire the ENCODING and keep the concept; §4.10 corrects "THE Composer" to a
per-form composer over one shared compiler; §14 is marked ASPIRATIONAL, because nothing here runs
on Managed Agents and the section read as description.

Also found and recorded: the v0.6 changelog claimed the narrative fields had moved into "the
storybook form's slot schema, where they always belonged," with `Story Spec` kept as a back-compat
alias. No storybook form was ever authored, so that migration never happened and `Story Spec` is
still the live primitive every book uses.

DELIBERATELY NOT DONE: the replacement model (golden works + a PROMPT for the console + incremental
evals + an END eval) is NOT written as normative. It waits on the second composer,
`garysheng-art-series`, being built now in `gary-sheng-art-universe`. Authoring it from one instance
is exactly what produced the model just deleted.

Also noted, not fixed: a second checkout at `~/.claude/plugins/marketplaces/agentic-brand-universe`
is 8 plugin versions behind (0.57.0) and still present, despite commit 2b8d06a recording "One
source: retire the private marketplace copy and the sync script". An agent read a stale SPEC from it
for a full session without noticing.
```

- [ ] **Step 7: Commit and push**

```bash
git add SPEC.md engine/agenticstory/__init__.py .claude-plugin/plugin.json SAVE-LOG.md
git commit -m "SPEC v0.17, plugin 0.66.0: section 14 marked aspirational, save-log entry

Nothing in this framework runs on Managed Agents. Section 14 argued for a
runtime as though describing one, so it is now labelled a claim about direction
rather than a description of the system."
git push
```

---

### Task 5: Resolve the stale second checkout

**Files:**
- No repo files. This is an environment fix.

**Interfaces:**
- Consumes: Task 4's commit.
- Produces: one source of truth, or a recorded reason there are two.

- [ ] **Step 1: Determine whether anything still points at the stale copy**

```bash
grep -rn "plugins/marketplaces/agentic-brand-universe" ~/.claude/*.json ~/.claude/plugins/*.json \
  ~/.agents/AGENTS.md 2>/dev/null | head
cat ~/.claude/plugins/known_marketplaces.json 2>/dev/null | python3 -m json.tool | head -30
```

- [ ] **Step 2: Report before acting**

Do NOT delete the stale checkout unilaterally. Marketplace directories are managed by the plugin system, and removing one by hand can break plugin resolution. Report to Gary:
- whether `known_marketplaces.json` registers it,
- whether its HEAD (`3bfd60b`) is an ancestor of the canonical HEAD (`git -C <stale> merge-base --is-ancestor HEAD <canonical-HEAD>`),
- whether it holds any commit the canonical repo lacks (`git log canonical..stale --oneline`).

If it holds unique commits, that is divergence to reconcile, not a stale mirror to drop.

- [ ] **Step 3: Refresh via the supported path**

If it registers as a marketplace and holds nothing unique, refresh it the supported way rather than by hand:

```
/plugin marketplace update agentic-brand-universe
```

Then confirm: `grep '"version"' ~/.claude/plugins/marketplaces/agentic-brand-universe/.claude-plugin/plugin.json`
Expected: `0.66.0`.

---

## Self-Review

**Spec coverage.** "Delete `skills/compose/`" → Task 1, extended to the coupled cluster with the reasoning recorded in Global Constraints. "Retire the slot/generator/feasibility machinery in §4.8/§4.10" → Task 2 steps 1–3, including §4.9 which the brief omitted but which encodes the same retired model and would have been left dangling. "Mark §14 aspirational" → Task 3 step 1. "Do NOT author the positive replacement" → honored throughout; §4.8's stub says so explicitly and the SAVE-LOG records it as deliberate. Version bump and log → Task 3. The stale checkout → Task 4, added because it caused a real error this session.

**Placeholder scan.** No TBD or TODO. Every edit gives exact replacement text. Every command is runnable and states its expected output. BASELINE is captured in Task 1 step 1 rather than guessed, because the count depends on the canonical repo's current suite.

**Type consistency.** No code interfaces are created; the only cross-task dependency is BASELINE (Task 1 step 1 → Task 1 step 4 → Task 3 step 5), used identically in all three. Version strings are consistent: `SPEC_VERSION` 0.16 → 0.17, plugin 0.65.0 → 0.66.0, and both appear with those exact values in the SAVE-LOG entry and Task 4's verification.
