# Phase A+B — Reference-matrix standard + Register-in-identity (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the two coupled foundations of the framework skill catalog: (A) a per-kind **reference-matrix standard** with an engine `lock_level()` report, and (B) **register/style as first-class `identity`**, defaulted and style-locked by the start-universe flow. Bump the framework to v0.4.

**Architecture:** Additive, back-compatible engine change (new `matrix.py` + `lock_level` in `refs.py`; existing `validate`/`assert-story` hard-fail semantics unchanged). SPEC gains §12 (matrix) and extends §11 (register). The scaffold emits an `identity.register` block; `start-new-story-universe` defaults it to "detailed comic book" and adds a style-lock step. AITX is the live test bed.

**Tech Stack:** Python 3 stdlib (engine), Markdown (SPEC + skill). Engine tests via `python3 -m unittest` (pytest is NOT installed).

## Global Constraints

- **Parent design:** `agenticstory/docs/superpowers/specs/2026-07-18-framework-skill-catalog-design.md`. This plan implements only Phases A + B.
- **Framework, not per-universe:** all changes land in `agenticstory` (SPEC, engine, scaffold, skill). Universes (AITX, nof-universe) receive only DATA (an `identity.register` block).
- **Back-compatible:** the matrix is ADVISORY in v0.4. `validate` and `assert-story` keep their exact current behavior — a missing `requiredForRender` sheet still hard-fails; the matrix only adds a `lock_level` report. A pre-v0.4 `universe.json` (no `register`) must still validate and render.
- **Self-containment (SPEC §3a):** any asset the standard introduces (the style anchor) lives inside the universe repo under `reference/register/`.
- **Version:** bump `SPEC_VERSION` `0.3` → `0.4` in `engine/agenticstory/__init__.py`; SPEC header + changelog updated. The engine scaffold test reads the `SPEC_VERSION` constant (not a literal), so the bump is safe.
- **Voice:** no em dashes in committed prose or commit messages.

**Absolute paths:**
- Framework: `/Users/garysheng/Documents/github-repos/agenticstory`
- Engine: `/Users/garysheng/Documents/github-repos/agenticstory/engine`
- Start-universe skill: `/Users/garysheng/Documents/github-repos/agenticstory/skills/start-new-story-universe/SKILL.md`
- AITX test bed: `/Users/garysheng/Documents/github-repos/aitx/universe`

---

## File Structure

- Create: `engine/agenticstory/matrix.py` — the per-kind reference matrix table + `matrix_for()`.
- Modify: `engine/agenticstory/refs.py` — add `lock_level(store, eid)`.
- Modify: `engine/agenticstory/__init__.py` — export `lock_level`, `REFERENCE_MATRIX`; bump `SPEC_VERSION`.
- Modify: `engine/agenticstory/cli.py` — add a `lock-level <universe> <entity>` subcommand (so the report is usable from skills).
- Modify: `engine/tests/test_engine.py` — tests for `lock_level` across kinds + back-compat.
- Modify: `engine/agenticstory/scaffold.py` — add `register` to the emitted `identity`; create `reference/register/.gitkeep`.
- Modify: `SPEC.md` — §12 (matrix), extend §11 (register), header + changelog + glossary.
- Modify: `skills/start-new-story-universe/SKILL.md` — register default + style-lock step + matrix awareness + done criteria.
- Modify: `/Users/garysheng/Documents/github-repos/aitx/universe/universe.json` — add `identity` (with `register`) + spec v0.4.

---

## Task 1: Engine — reference matrix module + `lock_level` (TDD)

**Files:**
- Create: `engine/agenticstory/matrix.py`
- Modify: `engine/agenticstory/refs.py`
- Modify: `engine/agenticstory/__init__.py`
- Test: `engine/tests/test_engine.py`

**Interfaces:**
- Produces: `matrix.REFERENCE_MATRIX: dict`, `matrix.matrix_for(kind: str) -> dict | None`, and `refs.lock_level(store: CanonStore, eid: str) -> "stub" | "partial" | "locked"`. `lock_level` is advisory; it never raises for an unknown entity (returns `"stub"`).

- [ ] **Step 1: Write the failing test**

Add to `engine/tests/test_engine.py` (a new test method on the existing test class, or a new class — match the file's style):

```python
def test_lock_level_reports_matrix_completeness(self):
    import tempfile, json, os
    from pathlib import Path
    from agenticstory import CanonStore
    from agenticstory.refs import lock_level
    d = Path(tempfile.mkdtemp())
    (d / "canon" / "entities").mkdir(parents=True)
    (d / "stories").mkdir()
    (d / "canon" / "relations").mkdir()
    (d / "universe.json").write_text(json.dumps({"name": "t", "assetRoot": "."}))
    art = d / "art"; art.mkdir()
    def png(name):
        p = art / name; p.write_bytes(b"x"); return f"art/{name}"
    # a character with the FULL matrix on disk -> locked
    full = {
        "id": "hero", "kind": "character",
        "structured": {
            "sheets": {k: png(f"{k}.png") for k in
                       ["face-neutral","face-3q","expressions","forward-fullbody",
                        "profile-left","profile-right","back","signature-pose"]},
            "requiredForRender": ["forward-fullbody","face-neutral"],
        },
    }
    # a character with only required on disk (legacy-style keys) -> partial
    partial = {
        "id": "sidekick", "kind": "character",
        "structured": {"sheets": {"man": png("man.png"), "face": png("face.png")},
                       "requiredForRender": ["man","face"]},
    }
    # a character with no sheets -> stub
    stub = {"id": "ghost", "kind": "character", "structured": {"sheets": {}, "requiredForRender": []}}
    for e in (full, partial, stub):
        (d / "canon" / "entities" / f"{e['id']}.json").write_text(json.dumps(e))
    store = CanonStore(d)
    self.assertEqual(lock_level(store, "hero"), "locked")
    self.assertEqual(lock_level(store, "sidekick"), "partial")
    self.assertEqual(lock_level(store, "ghost"), "stub")
    self.assertEqual(lock_level(store, "nonexistent"), "stub")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /Users/garysheng/Documents/github-repos/agenticstory/engine && python3 -m unittest tests.test_engine -v 2>&1 | tail -8`
Expected: FAIL — `ImportError: cannot import name 'lock_level'` (or AttributeError).

- [ ] **Step 3: Create the matrix module**

Create `engine/agenticstory/matrix.py`:

```python
"""Reference matrix (SPEC v0.4 §12): what 'locked' means per entity kind.

ADVISORY in v0.4 — `lock_level` (in refs.py) reports completeness against this
table. It does NOT change the load-bearing gate's hard-fail on a missing
REQUIRED sheet (refs.assert_story / assert_spread are unchanged).
"""
from __future__ import annotations

# Per-kind canonical reference shots for kinds addressed by `structured.sheets`.
# `shots` is the full matrix (needed for 'locked'); `required` is the minimum.
# setting / visual-metaphor are matrixed via their `contract` (see refs.resolve_setting),
# not sheet keys, so they are intentionally absent here.
REFERENCE_MATRIX: dict[str, dict] = {
    "character": {
        "shots": ["face-neutral", "face-3q", "expressions", "forward-fullbody",
                  "profile-left", "profile-right", "back", "signature-pose"],
        "required": ["forward-fullbody", "face-neutral"],
    },
    "prop":  {"shots": ["hero", "detail"], "required": ["hero"]},
    "motif": {"shots": ["hero", "detail"], "required": ["hero"]},
}


def matrix_for(kind: str) -> dict | None:
    """The reference matrix for a kind, or None if the kind is not sheet-matrixed."""
    return REFERENCE_MATRIX.get(kind)
```

- [ ] **Step 4: Add `lock_level` to refs.py**

Add to `engine/agenticstory/refs.py` (it already imports `CanonStore` and defines `resolve_setting`):

```python
from .matrix import matrix_for  # add near the top imports


def lock_level(store: CanonStore, eid: str) -> str:
    """Advisory reference-completeness of an entity: 'stub' | 'partial' | 'locked'.

    - setting / visual-metaphor: 'locked' iff resolve_setting reports no problems.
    - sheet-matrixed kinds (character/prop/motif): 'locked' iff the kind's FULL
      matrix resolves on disk; 'partial' iff the entity's own requiredForRender
      sheets resolve (covers legacy key names); else 'stub'.
    - other kinds: 'locked' iff requiredForRender resolves; 'partial' if it has
      sheets but they do not all resolve; else 'stub'.
    Never raises: an unknown entity is 'stub'.
    """
    e = store.entity(eid)
    if e is None:
        return "stub"
    if e.kind in ("setting", "visual-metaphor"):
        problems = resolve_setting(store, eid)
        if not problems:
            return "locked"
        contract = e.raw.get("contract", {}) or {}
        has_any = any(
            isinstance(contract.get(f), str) and (store.asset_root / contract[f]).exists()
            for f in ("turnaround", "blueprint")
        )
        return "partial" if has_any else "stub"

    root = store.asset_root
    sheets = (e.raw.get("structured") or {}).get("sheets") or {}
    if not sheets:
        return "stub"

    def on_disk(key: str) -> bool:
        v = sheets.get(key)
        return isinstance(v, str) and (root / v).exists()

    req = e.required_sheet_keys()
    req_ok = bool(req) and all(on_disk(k) for k in req)

    m = matrix_for(e.kind)
    if m is None:
        return "locked" if req_ok else "partial"
    if all(on_disk(k) for k in m["shots"]):
        return "locked"
    return "partial" if req_ok else "stub"
```

- [ ] **Step 5: Export from `__init__.py` and bump the version**

In `engine/agenticstory/__init__.py`:
- Change the refs import line to include `lock_level`:
  `from .refs import assert_story, assert_spread, resolve_entity_assets, resolve_setting, lock_level  # noqa: F401`
- Add: `from .matrix import REFERENCE_MATRIX, matrix_for  # noqa: F401`
- Change `SPEC_VERSION = "0.3"` to `SPEC_VERSION = "0.4"`.

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd /Users/garysheng/Documents/github-repos/agenticstory/engine && python3 -m unittest tests.test_engine -v 2>&1 | tail -4`
Expected: OK, all tests pass (the new one + the existing 17).

- [ ] **Step 7: Add a `lock-level` CLI subcommand**

In `engine/agenticstory/cli.py`, register a subcommand mirroring the existing ones (e.g. next to `assert-story`):

```python
    ll = sub.add_parser("lock-level"); ll.add_argument("universe"); ll.add_argument("entity")
```

and in the dispatch section (where other subcommands are handled), add:

```python
    elif args.cmd == "lock-level":
        from .refs import lock_level
        store = CanonStore(Path(args.universe))
        print(lock_level(store, args.entity))
```

(Match the file's existing arg-parsing and dispatch style; read the surrounding lines first.)

- [ ] **Step 8: Verify the CLI works**

Run: `cd /Users/garysheng/Documents/github-repos/agenticstory/engine && python3 -m agenticstory.cli lock-level /Users/garysheng/Documents/github-repos/aitx/universe michael-daigler`
Expected: prints `partial` or `stub` (michael has some reference art but not the full v0.4 matrix keys) — a clean single-word line, exit 0.

- [ ] **Step 9: Commit**

```bash
cd /Users/garysheng/Documents/github-repos/agenticstory
git add engine/agenticstory/matrix.py engine/agenticstory/refs.py engine/agenticstory/__init__.py engine/agenticstory/cli.py engine/tests/test_engine.py
git commit -m "feat(engine): reference-matrix standard + advisory lock_level (v0.4)"
```

---

## Task 2: SPEC v0.4 — §12 reference matrix + §11 register extension

**Files:**
- Modify: `SPEC.md`

**Interfaces:**
- Produces: the documented standard the skills and engine reference. No code.

- [ ] **Step 1: Bump the header + changelog**

In `SPEC.md`, change the version line `**v0.3 — 2026-07-18.**` to `**v0.4 — 2026-07-18.**` and add a changelog bullet under the existing v0.3 block:

```markdown
> **v0.4 changelog:** (1) **§12 Reference-matrix standard** — a per-kind canonical shot set
> defines what "locked" means; the engine reports `lock_level` (stub/partial/locked), advisory
> and back-compatible (the load-bearing gate's hard-fail on missing required sheets is unchanged).
> (2) **Register in identity** — a universe's illustrative style is a first-class `identity.register`
> (named style + a content-neutral style anchor passed first on every render), defaulted by the
> start-universe flow.
```

- [ ] **Step 2: Extend §11 with the register block**

In `SPEC.md` §11, in the `identity` JSONC example, add the `register` field, and add a short paragraph after the block:

```markdown
  "register": {                              // the universe's illustrative style (v0.4)
    "name": "detailed comic book",           // named style, defaulted by start-universe
    "anchor": "reference/register/style-anchor.png", // content-neutral swatch, passed FIRST every render
    "rejectedPoles": ["photoreal", "anime", "washed-out"]
  }
```

> **Register (v0.4).** A universe renders in one illustrative style. `identity.register` names it and
> points at a content-neutral **style anchor** the renderer passes as the first reference on every
> render, with `rejectedPoles` baked as negatives. A per-property `register` (SPEC §4.3) may still
> override it. `start-new-story-universe` defaults `register.name` to "detailed comic book" and locks
> the anchor via a style-lock step.
```

- [ ] **Step 3: Add §12 Reference-matrix standard**

Insert a new `## 12. Reference-matrix standard (v0.4)` section before `## 10. Glossary` (after §11):

```markdown
## 12. Reference-matrix standard (v0.4)

"Locked" must mean something checkable per kind. The reference matrix is the canonical set of
reference shots an entity needs before it is fully renderable, so tooling can report
under-referenced entities the way the gate reports missing files.

- **character** — the anti-uncanny-valley set: `face-neutral`, `face-3q`, `expressions`,
  `forward-fullbody`, `profile-left`, `profile-right`, `back`, `signature-pose`. Minimum
  (`requiredForRender`) is `forward-fullbody` + `face-neutral`; the rest strengthen identity
  consistency across renders. Real people are generated from a photo stack (never a
  painting-of-a-painting); fictional characters from a locked design.
- **setting** — the existing `contract`: `turnaround`, `emptyPlates[]`, `blueprint` (files) plus
  `map`, `blocking`, `dressing` (descriptors). Unchanged; named here as the setting matrix.
- **visual-metaphor** — a locked master plus `state` plates (the object across its argued states).
- **prop / motif** — `hero` plus `detail` crops.

**`lock_level(entity) -> stub | partial | locked`** (engine) reports completeness against the kind's
matrix. It is **advisory** in v0.4 and back-compatible: an entity that predates the matrix, or uses
its own sheet-key names, reports `partial` when its own `requiredForRender` resolves — it is not
broken, just not matrix-complete. The load-bearing gate (`assert_story` / `assert_spread`) is
unchanged: a missing REQUIRED sheet is still a hard error. A renderer MAY require `locked`.
```

- [ ] **Step 4: Add glossary entries**

In `SPEC.md` §10 Glossary, add:

```markdown
- **Reference matrix (§12)** — the canonical set of reference shots an entity needs per kind
  (a character's ~8 angles, a setting's contract, a visual-metaphor's states, a prop's hero+crops).
- **lock_level** — an advisory engine report of an entity's reference completeness: stub, partial,
  or locked against its kind's matrix. Distinct from the load-bearing gate, which hard-fails on
  missing required sheets.
- **Register** — a universe's illustrative style, a first-class `identity.register` (named style +
  a content-neutral style anchor passed first on every render); may be overridden per property.
```

- [ ] **Step 5: Commit**

```bash
cd /Users/garysheng/Documents/github-repos/agenticstory
git add SPEC.md
git commit -m "spec: v0.4 — §12 reference-matrix standard + §11 register-in-identity"
```

---

## Task 3: Scaffold emits `identity.register` + `reference/register/`

**Files:**
- Modify: `engine/agenticstory/scaffold.py`
- Test: `engine/tests/test_engine.py`

**Interfaces:**
- Consumes: the `identity` block added to the scaffold in v0.3.
- Produces: a scaffolded `universe.json` whose `identity` includes a `register` block, and a `reference/register/.gitkeep`.

- [ ] **Step 1: Write the failing test**

Add to `engine/tests/test_engine.py`:

```python
def test_scaffold_emits_register_and_reference_dir(self):
    import tempfile, json
    from pathlib import Path
    from agenticstory import scaffold
    d = Path(tempfile.mkdtemp()) / "demo-universe"
    scaffold.scaffold_universe(d, name="demo")
    man = json.loads((d / "universe.json").read_text())
    reg = man["identity"]["register"]
    self.assertEqual(reg["name"], "detailed comic book")
    self.assertIsNone(reg["anchor"])            # not locked yet
    self.assertIn("photoreal", reg["rejectedPoles"])
    self.assertTrue((d / "reference" / "register" / ".gitkeep").exists())
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/garysheng/Documents/github-repos/agenticstory/engine && python3 -m unittest tests.test_engine -v 2>&1 | tail -6`
Expected: FAIL (`KeyError: 'register'`).

- [ ] **Step 3: Add the register block + reference dir to the scaffold**

In `engine/agenticstory/scaffold.py`, in the `identity` dict written into `universe.json`, add a `register` key:

```python
            "register": {
                "name": "detailed comic book",   # default illustrative style (SPEC v0.4 §11/§12)
                "anchor": None,                   # locked via start-universe's style-lock step
                "rejectedPoles": ["photoreal", "anime", "washed-out"],
            },
```

And in the canon-dir creation block (where `canon/entities`, `canon/relations`, `stories` get `.gitkeep`), add `reference/register` so a home for the style anchor exists:

```python
    for d in ("canon/entities", "canon/relations", "stories", "reference/register"):
        write(f"{d}/.gitkeep", "")
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd /Users/garysheng/Documents/github-repos/agenticstory/engine && python3 -m unittest tests.test_engine -v 2>&1 | tail -4`
Expected: OK (new test + all prior pass).

- [ ] **Step 5: Sanity-scaffold a throwaway universe**

Run: `cd /Users/garysheng/Documents/github-repos/agenticstory/engine && T=$(mktemp -d)/x-universe && python3 -m agenticstory.cli init "$T" --name x && python3 -c "import json;print(json.load(open('$T/universe.json'))['identity']['register'])" && python3 -m agenticstory.cli validate "$T" | head -1 && rm -rf "$(dirname "$T")"`
Expected: prints the register dict (name "detailed comic book", anchor None) and `validate ... OK`.

- [ ] **Step 6: Commit**

```bash
cd /Users/garysheng/Documents/github-repos/agenticstory
git add engine/agenticstory/scaffold.py engine/tests/test_engine.py
git commit -m "feat(scaffold): emit identity.register default + reference/register/ (v0.4)"
```

---

## Task 4: `start-new-story-universe` — register default + style-lock step

**Files:**
- Modify: `skills/start-new-story-universe/SKILL.md`

**Interfaces:**
- Produces: the operator-facing recipe now establishes the register and locks a style anchor. Prose only.

- [ ] **Step 1: Add register to the Phase 1 interview**

In `skills/start-new-story-universe/SKILL.md`, the existing `- **Identity** —` bullet already lists identity fields. Add register to it (append to that bullet):

```markdown
  Also set `identity.register`: the universe's illustrative **style** (default **"detailed comic
  book"**), which the renderer passes as a style anchor on every render. Note any `rejectedPoles`
  (styles to bake as negatives, e.g. photoreal, anime, washed-out).
```

- [ ] **Step 2: Add a style-lock step to Phase 2 (Scaffold)**

In Phase 2, after the "Fill the `identity` block" bullet, add:

```markdown
- **Style-lock (register anchor).** The scaffold sets `register.name` (default "detailed comic
  book") with `register.anchor: null`. Lock the anchor before rendering: generate a content-neutral
  style swatch in that named style (no universe characters, just palette + line + finish), get the
  operator's "that's the look" approval, save it to `reference/register/style-anchor.png`, and set
  `identity.register.anchor` to that path. Until locked, renderers warn and fall back to wording.
```

- [ ] **Step 3: Add matrix awareness to Phase 3 (Seed the first canon)**

In Phase 3, in the Entities bullet, add a sentence:

```markdown
  A renderer-consumed entity is complete when its **reference matrix** (SPEC §12) is locked: for a
  character, the ~8-shot set (face-neutral/3q/expressions, forward-fullbody, profile L+R, back,
  signature-pose); for a setting, its contract plates; for a visual-metaphor, its states. Use
  `abu lock-level <universe> <entity>` to see stub/partial/locked. Authoring a new entity
  is the job of the `add-*` framework skills (they scaffold the matrix slots + prompts).
```

- [ ] **Step 4: Add to Definition of done**

In the `## Definition of done` list, add:

```markdown
- `identity.register` is set (default "detailed comic book") and its **style anchor is locked**
  (`reference/register/style-anchor.png` exists, `register.anchor` points at it).
```

- [ ] **Step 5: Commit**

```bash
cd /Users/garysheng/Documents/github-repos/agenticstory
git add skills/start-new-story-universe/SKILL.md
git commit -m "docs(skill): start-universe sets identity.register + style-lock step (v0.4)"
```

---

## Task 5: Apply Phase B to the AITX test bed (data only)

**Files:**
- Modify: `/Users/garysheng/Documents/github-repos/aitx/universe/universe.json`

**Interfaces:**
- Consumes: the v0.4 identity+register shape.
- Produces: AITX carrying a filled `identity` (with `register`) and spec v0.4 — the reference implementation for Phase B.

- [ ] **Step 1: Add the identity + register block to AITX**

Edit `/Users/garysheng/Documents/github-repos/aitx/universe/universe.json` to add a `spec` (v0.4) and an `identity` block. Preserve `name` and `assetRoot`. Use AITX's real values (from its README): brand palette `#ff4201 / #010101 / #ffffff`, the aitx-mark motif, community voice. Result:

```json
{
  "name": "aitx",
  "assetRoot": ".",
  "spec": {
    "framework": "agenticstory",
    "version": "0.4",
    "wiki": "https://agenticstory.wiki",
    "conformsTo": "https://agenticstory.wiki/spec v0.4"
  },
  "identity": {
    "mark": "An AITX story",
    "platformUniverseId": "aitx",
    "theme": "aitx-ff4201",
    "closingOrnament": null,
    "voice": { "capitalize": [], "oneWord": [] },
    "subjectApproval": { "realLivingPerson": "requires-blessing" },
    "register": {
      "name": "detailed comic book",
      "anchor": null,
      "rejectedPoles": ["photoreal", "anime", "washed-out"]
    }
  },
  "note": "AITX universe canon (agenticstory schema v0.4). Self-contained: assetRoot is '.' and every referenced asset lives inside this repo. Generic Agentic Brand Universe skills read the identity block above. Register style anchor to be locked via the style-lock step."
}
```

- [ ] **Step 2: Verify AITX still validates and lock_level reports work**

Run:
```bash
cd /Users/garysheng/Documents/github-repos/agenticstory/engine
python3 -m agenticstory.cli validate /Users/garysheng/Documents/github-repos/aitx/universe | head -1
python3 -m agenticstory.cli lock-level /Users/garysheng/Documents/github-repos/aitx/universe michael-daigler
python3 -m agenticstory.cli lock-level /Users/garysheng/Documents/github-repos/aitx/universe aitx-mark
```
Expected: `validate [aitx]: OK`; `michael-daigler` prints `partial` or `stub` (has face+full GABRs but not the v0.4 matrix keys); `aitx-mark` (a motif) prints its level. No crash.

- [ ] **Step 3: Commit (in the aitx repo)**

```bash
cd /Users/garysheng/Documents/github-repos/aitx
git add universe/universe.json
git commit -m "feat: add identity block (mark, register, voice, subject-approval) + spec v0.4"
```

---

## Verification (whole phase)

- [ ] Engine: `cd .../agenticstory/engine && python3 -m unittest discover -s tests -p 'test_*.py'` → OK (all tests, including the 2 new ones).
- [ ] Back-compat: `python3 -m agenticstory.cli validate` on BOTH `aitx/universe` and `nation-of-fire/nof-universe` → each prints its normal result (AITX OK; NoF its 2 pre-existing `readier-than-a-year-ago` notes). No new failure.
- [ ] `nof-universe` self-containment unchanged: `cd .../nof-universe && python3 scripts/verify_selfcontained.py` → A=0, B=0, C=0.
- [ ] A fresh `abu init` scaffolds a universe with `identity.register` + `reference/register/` and validates green.
- [ ] `SPEC.md` reads v0.4 with §12 present and §11 carrying `register`.

## Out of scope (later phases)

- The `add-*` authoring skills (Phase C), `lock-references` art skill (Phase D).
- Migrating the 9 NoF skills (Phase E) and retiring the NoF plugin (Phase F).
- Making the matrix a HARD gate (it stays advisory in v0.4).
- Migrating `nof-universe`'s `identity` to add a `register` block (a one-line data add, folded into Phase E when NoF's renderer starts reading it) and renaming `aitx/universe` to `aitx/aitx-universe` (cosmetic, deferred).
