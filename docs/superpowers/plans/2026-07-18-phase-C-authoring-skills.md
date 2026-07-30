# Phase C — Atomic authoring skills (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** A framework skill for every atomic canon-authoring unit — `add-character`, `add-setting`, `add-visual-metaphor`, `add-motif`, `add-prop`, `add-story`, `add-relation` — each generic and universe-parameterized. Under them, a tested engine helper (`scaffold_entity` + an `add-entity` CLI) emits a schema-valid entity stub with the kind's reference-matrix slots, so authoring is machinery, not hand-written JSON. Art generation stays a separate step (Phase D `lock-references`).

**Architecture:** Engine gains `authoring.py` (`scaffold_entity`) + an `add-entity` CLI that writes the entity JSON and creates the entity's `reference/<id>/` home. The `add-*` skills are SKILL.md files that do the human parts (interview, photo collection, decisions) then call `add-entity` and write a `prompts.md` from `identity.register`. A freshly scaffolded entity validates green with `lock_level == "stub"`; it becomes gate-real only when `lock-references` fills the matrix.

**Tech Stack:** Python 3 stdlib (engine), Markdown (skills). Tests via `python3 -m unittest`.

## Global Constraints

- **Parent design:** `docs/superpowers/specs/2026-07-18-framework-skill-catalog-design.md` (Phase C). Builds on v0.4 (reference matrix + identity.register).
- **Framework only:** engine + skills land in `agenticstory`; universes (AITX) receive only data.
- **Validate-green scaffold:** a scaffolded entity must pass `validate` immediately. Per the engine model: a `character` needs non-empty `structured.sheets` and every `requiredForRender` key must have a non-null path; a `realPerson` block needs a non-empty `photoStack`. Therefore the scaffold emits matrix keys as **null slots** with **`requiredForRender: []`**, and includes a `realPerson` block ONLY when a non-empty photo stack is supplied. `lock-references` (Phase D) later fills paths and promotes the required set.
- **Reference matrix source of truth:** `matrix.REFERENCE_MATRIX` (SPEC §12). Character slots = its 8 shots; prop/motif = hero+detail; setting/visual-metaphor use the `contract`.
- **Real-person gate:** a real-person character is created `realPerson.approval.state: "gated"` and stays gated until the subject blesses it. Never collect or store private details flagged on the sensitive list.
- **Back-compat:** additive only; no change to `validate`/`assert_*`/`lock_level` behavior.
- **Voice:** no em dashes in committed prose or commit messages.

**Absolute paths:** framework `/Users/garysheng/Documents/github-repos/agenticstory`; engine `.../agenticstory/engine`; AITX test bed `/Users/garysheng/Documents/github-repos/aitx/universe`.

---

## File Structure

- Create: `engine/agenticstory/authoring.py` — `scaffold_entity(kind, eid, name, ...) -> dict`.
- Modify: `engine/agenticstory/cli.py` — `add-entity` subcommand (writes the JSON + reference dirs).
- Modify: `engine/agenticstory/__init__.py` — export `scaffold_entity`.
- Modify: `engine/tests/test_engine.py` — tests: each kind scaffolds valid + lock_level stub; real-person requires photos.
- Create: `skills/add-character/SKILL.md` — the flagship (interview + photo stack + matrix + prompts).
- Create: `skills/add-setting/SKILL.md`, `skills/add-visual-metaphor/SKILL.md`, `skills/add-motif/SKILL.md`, `skills/add-prop/SKILL.md`, `skills/add-story/SKILL.md`, `skills/add-relation/SKILL.md`.
- Modify: `README.md` (agenticstory) — list the authoring skills.

---

## Task 1: Engine — `scaffold_entity` + `add-entity` CLI (TDD)

**Files:** Create `engine/agenticstory/authoring.py`; modify `cli.py`, `__init__.py`, `tests/test_engine.py`.

**Interfaces:**
- Produces: `authoring.scaffold_entity(kind: str, eid: str, name: str, origin_story: str | None = None, photo_stack: list[str] | None = None) -> dict` returning a schema-valid entity dict. If `photo_stack` is a non-empty list, a `realPerson` block is included (character kinds only). CLI `add-entity <universe> <kind> <eid> [--name N] [--origin S] [--photo path ...]` writes `canon/entities/<eid>.json`, creates `reference/<eid>/` (and `reference/<eid>/photos/` when photos given), and prints the entity's `lock_level`.

- [ ] **Step 1: Write the failing test**

Add to `engine/tests/test_engine.py`:

```python
def test_scaffold_entity_validates_and_reports_stub(self):
    import json
    from agenticstory import CanonStore, scaffold_entity
    from agenticstory.model import Entity
    from agenticstory.refs import lock_level
    import tempfile
    from pathlib import Path
    d = Path(tempfile.mkdtemp())
    (d / "canon" / "entities").mkdir(parents=True)
    (d / "canon" / "relations").mkdir()
    (d / "stories").mkdir()
    (d / "universe.json").write_text(json.dumps({"name": "t", "assetRoot": "."}))
    # character (fictional): 8 matrix slots, requiredForRender empty, validates, lock_level stub
    ch = scaffold_entity("character", "hero", "Hero")
    self.assertEqual(set(ch["structured"]["sheets"].keys()),
                     {"face-neutral","face-3q","expressions","forward-fullbody",
                      "profile-left","profile-right","back","signature-pose"})
    self.assertEqual(ch["structured"]["requiredForRender"], [])
    self.assertNotIn("realPerson", ch)
    self.assertEqual(Entity.from_dict(ch).validate(), [])
    # real person: photo stack required -> realPerson gated
    rp = scaffold_entity("character", "vip", "Vip", photo_stack=["reference/vip/photos/01.jpg"])
    self.assertEqual(rp["realPerson"]["approval"]["state"], "gated")
    self.assertEqual(rp["realPerson"]["photoStack"], ["reference/vip/photos/01.jpg"])
    self.assertEqual(Entity.from_dict(rp).validate(), [])
    # setting: unlocked contract, validates
    st = scaffold_entity("setting", "the-hall", "The Hall")
    self.assertEqual(st["status"], "unlocked")
    self.assertIn("contract", st)
    self.assertEqual(Entity.from_dict(st).validate(), [])
    # prop: hero+detail slots
    pr = scaffold_entity("prop", "the-key", "The Key")
    self.assertEqual(set(pr["structured"]["sheets"].keys()), {"hero","detail"})
    self.assertEqual(Entity.from_dict(pr).validate(), [])
    # write them and confirm lock_level stub + store validates
    for e in (ch, rp, st, pr):
        (d / "canon" / "entities" / f"{e['id']}.json").write_text(json.dumps(e))
    store = CanonStore(d)
    self.assertEqual(store.validate_canon(), [])
    self.assertEqual(lock_level(store, "hero"), "stub")
    self.assertEqual(lock_level(store, "the-hall"), "stub")
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/garysheng/Documents/github-repos/agenticstory/engine && python3 -m unittest tests.test_engine -v 2>&1 | tail -6`
Expected: FAIL — `ImportError: cannot import name 'scaffold_entity'`.

- [ ] **Step 3: Create `authoring.py`**

Create `engine/agenticstory/authoring.py`:

```python
"""Deterministic entity scaffolding (SPEC v0.4 §12 reference matrix).

The `add-*` skills call this so authoring is tested machinery, not hand-written
JSON. A scaffolded entity validates green immediately with lock_level == "stub":
its reference-matrix slots are null and requiredForRender is empty until the art
step (lock-references) fills paths and promotes the required set.
"""
from __future__ import annotations

from .matrix import matrix_for


def scaffold_entity(
    kind: str,
    eid: str,
    name: str,
    origin_story: str | None = None,
    photo_stack: list[str] | None = None,
) -> dict:
    """A schema-valid entity stub for `kind`. Raises ValueError on an unknown kind.

    - character/prop/motif: `structured.sheets` carries the kind's matrix keys as
      null slots; `requiredForRender` is [] (populated when art locks).
    - setting/visual-metaphor: an `unlocked` `contract` (refused until locked).
    - a non-empty `photo_stack` (character only) adds a `gated` `realPerson` block.
    """
    KNOWN = {"character", "setting", "visual-metaphor", "doctrine", "motif", "beat", "prop", "group"}
    if kind not in KNOWN:
        raise ValueError(f"unknown kind '{kind}' (allowed: {sorted(KNOWN)})")

    ent: dict = {
        "id": eid,
        "kind": kind,
        "originStory": origin_story,
        "authority": {"lockedBy": "TODO-you", "lockedOn": None},
    }

    if kind in ("character", "prop", "motif"):
        m = matrix_for(kind)
        shots = m["shots"] if m else ["hero"]
        ent["structured"] = {
            "sheets": {s: None for s in shots},   # null slots -> filled by lock-references
            "requiredForRender": [],               # promoted to the matrix required set on lock
            "invariants": [],
        }
        ent["prose"] = {"voice": "", "lore": "", "rules": ""}
        if kind == "character" and photo_stack:
            ent["realPerson"] = {
                "photoStack": list(photo_stack),
                "canonicalPhotos": {},
                "approval": {"state": "gated", "by": eid, "on": None},
                "sensitiveList": "RESEARCH.md#sensitive",
                "wardrobeEras": {"default": ""},
                "groupCount": None,
            }
    elif kind in ("setting", "visual-metaphor"):
        ent["status"] = "unlocked"
        ent["contract"] = {
            "turnaround": None, "emptyPlates": [], "blueprint": None,
            "map": "", "blocking": "", "dressing": "",
        }
        ent["prose"] = {"rules": ""}
    else:  # doctrine, beat, group
        ent["structured"] = {"sheets": {}, "requiredForRender": []}
        ent["prose"] = {"rules": ""}

    return ent
```

- [ ] **Step 4: Export from `__init__.py`**

Add: `from .authoring import scaffold_entity  # noqa: F401`.

- [ ] **Step 5: Run to verify it passes**

Run: `cd /Users/garysheng/Documents/github-repos/agenticstory/engine && python3 -m unittest tests.test_engine -v 2>&1 | tail -4`
Expected: OK (new test + all prior; 21 total).

- [ ] **Step 6: Add the `add-entity` CLI subcommand**

Read `cli.py` first to match its dispatch style. Register:

```python
    ae = sub.add_parser("add-entity")
    ae.add_argument("universe"); ae.add_argument("kind"); ae.add_argument("eid")
    ae.add_argument("--name", default=""); ae.add_argument("--origin", default=None)
    ae.add_argument("--photo", action="append", default=None, help="a photo-stack path (repeatable)")
```

and in the dispatch:

```python
    elif args.cmd == "add-entity":
        from .authoring import scaffold_entity
        from .refs import lock_level
        uni = Path(args.universe)
        ent = scaffold_entity(args.kind, args.eid, args.name or args.eid,
                              origin_story=args.origin, photo_stack=args.photo)
        dest = uni / "canon" / "entities" / f"{args.eid}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(ent, indent=2) + "\n")
        (uni / "reference" / args.eid).mkdir(parents=True, exist_ok=True)
        if args.photo:
            (uni / "reference" / args.eid / "photos").mkdir(parents=True, exist_ok=True)
        store = CanonStore(uni)
        print(f"wrote {dest.relative_to(uni)}  (lock_level: {lock_level(store, args.eid)})")
```

(Adapt names/imports to the file's actual style; ensure `json` and `CanonStore` are imported at the top as the other subcommands use them.)

- [ ] **Step 7: Verify the CLI on a throwaway universe**

Run:
```bash
cd /Users/garysheng/Documents/github-repos/agenticstory/engine
T=$(mktemp -d)/x-universe && python3 -m agenticstory.cli init "$T" --name x >/dev/null
python3 -m agenticstory.cli add-entity "$T" character alex --name Alex
python3 -m agenticstory.cli validate "$T" | head -1
python3 -c "import json;print('slots:', list(json.load(open('$T/canon/entities/alex.json'))['structured']['sheets']))"
rm -rf "$(dirname "$T")"
```
Expected: `wrote canon/entities/alex.json  (lock_level: stub)`; `validate ... OK`; the 8 character slots printed.

- [ ] **Step 8: Commit**

```bash
cd /Users/garysheng/Documents/github-repos/agenticstory
git add engine/agenticstory/authoring.py engine/agenticstory/cli.py engine/agenticstory/__init__.py engine/tests/test_engine.py
git commit -m "feat(engine): scaffold_entity + add-entity CLI (reference-matrix slots)"
```

---

## Task 2: `add-character` skill (flagship)

**Files:** Create `skills/add-character/SKILL.md`.

**Interfaces:** Consumes `add-entity` (Task 1) + `lock-level` + `casting-sweep` semantics. Produces a committed character entity + `reference/<id>/` (photos for real people) + a `prompts.md`. Does NOT generate art.

- [ ] **Step 1: Write the skill**

Create `skills/add-character/SKILL.md`:

```markdown
---
name: add-character
description: Add ONE character to an Agentic Brand Universe — interview the source (a real person's story/wardrobe/sensitive-list, or a fictional design brief), reuse-first via casting sweep, then scaffold a typed `character` entity with the SPEC §12 reference-matrix slots (8 shots) and a ready-to-run generation prompt per shot. Real people get a photo stack and a subject-approval gate; art is NOT generated here (that is `lock-references`). Use when adding a person/character to a universe. Generic and universe-parameterized: pass the target universe.
---

# Add Character

One character, into a universe's canon, as a typed record with its reference matrix scaffolded. This is authoring, not art: it ends with a validated `stub` entity + ready-to-run prompts. `lock-references` generates and locks the shots afterward.

## Inputs
- The target universe (a path containing `universe.json`). Read its `identity` (mark, register, voice) and `assetRoot`.
- Whether the character is a REAL living person (triggers the dossier + gate) or FICTIONAL.

## Procedure

1. **Casting sweep first (reuse wins).** Before naming a new character, sweep `canon/entities/` + any CANON.md for an existing entity that fits the role. If one fits, STOP and reuse it (a reuse is a crossover receipt, and it saves the whole matrix build). Only proceed if genuinely new.
2. **Interview (one question at a time).** Gather only what canon needs.
   - **Real person:** their name; the role they play in this universe; their story/voice; wardrobe eras (default + any activity-specific, e.g. no street clothes while running); signature physical invariants (glasses, a scar, a pendant); and the **sensitive list** — what must NEVER ship (private details). Collect a **photo stack** (aim for 8+ varied real photos: front, 3/4, profile, full-body, candids) into `reference/<id>/photos/`. Never invent or store details the subject did not authorize.
   - **Fictional:** a design brief — look, silhouette, palette, signature invariants, voice. No photo stack; no gate.
3. **Scaffold the entity (tested machinery).** From the engine dir:
   ```bash
   python3 -m agenticstory.cli add-entity <universe> character <id> --name "<Name>" \
     [--origin <first-story>] [--photo reference/<id>/photos/01.jpg --photo ...]
   ```
   This writes `canon/entities/<id>.json` with the 8 matrix slots (null), `requiredForRender: []`, and (for a real person with photos) a `gated` `realPerson` block. It prints `lock_level: stub`.
4. **Fill the prose + invariants.** Edit the entity's `prose` (voice/lore/rules) and `structured.invariants` (the load-bearing identity rules the read-back will check — e.g. `no-lenses`, `double-eyelid-crease`). For a real person, fill `realPerson.wardrobeEras` and confirm `sensitiveList` points at the universe `RESEARCH.md#sensitive` entry you populated.
5. **Write the generation prompts.** Create `reference/<id>/prompts.md`: one block per matrix shot (face-neutral, face-3q, expressions, forward-fullbody, profile-left, profile-right, back, signature-pose). Each prompt: (a) passes `identity.register.anchor` FIRST as the style anchor and bakes `register.rejectedPoles` as negatives; (b) for a real person, passes the photo stack (build from photos, never a painting-of-a-painting); (c) states the shot's angle + the entity's invariants; (d) names the target output path `reference/<id>/<shot>.png`. These are what `lock-references` will run.
6. **Validate + commit.** `abu validate <universe>` stays green. Commit the entity + reference dir + prompts.md. Report the `lock_level` (stub) and that the next step is `lock-references <universe> <id>`.

## Gates honored
- **Reuse-first** (step 1) — never invent a character an existing entity already covers.
- **Subject-approval** — a real person is `gated`; no property featuring them renders until they bless the words and art (enforced downstream; never bypass).
- **Sensitivity** — the sensitive list is populated before any art; private detail never ships.
- **No art here** — generation is `lock-references`, so this skill never calls an image model.

## Not this skill
- Generating/locking the shots → `lock-references`.
- A setting, prop, motif, story, or relation → the sibling `add-*` skills.
```

- [ ] **Step 2: Commit**

```bash
cd /Users/garysheng/Documents/github-repos/agenticstory
git add skills/add-character/SKILL.md
git commit -m "feat(skill): add-character (interview + matrix scaffold + prompts, art-free)"
```

---

## Task 3: Sibling authoring skills (setting, visual-metaphor, motif, prop, story, relation)

**Files:** Create `skills/add-setting/SKILL.md`, `skills/add-visual-metaphor/SKILL.md`, `skills/add-motif/SKILL.md`, `skills/add-prop/SKILL.md`, `skills/add-story/SKILL.md`, `skills/add-relation/SKILL.md`.

Each follows the `add-character` shape (casting-sweep where relevant → interview/brief → `add-entity` scaffold → fill prose/contract → prompts → validate + commit), scaled to its kind. Write each as a complete SKILL.md with a frontmatter `name` + `description` and a Procedure. Key differences per skill:

- [ ] **Step 1: `add-setting`** — scaffolds a `setting` (unlocked `contract`). Interview: what the place is, the shots C1/C2, fixed geometry, dressing. Prompts cover `turnaround`, per-angle `emptyPlates`, `blueprint`. Fill `map`/`blocking`/`dressing` descriptors (prose, passed every render). Stays `status: unlocked` (correctly refused) until `lock-references` fills the plates and you set `status: locked`.

- [ ] **Step 2: `add-visual-metaphor`** — a `visual-metaphor` (the spine-object a whole property argues through). Scaffold via `add-entity visual-metaphor`. Interview: the object, its argued states. Prompts cover a locked master + the state plates. Same unlocked-until-plated discipline as a setting.

- [ ] **Step 3: `add-motif`** and **Step 4: `add-prop`** — scaffold `motif`/`prop` (hero + detail slots). Interview: what it is + its load-bearing detail. Prompts cover hero + detail crops.

- [ ] **Step 5: `add-story`** — scaffold a `story` record (NOT via `add-entity`; a story is a StorySpec in `stories/`). Interview: logline, **spine** (obedient-servant | thesis | primer | testimony | ...; not assumed), refrain, register (defaults to `identity.register`; per-story override allowed), features, beats + per-beat provenance. Register as `status: "stub"` (spine + logline only) or `"full"`. Run a casting sweep over the beats' named entities and hand any not-yet-in-canon off to `add-character`/`add-setting`/etc. Write `stories/<id>.json`; `validate` green.

- [ ] **Step 6: `add-relation`** — write a typed relation into `canon/relations/` (`crossover-with` | `appears-in` | `derived-from` | `contradicts` | `supersedes`) with `from`/`rel`/`to`/`story`/`note`, so the graph stays queryable and contradictions are explicit records. `validate` green.

- [ ] **Step 7: Commit**

```bash
cd /Users/garysheng/Documents/github-repos/agenticstory
git add skills/add-setting/SKILL.md skills/add-visual-metaphor/SKILL.md skills/add-motif/SKILL.md skills/add-prop/SKILL.md skills/add-story/SKILL.md skills/add-relation/SKILL.md
git commit -m "feat(skills): add-setting/-visual-metaphor/-motif/-prop/-story/-relation"
```

---

## Task 4: Prove the flagship on AITX (test bed)

**Files:** creates canon in `/Users/garysheng/Documents/github-repos/aitx`.

Run the machinery end-to-end (authoring only) on a genuinely-needed AITX entity to prove it produces valid canon. Use a FICTIONAL test-of-the-machinery character to avoid needing a real interview + subject approval mid-build (jake-oshea is a real person and gets a proper `add-character` interview run later, with his blessing).

- [ ] **Step 1: Scaffold a fictional AITX character via the CLI**

```bash
cd /Users/garysheng/Documents/github-repos/agenticstory/engine
python3 -m agenticstory.cli add-entity /Users/garysheng/Documents/github-repos/aitx/universe character the-newcomer --name "The Newcomer" --origin origin-of-aitx
python3 -m agenticstory.cli validate /Users/garysheng/Documents/github-repos/aitx/universe | head -1
python3 -m agenticstory.cli lock-level /Users/garysheng/Documents/github-repos/aitx/universe the-newcomer
```
Expected: entity written, `validate [aitx]: OK`, `lock-level` prints `stub`.

- [ ] **Step 2: Scaffold an AITX setting**

```bash
python3 -m agenticstory.cli add-entity /Users/garysheng/Documents/github-repos/aitx/universe setting the-meetup-hall --name "The Meetup Hall"
python3 -m agenticstory.cli validate /Users/garysheng/Documents/github-repos/aitx/universe | head -1
python3 -m agenticstory.cli lock-level /Users/garysheng/Documents/github-repos/aitx/universe the-meetup-hall
```
Expected: written, `OK`, `stub` (unlocked contract).

- [ ] **Step 3: Confirm reference dirs + commit the AITX canon**

```bash
ls -d /Users/garysheng/Documents/github-repos/aitx/universe/reference/the-newcomer /Users/garysheng/Documents/github-repos/aitx/universe/reference/the-meetup-hall
cd /Users/garysheng/Documents/github-repos/aitx
git add universe/canon/entities/the-newcomer.json universe/canon/entities/the-meetup-hall.json universe/reference/the-newcomer universe/reference/the-meetup-hall
git commit -m "canon: scaffold the-newcomer + the-meetup-hall via add-entity (Phase C proof)"
```

(If Gary would rather not keep these test entities, delete them after the proof instead of committing. Default: keep, they are plausible AITX canon.)

---

## Verification (whole phase)

- [ ] Engine: `python3 -m unittest discover -s tests -p 'test_*.py'` → OK (all, incl. the new scaffold_entity test).
- [ ] `add-entity` produces a `validate`-green entity for each kind (character/setting/visual-metaphor/motif/prop) with `lock_level == "stub"`.
- [ ] Each `add-*/SKILL.md` exists with valid frontmatter (`name` + `description`) and a Procedure that (where relevant) runs casting-sweep, calls `add-entity`, writes prompts, and honors the subject-approval + sensitivity gates for real people.
- [ ] AITX still `validate`s green after the scaffolded entities.
- [ ] Back-compat: `nof-universe` unchanged (A=0/B=0/C=0); NoF `validate` its usual 2 pre-existing notes.
- [ ] No skill calls an image model (art is Phase D).

## Out of scope (Phase D+)

- `lock-references` (generate + readback + lock the matrix) — Phase D.
- Migrating the 9 NoF skills — Phase E.
- A real `add-character` interview run on jake-oshea (needs him + his blessing).
- Making requiredForRender auto-promote on lock (that lives in Phase D `lock-references`).
