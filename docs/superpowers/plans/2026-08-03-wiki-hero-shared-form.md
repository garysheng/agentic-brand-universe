# Shared Forms and the Wiki Article Hero Form (Unit B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a form usable from ANY universe, then declare `wiki-article-hero` as the first one, so a wiki hero is a work an ABU can make rather than a script each wiki re-hand-rolls.

**Architecture:** `forms.py` currently resolves only `<universe>/forms/`. It gains a second root at `<abu-repo>/forms/` whose entries are visible to every universe, with local forms shadowing shared ones by id. The new `forms/wiki-article-hero/` folder then supplies the method, and its `evals/panels.py` reuses the panel-counting logic proven in Unit A.

**Tech Stack:** python3, `unittest` (no pytest in this repo), Pillow, the existing `abu` engine and `on-brand-image` generator.

**Source spec:** `docs/superpowers/specs/2026-08-03-wiki-article-hero-design.md`

**Repo under change:** `~/Documents/github-repos/agentic-brand-universe`

**Prerequisite:** Unit A is complete and has produced at least two real wiki heroes. Task 4 below writes `FORM.md`, which must state honestly how many works the form rests on, and that number has to be greater than zero. The retired composer had 896 lines, 91 tests and zero works, and that is the failure this must not repeat.

## Global Constraints

- **No em dashes** in any prose, code comment, doc, or commit message you WRITE. One appears in this plan inside a reproduction of an existing `forms.py` print string ("NOT USABLE — missing"). Preserve it verbatim; rewriting an unrelated user-facing string is not part of this change.
- **Tests are `unittest`, run as plain scripts**, discovered by `run-tests.sh` via the glob `skills/*/tests/test*.py`. A test file placed anywhere else runs nowhere.
- **`run-tests.sh` must stay green**, and it parses `Ran N test` from each suite. A suite producing no parseable count is a failure, not a zero.
- **Prove every new test bites.** Revert the behavior, confirm the test fails, restore. Assert the mutation actually applied; a string-replacement patch that silently does not match reports SURVIVED when nothing was mutated.
- **Never rewrite a historical record.** `.recipe.json` files and dated canon attestations state what actually ran.
- **`local` shadows `shared` by id, entirely.** Never merge the two definitions of one form.
- **A form needs both `FORM.md` and `PROMPT.md`.** A folder with only one is not usable and must refuse rather than improvise.
- **Commits use Gary's real git identity.** No `Co-Authored-By: Claude`, no "Generated with Claude Code".
- **Do not push.** Commit locally; pushing waits for an explicit go.

## File Structure

| File | Responsibility |
|---|---|
| `skills/make-a-work/scripts/forms.py` | MODIFY. `survey()` merges a shared root with the universe root; records gain `source`. |
| `skills/make-a-work/tests/test_forms.py` | MODIFY. Add shared-root, shadowing, and labeling tests to the existing suite. |
| `forms/wiki-article-hero/FORM.md` | CREATE. What it is, its goldens, an honest STATUS section. |
| `forms/wiki-article-hero/PROMPT.md` | CREATE. The method. This IS the composer. |
| `forms/wiki-article-hero/evals/panels.py` | CREATE. Asserts the render is a strip, not a plate. |
| `skills/make-a-work/SKILL.md` | MODIFY. Document the shared root and the shadowing rule. |
| `CLAUDE.md` | MODIFY. Add the eval script to the job-indexed table. |

---

### Task 1: Shared forms root

**Files:**
- Modify: `skills/make-a-work/scripts/forms.py:48-69` (`survey`), `:70-86` (`cmd_list`), `:87-102` (`cmd_resolve`)
- Test: `skills/make-a-work/tests/test_forms.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `survey(root, shared_root=None) -> list[dict]`, each record gaining `"source": "shared" | "local"`.
  - `shared_forms_root() -> pathlib.Path`, resolving `<abu-repo>/forms`.
  - `cmd_list` printing the source label; `cmd_resolve` emitting `source` in its JSON.

- [ ] **Step 1: Write the failing tests**

Append to `skills/make-a-work/tests/test_forms.py`, above the `if __name__` block. The existing `universe()` and `form()` helpers are reused; `form()` takes a directory whose `forms/` subdir it writes into, so a shared root is built by pointing it at a plain directory.

```python
def shared_root(root, name="shared"):
    d = pathlib.Path(root) / name
    (d / "forms").mkdir(parents=True, exist_ok=True)
    return d


class TestSharedForms(unittest.TestCase):
    """A form that only one universe can see is not a framework capability.

    Exactly one universe on the machine declared any forms at all, and the
    cartridge powering five wiki heroes declared none, so 'make a wiki hero'
    could not be a form until forms could be shared."""

    def test_shared_form_is_visible_from_a_universe_with_no_forms(self):
        with tempfile.TemporaryDirectory() as t:
            u = universe(t)
            s = shared_root(t); form(s, "wiki-article-hero")
            got = forms.survey(u, shared_root=s / "forms")
            self.assertEqual([f["id"] for f in got], ["wiki-article-hero"])
            self.assertEqual(got[0]["source"], "shared")
            self.assertTrue(got[0]["usable"])

    def test_local_form_is_labeled_local(self):
        with tempfile.TemporaryDirectory() as t:
            u = universe(t); form(u, "event-flyer")
            s = shared_root(t)
            got = forms.survey(u, shared_root=s / "forms")
            self.assertEqual(got[0]["source"], "local")

    def test_local_shadows_shared_entirely(self):
        """Shadowing replaces, never merges. Two methods for one id is how a
        form silently becomes whatever the last agent felt like."""
        with tempfile.TemporaryDirectory() as t:
            u = universe(t); form(u, "wiki-article-hero")
            s = shared_root(t); form(s, "wiki-article-hero", evals=("panels.py",))
            got = forms.survey(u, shared_root=s / "forms")
            self.assertEqual(len(got), 1)
            self.assertEqual(got[0]["source"], "local")
            self.assertEqual(got[0]["evals"], [])   # the shared evals did NOT leak in
            self.assertTrue(got[0]["dir"].startswith(str(u)))

    def test_both_roots_merge_and_sort(self):
        with tempfile.TemporaryDirectory() as t:
            u = universe(t); form(u, "zeta")
            s = shared_root(t); form(s, "alpha")
            got = forms.survey(u, shared_root=s / "forms")
            self.assertEqual([f["id"] for f in got], ["alpha", "zeta"])

    def test_an_unusable_shared_form_still_refuses(self):
        """Sharing must not become a back door around the usability gate."""
        with tempfile.TemporaryDirectory() as t:
            u = universe(t)
            s = shared_root(t); form(s, "broken", prompt_md=False)
            got = forms.survey(u, shared_root=s / "forms")
            self.assertFalse(got[0]["usable"])
            self.assertEqual(got[0]["missing"], ["PROMPT.md"])

    def test_missing_shared_root_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as t:
            u = universe(t); form(u, "only-local")
            got = forms.survey(u, shared_root=pathlib.Path(t) / "nope" / "forms")
            self.assertEqual([f["id"] for f in got], ["only-local"])

    def test_shared_root_resolves_to_the_repo(self):
        p = forms.shared_forms_root()
        self.assertEqual(p.name, "forms")
        self.assertTrue((p.parent / "SPEC.md").exists(),
                        f"shared_forms_root resolved outside the repo: {p}")

    def test_list_labels_the_source(self):
        with tempfile.TemporaryDirectory() as t:
            u = universe(t)
            s = shared_root(t); form(s, "wiki-article-hero")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                forms.cmd_list(argparse.Namespace(universe=str(u), shared=str(s / "forms")))
            self.assertIn("shared", buf.getvalue())
            self.assertIn("wiki-article-hero", buf.getvalue())
```

Add `argparse` to the module's import line at the top of the file:

```python
import argparse, importlib.util, io, contextlib, json, pathlib, sys, tempfile, unittest
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd ~/Documents/github-repos/agentic-brand-universe/skills/make-a-work
python3 tests/test_forms.py
```

Expected: FAIL. `TypeError: survey() got an unexpected keyword argument 'shared_root'` and `AttributeError: module 'forms' has no attribute 'shared_forms_root'`.

- [ ] **Step 3: Implement the shared root**

In `skills/make-a-work/scripts/forms.py`, replace `survey` with the version below and add `shared_forms_root` above it:

```python
def shared_forms_root():
    """The framework-level forms root, visible from every universe.

    A form was per-universe only until 2026-08-03, which meant a kind of work
    shared across universes (a wiki article hero is the same artifact in every
    one) had to be re-declared, or re-hand-rolled as a script, per universe.
    """
    # scripts/ -> make-a-work/ -> skills/ -> <repo root>
    return pathlib.Path(__file__).resolve().parents[3] / "forms"


def _scan(fdir, source):
    out = []
    if not fdir.is_dir():
        return out
    for d in sorted(p for p in fdir.iterdir() if p.is_dir()):
        form_md, prompt_md = d / "FORM.md", d / "PROMPT.md"
        missing = [n for n, p in (("FORM.md", form_md), ("PROMPT.md", prompt_md))
                   if not p.exists()]
        out.append({
            "id": d.name,
            "dir": str(d),
            "source": source,
            "usable": not missing,
            "missing": missing,
            "evals": sorted(x.name for x in (d / "evals").glob("*.py")) if (d / "evals").is_dir() else [],
            "retiredEncodingOnly": bool(missing) and (d / "form.json").exists(),
            "status": _status_line(form_md) if form_md.exists() else None,
        })
    return out


def survey(root, shared_root=None):
    """Shared forms, then local ones. LOCAL SHADOWS SHARED BY ID, entirely.

    Shadowing replaces rather than merges: a universe that declares its own
    wiki-article-hero gets exactly its own method, never a blend of two. A blend
    is how a form silently becomes whatever the last agent felt like.
    """
    if shared_root is None:
        shared_root = shared_forms_root()
    merged = {f["id"]: f for f in _scan(pathlib.Path(shared_root), "shared")}
    for f in _scan(pathlib.Path(root) / "forms", "local"):
        merged[f["id"]] = f
    return [merged[k] for k in sorted(merged)]
```

- [ ] **Step 4: Label the source in `list` and `resolve`**

In `cmd_list`, replace the usable-branch print so the source is visible, and thread an optional `--shared` override:

```python
def cmd_list(a):
    shared = getattr(a, "shared", None)
    forms_ = survey(_universe(a.universe), shared_root=shared)
    if not forms_:
        print("no forms declared. A form is a folder at forms/<id>/ holding FORM.md + PROMPT.md.")
        return 0
    for f in forms_:
        tag = f"({f['source']})"
        if f["usable"]:
            print(f"  {f['id']:<24} {tag:<9} usable"
                  + (f"   evals: {', '.join(f['evals'])}" if f["evals"] else ""))
            if f["status"]:
                print(f"  {'':<24} {'':<9} {f['status'][:96]}")
        elif f["retiredEncodingOnly"]:
            print(f"  {f['id']:<24} {tag:<9} RETIRED ENCODING (form.json only, SPEC 4.8 slot model, v0.17)")
        else:
            print(f"  {f['id']:<24} {tag:<9} NOT USABLE — missing {', '.join(f['missing'])}")
    return 0
```

Apply the same `shared = getattr(a, "shared", None)` and `survey(..., shared_root=shared)` change in `cmd_resolve`. Its existing `json.dumps(hit, indent=2)` already emits the new `source` field for free.

Register the flag on both subparsers in `main`:

```python
    p = sub.add_parser("list"); p.add_argument("universe")
    p.add_argument("--shared", help="Override the shared forms root (testing).")
    p.set_defaults(fn=cmd_list)
    p = sub.add_parser("resolve"); p.add_argument("universe"); p.add_argument("form")
    p.add_argument("--shared", help="Override the shared forms root (testing).")
    p.set_defaults(fn=cmd_resolve)
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
cd ~/Documents/github-repos/agentic-brand-universe/skills/make-a-work
python3 tests/test_forms.py
```

Expected: `OK`, with the pre-existing tests still passing.

- [ ] **Step 6: Prove the shadowing test bites**

Change `survey` so local does NOT override shared (swap the merge order), assert the patch applied, re-run, and confirm `test_local_shadows_shared_entirely` FAILS. Then restore.

```bash
python3 - <<'PY'
import pathlib
p = pathlib.Path("scripts/forms.py"); s = p.read_text()
old = 'merged = {f["id"]: f for f in _scan(pathlib.Path(shared_root), "shared")}'
assert old in s, "PATCH DID NOT MATCH"   # without this the no-op is silent
PY
```

- [ ] **Step 7: Prove the real universes still resolve**

```bash
cd ~/Documents/github-repos/agentic-brand-universe
python3 skills/make-a-work/scripts/forms.py list ~/Documents/github-repos/christofuturism-universe
```

Expected: `event-flyer`, `fashion-look` labeled `(local)` and still usable; `scrolling-diorama` still reported as RETIRED ENCODING.

- [ ] **Step 8: Full suite green**

```bash
bash run-tests.sh
```

Expected: no `FAILED`, no `NO TEST COUNT PARSED`, and the `make-a-work` count risen by 8.

- [ ] **Step 9: Commit**

```bash
git add skills/make-a-work/scripts/forms.py skills/make-a-work/tests/test_forms.py
git commit -m "Forms can be shared across universes

survey() read only <universe>/forms/, so a kind of work that is identical in
every universe had to be re-declared per universe or re-hand-rolled as a script.
Adds a framework-level root; local shadows shared by id, entirely, never merged."
```

---

### Task 2: The panel eval

**Files:**
- Create: `forms/wiki-article-hero/evals/panels.py`
- Test: `skills/make-a-work/tests/test_wiki_hero_eval.py`

**Interfaces:**
- Consumes: nothing from Task 1 (evals are standalone scripts a method calls).
- Produces: `python3 forms/wiki-article-hero/evals/panels.py <image> --expect N`, exit 0 on match, 1 on mismatch. Importable as `count_panels(path, *, min_gutter_px=8, flat_max=6.0, light_min=200.0) -> int`.

Same logic as Unit A's `check_panels.py`, deliberately duplicated. ABU must not depend on `wiki-template` and `wiki-template` must not depend on ABU; portability is the point, and the header names the sibling so a fixer knows to fix both.

- [ ] **Step 1: Write the failing test**

Create `skills/make-a-work/tests/test_wiki_hero_eval.py`:

```python
#!/usr/bin/env python3
"""The panel eval is what makes the multipanel law load-bearing.

A layout law with nothing checking it is how a template kept shipping a
single-focal-scene rule for weeks after that rule was reversed."""
import importlib.util, pathlib, tempfile, unittest

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
EVAL = REPO / "forms" / "wiki-article-hero" / "evals" / "panels.py"
_spec = importlib.util.spec_from_file_location("panels", EVAL)
panels = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(panels)

from PIL import Image, ImageDraw

CREAM = (255, 250, 236)


def strip(path, n, w=1536, h=1024, gutter=40):
    img = Image.new("RGB", (w, h), CREAM); d = ImageDraw.Draw(img)
    pw = (w - gutter * (n - 1)) // n
    for i in range(n):
        x0 = i * (pw + gutter)
        d.rectangle([x0, 0, x0 + pw, h], fill=(40, 40, 60))
    img.save(path); return path


def plate(path, w=1536, h=1024):
    img = Image.new("RGB", (w, h), CREAM); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, h], fill=(40, 40, 60))
    img.save(path); return path


class TestPanelEval(unittest.TestCase):
    def test_three_panel_strip(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(panels.count_panels(strip(pathlib.Path(t) / "a.png", 3)), 3)

    def test_four_panel_strip(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(panels.count_panels(strip(pathlib.Path(t) / "b.png", 4)), 4)

    def test_single_plate(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(panels.count_panels(plate(pathlib.Path(t) / "c.png")), 1)

    def test_a_plate_does_not_pass_as_a_strip(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertNotEqual(panels.count_panels(plate(pathlib.Path(t) / "d.png")), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd ~/Documents/github-repos/agentic-brand-universe/skills/make-a-work
python3 tests/test_wiki_hero_eval.py
```

Expected: FAIL, `FileNotFoundError` for the eval.

- [ ] **Step 3: Write the eval**

Create `forms/wiki-article-hero/evals/panels.py` with the same body as Unit A's `illustrations/scripts/check_panels.py` (`_flat_light_columns`, `count_panels`, `main`), and this docstring in place of Unit A's:

```python
"""Count the panels in a rendered wiki hero.

A gutter is a full-height run of columns that is uniformly light. Reduce the image
to one number per column (how much variation it contains), mark the flat-and-light
columns, count the interior runs. Panels = interior runs plus one. Outer margins are
walked past, or a strip drawn with breathing room reports N+2 panels forever.

SIBLING: wiki-template/illustrations/scripts/check_panels.py is the same logic,
deliberately duplicated. ABU must not depend on wiki-template and wiki-template must
not depend on ABU. Fixing a bug here means fixing it there.
"""
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
python3 tests/test_wiki_hero_eval.py
```

Expected: `Ran 4 tests` / `OK`.

- [ ] **Step 5: Prove it bites**

Make `count_panels` always `return 3`, re-run, confirm `test_single_plate` and `test_a_plate_does_not_pass_as_a_strip` FAIL, then revert.

- [ ] **Step 6: Commit**

```bash
cd ~/Documents/github-repos/agentic-brand-universe
git add forms/wiki-article-hero/evals/panels.py skills/make-a-work/tests/test_wiki_hero_eval.py
git commit -m "Add the wiki-hero panel eval

Makes the multipanel law checkable rather than aspirational."
```

---

### Task 3: The method

**Files:**
- Create: `forms/wiki-article-hero/PROMPT.md`

**Interfaces:**
- Consumes: `evals/panels.py` from Task 2; `on-brand-image/scripts/generate.py`, `render-readback/scripts/verify_render.py`, and `canon-resolve` from the existing framework.
- Produces: the composer `make-a-work` reads and follows exactly.

- [ ] **Step 1: Write the method**

Create `forms/wiki-article-hero/PROMPT.md`:

````markdown
# Method: wiki article hero

You are making ONE hero image for ONE wiki article. Follow this in order. Where a
step names an eval, run it at that point, not at the end.

## 0. Inputs you must have before starting

| | |
|---|---|
| `--universe` | the universe supplying the register and cast |
| `--wiki` | absolute path to the wiki repo |
| `--slug` | the page slug, no extension |
| `--scene` | the argument, written AS BEATS |
| `--panels` | default 3 |

If `--scene` arrived as one paragraph rather than beats, STOP and rewrite it as
beats with the requester. A scene handed over as one paragraph renders as one plate
whatever the layout instruction says. This is the single most common failure.

Read the wiki's `wiki.config.json`. If `hero_register.mode` is `local`, this form is
the wrong tool: that wiki drives its own vendored engine. Say so and stop.

## 1. Resolve canon

Run `abu:canon-resolve` for every named entity in the scene. Use the locked sheet
paths it returns. Never describe a character's clothing or face in the scene text;
if a look is bound, the words come from canon.

## 2. Assemble the prompt

Four blocks, in this order:

1. The universe's `identity.register` anchor. It goes FIRST, always.
2. The panel law, with `--panels` substituted:

   > ONE single image divided into {N} CLEAR PANELS of equal size, arranged left to
   > right in a horizontal row, separated by generous clean cream gutters with NO
   > drawn borders and NO frame lines. Each panel is one BEAT of the same argument
   > and they read in order as a sequence. Beat two shows the CONSEQUENCE of beat
   > one rather than restating it. Keep ONE consistent world and ONE consistent cast
   > across every panel.

3. `The scene, beat by beat: {scene}`
4. The no-text law:

   > ABSOLUTELY NO TEXT ANYWHERE: no words, no letters, no numbers, no captions, no
   > speech bubbles, no labels, no UI chrome, no menus, no icons. Every beat must be
   > legible from image alone.

## 3. Generate

```bash
python3 skills/on-brand-image/scripts/generate.py \
  --out <work-dir>/candidates/<timestamp>.png --no-open \
  --entity "<universe>:<id>[@look]" \
  --size 1536x1024 --quality high \
  --prompt "<the assembled prompt>"
```

`--entity` is repeatable. Use `@look` whenever a look is bound; a bare `--entity`
with a hand-written outfit is how a blessed garment comes back wrong with nothing
complaining.

## 4. Gate: is it a strip

```bash
python3 forms/wiki-article-hero/evals/panels.py <candidate>.png --expect <N>
```

Non-zero means it came back as a plate. Regenerate FROM SCRATCH. Never stack an
edit pass, and never accept it because it looks nice.

## 5. Gate: did the canon arrive

```bash
python3 skills/render-readback/scripts/verify_render.py <candidate>.png \
  --expect "<id>@<look>" --scene "<the scene text>"
```

Any DEFECT means regenerate from scratch. Use `crop_zoom.py` before calling a defect;
a contact sheet is downsampled and has produced false defect calls.

## 6. File the work

```
works/<YYYY-MM-DD>-<slug>-hero/
  work.json            id == the folder name
  hero.png             the blessed candidate, a STABLE name
  hero.png.recipe.json
  candidates/          every attempt, timestamped, NEVER deleted
```

`status` starts at `candidate`. Only the requester moves it to `blessed`. Looking at
the thing is the gate and you are not the one who passes it.

## 7. Install into the wiki

Only after the requester blesses it. Emit the same five-artifact contract the local
engine emits, so a wiki cannot tell which engine drew its hero:

```bash
cwebp -quiet -q 85 works/<...>/hero.png -o <wiki>/static/img/illustrations/<slug>.webp
cp works/<...>/hero.png <wiki>/illustrations/<slug>.png
cp works/<...>/hero.png.recipe.json <wiki>/static/img/illustrations/<slug>.webp.recipe.json
```

Then print, for the requester to paste:

```
Frontmatter:  image: "/img/illustrations/<slug>.webp"
Body:         ![<the verbatim scene prompt>](/img/illustrations/<slug>.webp)
```

The alt text IS the prompt, verbatim. It is the prompt archive.

## Refusals

- `--scene` is one paragraph rather than beats. Rewrite first.
- `hero_register.mode` is `local`. Wrong tool.
- The panel eval fails. Regenerate, never edit.
- Readback reports a DEFECT. Regenerate, never patch.
- You are about to bless your own work. You are not the requester.
````

- [ ] **Step 2: Verify the referenced scripts exist**

```bash
cd ~/Documents/github-repos/agentic-brand-universe
for f in skills/on-brand-image/scripts/generate.py \
         skills/render-readback/scripts/verify_render.py \
         skills/render-readback/scripts/crop_zoom.py \
         forms/wiki-article-hero/evals/panels.py; do
  [ -f "$f" ] && echo "ok   $f" || echo "MISSING $f"
done
```

Expected: four `ok` lines. A method naming a script that does not exist is the defect this check prevents.

- [ ] **Step 3: Commit**

```bash
git add forms/wiki-article-hero/PROMPT.md
git commit -m "Add the wiki-article-hero method"
```

---

### Task 4: FORM.md, with an honest status

**Files:**
- Create: `forms/wiki-article-hero/FORM.md`

**Interfaces:**
- Consumes: `PROMPT.md` from Task 3, and the real heroes produced by Unit A.
- Produces: the record `forms.py` reads for its STATUS line, and the first thing `make-a-work` surfaces to an operator.

- [ ] **Step 1: Count the actual works first**

Do not write this file from imagination. Count the real heroes that exist and list them by path. If the count is zero, STOP: Unit A has not run yet, and a form written before anything exists in it is the exact failure the framework spent a day removing.

- [ ] **Step 2: Write it**

Create `forms/wiki-article-hero/FORM.md`:

```markdown
# Form: wiki article hero

The hero image at the top of a wiki article. A STRIP OF BEATS that argues the
page's claim, so a reader who only looks at the picture still gets the argument.

Shared across universes rather than declared per universe, because a wiki hero is
the same artifact everywhere: same aspect, same no-text law, same panel law, same
five-artifact output contract. Only the register and the cast change, and those come
from the universe.

## Surface

One landscape image, 1536x1024, installed into a wiki at
`static/img/illustrations/<slug>.webp` with its source PNG and provenance recipe.

## The law it enforces

- Multipanel by default, 3 beats. One plate is the exception, not the default.
- Beat two shows the consequence of beat one. A middle panel that restates is a
  plate with extra steps.
- No text anywhere in the image.
- The alt text is the verbatim prompt.

## Goldens

<list each blessed hero by path, with its universe and panel count>

## STATUS

<Replace with the true count. Shape:>

Derived from N works. That is a hypothesis, not a standard. The next work is
expected to correct it, and if it does, edit this file rather than working around
the method.

## Evals

- `evals/panels.py` asserts the render is a strip of the expected width, not a
  plate. Called at step 4 of the method, before readback.

## Not this form

- A picture book spread. `abu:make-a-book` owns that chain.
- One on-brand image with no wiki destination. `abu:on-brand-image`.
- A wiki whose `hero_register.mode` is `local`. That wiki drives its own vendored
  engine and does not need ABU installed at all.
```

- [ ] **Step 3: Verify the form now resolves as shared and usable**

```bash
cd ~/Documents/github-repos/agentic-brand-universe
python3 skills/make-a-work/scripts/forms.py list ~/Documents/github-repos/hyperagentic-age
```

Expected: `wiki-article-hero  (shared)  usable   evals: panels.py`, plus its STATUS line, from a universe that declares no forms of its own.

- [ ] **Step 4: Verify resolve emits the source**

```bash
python3 skills/make-a-work/scripts/forms.py resolve ~/Documents/github-repos/hyperagentic-age wiki-article-hero
```

Expected: JSON with `"source": "shared"` and `"usable": true`.

- [ ] **Step 5: Commit**

```bash
git add forms/wiki-article-hero/FORM.md
git commit -m "Declare wiki-article-hero as the first shared form"
```

---

### Task 5: Document the shared root

**Files:**
- Modify: `skills/make-a-work/SKILL.md:15-31` (What a form is)
- Modify: `CLAUDE.md` (the job-indexed script table)

**Interfaces:**
- Consumes: everything above.
- Produces: the discoverability that stops the next agent re-hand-rolling.

Discoverability is a just-in-time problem. A capability nobody can find at the moment they need it does not exist.

- [ ] **Step 1: Update `make-a-work/SKILL.md`**

In the `## What a form is` section, after the table, insert:

```markdown
Forms resolve from TWO roots:

| Root | Visible to |
|---|---|
| `<abu-repo>/forms/<id>/` | every universe |
| `<universe>/forms/<id>/` | that universe only |

**Local shadows shared by id, entirely.** A universe that declares its own
`wiki-article-hero` gets exactly its own method, never a blend of the two. `list`
labels each form `(shared)` or `(local)` so nobody is surprised about where a method
came from.

Put a form in the shared root when the artifact is the same kind of thing in every
universe and only the register and cast change. A wiki article hero is the worked
example. Put it in a universe when the form only makes sense there.
```

- [ ] **Step 2: Update `CLAUDE.md`**

Add to the job-indexed table:

```markdown
| **check a hero is a strip, not a plate** | `forms/wiki-article-hero/evals/panels.py <png> --expect 3` |
```

And amend the existing `list what a universe can MAKE` row to note it now includes shared forms.

- [ ] **Step 3: Full suite green**

```bash
cd ~/Documents/github-repos/agentic-brand-universe
bash run-tests.sh
```

Expected: no `FAILED`, no `STALE` docs, no `NO TEST COUNT PARSED`.

- [ ] **Step 4: Commit**

```bash
git add skills/make-a-work/SKILL.md CLAUDE.md
git commit -m "Document the shared forms root and the shadowing rule"
```

---

### Task 6: End-to-end proof

**Files:** none. This task proves the unit.

- [ ] **Step 1: Prove a universe with no forms can now make one**

```bash
cd ~/Documents/github-repos/agentic-brand-universe
python3 skills/make-a-work/scripts/forms.py list ~/Documents/github-repos/nation-of-fire
```

Expected: `wiki-article-hero (shared) usable`. Before this unit, this universe reported "no forms declared."

- [ ] **Step 2: Prove local shadowing works on real data**

```bash
mkdir -p ~/Documents/github-repos/christofuturism-universe/forms/wiki-article-hero
printf '# Form: local override\n\n> ## STATUS: local test override\n' \
  > ~/Documents/github-repos/christofuturism-universe/forms/wiki-article-hero/FORM.md
printf '# method\n' > ~/Documents/github-repos/christofuturism-universe/forms/wiki-article-hero/PROMPT.md
python3 skills/make-a-work/scripts/forms.py resolve \
  ~/Documents/github-repos/christofuturism-universe wiki-article-hero
```

Expected: `"source": "local"`, `"dir"` pointing into `christofuturism-universe`, and `"evals": []` proving the shared eval did not leak in.

- [ ] **Step 3: Clean up the test override**

```bash
rm -rf ~/Documents/github-repos/christofuturism-universe/forms/wiki-article-hero
python3 skills/make-a-work/scripts/forms.py resolve \
  ~/Documents/github-repos/christofuturism-universe wiki-article-hero | head -5
```

Expected: back to `"source": "shared"`.

- [ ] **Step 4: Make one real hero through the form**

Run `abu:make-a-work` against `hyperagentic-age` and one real wiki article, following `PROMPT.md` exactly. Verify the five artifacts land and that the panel eval passed at step 4 of the method.

- [ ] **Step 5: Update FORM.md's count**

The work in Step 4 raises the number. Edit the STATUS line to the new true count and add the new golden. This is the discipline the form exists to model.

```bash
git add forms/wiki-article-hero/FORM.md
git commit -m "wiki-article-hero: record the work made through the form"
```

- [ ] **Step 6: Report, do not push**

Report the hero inline for a look. Do NOT push; pushing waits for an explicit go.

---

## Self-Review

**Spec coverage:**

| Spec item | Task |
|---|---|
| B1 shared forms root, local shadows shared | 1 |
| B1 `source` field, labeled in `list` and `resolve` | 1 |
| B2 `forms/wiki-article-hero/` folder | 2, 3, 4 |
| B2 `PROMPT.md` owns the method and the gates | 3 |
| B2 destination via works/ plus install into the wiki | 3, step 6 and 7 |
| B2 `evals/panels.py` asserts a strip | 2 |
| B3 FORM.md states honest evidence | 4, and re-counted in 6 |
| Five-artifact contract identical to Unit A | 3, step 7 |
| Existing christofuturism forms still resolve | 1 step 7, 6 step 2 |
| Reverting the survey change fails the tests | 1 step 6 |

**Type consistency:** `survey(root, shared_root=None)` is defined in Task 1 Step 3 and called with that keyword in every test in Task 1 Step 1. `shared_forms_root()` is defined once and asserted in `test_shared_root_resolves_to_the_repo`. `count_panels(path, *, min_gutter_px, flat_max, light_min)` matches Unit A's signature exactly, which is what makes the deliberate duplication safe to diff.

**Deliberate duplication, flagged:** `evals/panels.py` and Unit A's `check_panels.py` are the same logic in two repos. This follows the precedent the spec already set and Gary already approved for `generate.py` ("Accepted. Portability is the whole point"). Both headers name the sibling.

**Prerequisite gate:** Task 4 cannot be completed truthfully before Unit A has produced real heroes. Task 4 Step 1 makes that a hard stop rather than a note.
