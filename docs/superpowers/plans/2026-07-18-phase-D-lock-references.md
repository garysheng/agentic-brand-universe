# Phase D — lock-references (art: generate + read-back + lock) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Steps use `- [ ]`.

**Goal:** The art step that turns a scaffolded entity's null matrix slots into locked reference shots. `lock-references` generates each shot from the entity's `prompts.md` (passing `identity.register.anchor` + the photo stack + prior locked shots), reads each back against the entity's invariants (PASS/DEFECT), and locks passers into `structured.sheets`, promoting `requiredForRender` as the required shots lock. Under it, a tested engine helper (`lock_shot` + a `lock-shot` CLI) does the deterministic promotion. A generic `render-readback` skill is authored here because it is the quality gate `lock-references` depends on.

**Architecture:** `lock-references` is a skill (it drives an image model + agent-vision read-back, both non-deterministic). The deterministic part (set a sheet path, recompute `requiredForRender`) is `engine/agenticstory/authoring.py::lock_shot` + CLI `lock-shot`, tested. Generation uses the `chatgpt-images` skill (gpt-image-2, Gary's default). Real-person entities stay subject-approval `gated` even after art locks; blessing is a separate human act.

**Tech Stack:** Python 3 stdlib (engine), Markdown (skills). Image gen via the `chatgpt-images` skill. Tests via `python3 -m unittest`.

## Global Constraints

- **Parent design:** `docs/superpowers/specs/2026-07-18-framework-skill-catalog-design.md` (Phase D). Builds on v0.4 (matrix + register) and Phase C (scaffold_entity, add-* skills).
- **Framework only:** engine + skills land in `agenticstory`; universes receive only data (generated art + updated entity JSON in the target universe repo).
- **Promotion rule:** `lock_shot(entity, shot, path)` sets `structured.sheets[shot] = path` and recomputes `requiredForRender = [k for k in matrix.required if sheets[k]]`. This keeps `validate` green at every step (a required key always has a non-null path) and makes the entity gate-real only once its required shots are locked. A character's required set is `forward-fullbody` + `face-neutral`; full matrix is 8 shots.
- **Read-back is load-bearing:** a shot is locked ONLY after it passes read-back on every one of the entity's `structured.invariants` (crop-zoom each; DEFECT means regenerate from scratch, never edit-patch).
- **Register first:** every generation passes `identity.register.anchor` as the first reference and bakes `register.rejectedPoles` as negatives. If `register.anchor` is null (style not locked), warn and stop, pointing the operator at the start-universe style-lock step.
- **Real-person discipline:** build from the photo stack (never a painting-of-a-painting); honor the sensitive list; the entity stays `realPerson.approval.state: "gated"` after art. Do NOT flip approval to "approved" in this skill.
- **Idempotent:** re-running only regenerates shots that are missing or previously DEFECT; locked passers are left alone.
- **Back-compat:** additive; no change to existing engine behavior.
- **Voice:** no em dashes in committed prose or commit messages.

**Absolute paths:** framework `/Users/garysheng/Documents/github-repos/agenticstory`; engine `.../engine`.

---

## File Structure

- Modify: `engine/agenticstory/authoring.py` — add `lock_shot(entity, shot, path) -> dict`.
- Modify: `engine/agenticstory/cli.py` — `lock-shot <universe> <eid> <shot> <path>` subcommand.
- Modify: `engine/agenticstory/__init__.py` — export `lock_shot`.
- Modify: `engine/tests/test_engine.py` — test promotion + validate-green + lock_level transitions.
- Create: `skills/render-readback/SKILL.md` — the generic invariant read-back gate.
- Create: `skills/lock-references/SKILL.md` — the generate + read-back + lock loop.
- Modify: `README.md` (agenticstory) — list the two skills.

---

## Task 1: Engine — `lock_shot` + `lock-shot` CLI (TDD)

**Files:** modify `engine/agenticstory/authoring.py`, `cli.py`, `__init__.py`, `tests/test_engine.py`.

**Interfaces:**
- Produces: `authoring.lock_shot(entity: dict, shot: str, path: str) -> dict` (mutates + returns the entity: sets the sheet path, recomputes `requiredForRender` from the kind's matrix). CLI `lock-shot <universe> <eid> <shot> <path>` loads the entity JSON, applies `lock_shot`, writes it back, prints the new `lock_level`.

- [ ] **Step 1: Write the failing test**

Add to `engine/tests/test_engine.py`:

```python
def test_lock_shot_promotes_required_and_keeps_validate_green(self):
    import json, tempfile
    from pathlib import Path
    from agenticstory import CanonStore, scaffold_entity, lock_shot
    from agenticstory.model import Entity
    from agenticstory.refs import lock_level
    d = Path(tempfile.mkdtemp())
    (d / "canon" / "entities").mkdir(parents=True)
    (d / "canon" / "relations").mkdir(); (d / "stories").mkdir()
    (d / "universe.json").write_text(json.dumps({"name": "t", "assetRoot": "."}))
    art = d / "art"; art.mkdir()
    def png(name):
        p = art / name; p.write_bytes(b"x"); return f"art/{name}"
    ch = scaffold_entity("character", "hero", "Hero")
    # lock ONE required shot -> requiredForRender gains just that key, validate green, still partial
    lock_shot(ch, "forward-fullbody", png("ff.png"))
    self.assertEqual(ch["structured"]["requiredForRender"], ["forward-fullbody"])
    # lock the other required -> both required present
    lock_shot(ch, "face-neutral", png("fn.png"))
    self.assertEqual(set(ch["structured"]["requiredForRender"]), {"forward-fullbody", "face-neutral"})
    self.assertEqual(Entity.from_dict(ch).validate(), [])
    (d / "canon" / "entities" / "hero.json").write_text(json.dumps(ch))
    store = CanonStore(d)
    self.assertEqual(lock_level(store, "hero"), "partial")   # required locked, matrix not complete
    # lock the rest of the matrix -> locked
    for shot in ["face-3q", "expressions", "profile-left", "profile-right", "back", "signature-pose"]:
        lock_shot(ch, shot, png(f"{shot}.png"))
    (d / "canon" / "entities" / "hero.json").write_text(json.dumps(ch))
    store = CanonStore(d)
    self.assertEqual(lock_level(store, "hero"), "locked")
    self.assertEqual(Entity.from_dict(ch).validate(), [])
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/garysheng/Documents/github-repos/agenticstory/engine && python3 -m unittest tests.test_engine -v 2>&1 | tail -6`
Expected: FAIL — `ImportError: cannot import name 'lock_shot'`.

- [ ] **Step 3: Add `lock_shot` to `authoring.py`**

Append to `engine/agenticstory/authoring.py`:

```python
def lock_shot(entity: dict, shot: str, path: str) -> dict:
    """Lock a generated reference shot into an entity (mutates + returns it).

    Sets `structured.sheets[shot] = path` and recomputes `requiredForRender` to the
    kind's matrix-required shots that now have a path. This keeps `validate` green at
    every step (a required key always resolves) and promotes the entity to gate-real
    only once its required shots are locked. Non-matrixed kinds keep any existing
    requiredForRender untouched.
    """
    st = entity.setdefault("structured", {})
    sheets = st.setdefault("sheets", {})
    sheets[shot] = path
    m = matrix_for(entity.get("kind", ""))
    if m:
        required = m.get("required", [])
        st["requiredForRender"] = [k for k in required if sheets.get(k)]
    return entity
```

- [ ] **Step 4: Export from `__init__.py`**

Change the authoring import to: `from .authoring import scaffold_entity, lock_shot  # noqa: F401`.

- [ ] **Step 5: Run to verify it passes**

Run: `cd /Users/garysheng/Documents/github-repos/agenticstory/engine && python3 -m unittest tests.test_engine -v 2>&1 | tail -4`
Expected: OK (new test + all prior; 22 total).

- [ ] **Step 6: Add the `lock-shot` CLI subcommand**

Read `cli.py` to match its style, then register:

```python
    ls2 = sub.add_parser("lock-shot", help="lock a generated reference shot into an entity")
    ls2.add_argument("universe"); ls2.add_argument("eid"); ls2.add_argument("shot"); ls2.add_argument("path")
```

and dispatch:

```python
    if args.cmd == "lock-shot":
        from .authoring import lock_shot
        uni = Path(args.universe)
        entp = uni / "canon" / "entities" / f"{args.eid}.json"
        ent = json.loads(entp.read_text())
        lock_shot(ent, args.shot, args.path)
        entp.write_text(json.dumps(ent, indent=2) + "\n")
        print(f"locked {args.eid}.{args.shot} -> {args.path}  (lock_level: {refs.lock_level(CanonStore(uni), args.eid)})")
        return 0
```

(Adapt to the file's actual idiom; `json`, `Path`, `CanonStore`, `refs` are already imported.)

- [ ] **Step 7: Verify the CLI**

Run:
```bash
cd /Users/garysheng/Documents/github-repos/agenticstory/engine
T=$(mktemp -d)/x-universe && python3 -m agenticstory.cli init "$T" --name x >/dev/null
python3 -m agenticstory.cli add-entity "$T" character alex --name Alex >/dev/null
mkdir -p "$T/reference/alex"; : > "$T/reference/alex/forward-fullbody.png"; : > "$T/reference/alex/face-neutral.png"
python3 -m agenticstory.cli lock-shot "$T" alex forward-fullbody reference/alex/forward-fullbody.png
python3 -m agenticstory.cli lock-shot "$T" alex face-neutral reference/alex/face-neutral.png
python3 -m agenticstory.cli validate "$T" | head -1
python3 -m agenticstory.cli lock-level "$T" alex
rm -rf "$(dirname "$T")"
```
Expected: two `locked alex.<shot> ...` lines (the second printing `lock_level: partial`), `validate ... OK`, final `lock-level` prints `partial`.

- [ ] **Step 8: Commit**

```bash
cd /Users/garysheng/Documents/github-repos/agenticstory
git add engine/agenticstory/authoring.py engine/agenticstory/cli.py engine/agenticstory/__init__.py engine/tests/test_engine.py
git commit -m "feat(engine): lock_shot + lock-shot CLI (promote requiredForRender on lock)"
```

---

## Task 2: `render-readback` skill (the invariant gate)

**Files:** Create `skills/render-readback/SKILL.md`.

- [ ] **Step 1: Write the skill**

Create `skills/render-readback/SKILL.md`:

```markdown
---
name: render-readback
description: After EVERY render in an Agentic Story universe, read the image back and crop-zoom each of the in-frame entity's invariants, returning a per-invariant PASS or DEFECT verdict. Any DEFECT means regenerate the image FROM SCRATCH (never stack an edit pass). Use immediately after each generated image, before accepting or locking it. Generic and universe-parameterized: the invariants come from the entity's `structured.invariants`.
---

# Render Read-back

The quality gate that catches a defective render before it ships or locks. A render that looks fine at thumbnail can be wrong at the invariant level (a lens that should not be there, a missing patch, a wrong pendant). Read-back forces a per-invariant check.

## Procedure
1. **Load the entity's invariants.** From `canon/entities/<id>.json` read `structured.invariants` (the load-bearing identity rules). If the entity has none, there is nothing to check and the render passes trivially.
2. **Read the image back.** Open the just-generated image. For EACH invariant, crop-zoom the relevant region (the face for a face rule, the chest for a patch rule, the feet for a shoe rule) and judge it directly against the invariant. Do not judge from the thumbnail or from memory of the prompt.
3. **Verdict per invariant.** PASS (the invariant holds) or DEFECT (it does not), with a one-line reason on any DEFECT.
4. **Act on the result.** All PASS: the render is accepted. Any DEFECT: regenerate the image FROM SCRATCH with the defect named as an explicit negative. Never stack an edit pass on a defective render (it compounds artifacts).

## Not this skill
- Generating the image (that is the caller, e.g. `lock-references` or a renderer).
- Locking the passed shot into canon (that is `lock-references` / the renderer).
```

- [ ] **Step 2: Commit**

```bash
cd /Users/garysheng/Documents/github-repos/agenticstory
git add skills/render-readback/SKILL.md
git commit -m "feat(skill): render-readback (per-invariant PASS/DEFECT gate)"
```

---

## Task 3: `lock-references` skill (generate + read-back + lock)

**Files:** Create `skills/lock-references/SKILL.md`.

- [ ] **Step 1: Write the skill**

Create `skills/lock-references/SKILL.md`:

```markdown
---
name: lock-references
description: Generate and lock an entity's reference matrix in an Agentic Story universe. For each unlocked or DEFECT matrix slot, generate the shot from the entity's `reference/<id>/prompts.md` (passing `identity.register.anchor` first, plus the photo stack for a real person and any already-locked shots for identity consistency), read it back against the entity's invariants, and lock passers via `agenticstory lock-shot`. Idempotent. Real-person entities stay subject-approval gated after art. Use after `add-*` has scaffolded an entity, to give it its art.
---

# Lock References

Turn a scaffolded entity's null matrix slots into locked reference shots. This is the art step: `add-character` (and siblings) leave an entity at `lock_level: stub` with a `prompts.md`; this skill generates, reads back, and locks until the entity is `locked` (or at least `partial`, once its required shots pass).

## Inputs
- The target universe (a path with `universe.json`) and the entity id.
- Read `identity.register` (anchor + rejectedPoles). If `register.anchor` is null, STOP: the universe's style is not locked. Point the operator at the start-universe style-lock step and do not generate.

## Procedure
1. **Resolve the work.** Read `canon/entities/<id>.json` (its kind, matrix, invariants, and for a real person the `realPerson` photo stack + sensitive list) and `reference/<id>/prompts.md`. Run `agenticstory lock-level <universe> <id>` to see what remains.
2. **For each shot that is missing or was a DEFECT** (skip already-locked passers, so re-runs are cheap):
   a. **Generate** via the `chatgpt-images` skill (gpt-image-2): pass `identity.register.anchor` as the FIRST input image; bake `register.rejectedPoles` as negatives; for a real person pass the photo stack (build from real photos, never a painting-of-a-painting) and honor the sensitive list; pass any already-locked shots of this entity so the face/build stays consistent; use the shot's prompt block from `prompts.md`. Write to `reference/<id>/<shot>.png`.
   b. **Read back** with `render-readback`: crop-zoom each of the entity's invariants, PASS/DEFECT. On any DEFECT, regenerate that shot FROM SCRATCH (never an edit pass), naming the defect as an explicit negative.
   c. **Lock the passer:** `python3 -m agenticstory.cli lock-shot <universe> <id> <shot> reference/<id>/<shot>.png`. This sets the sheet path and promotes `requiredForRender` as the required shots lock.
3. **Verify + commit.** `agenticstory validate <universe>` stays green. `lock-level` should reach `partial` once the required shots pass and `locked` once the full matrix passes. Commit the generated art + the updated entity JSON.

## Gates honored
- **Register-first:** every generation leads with the universe style anchor; no anchor means stop.
- **Read-back:** no shot locks without passing every invariant; DEFECT means regenerate from scratch.
- **Subject-approval:** a real person stays `realPerson.approval.state: "gated"` after art. This skill NEVER flips it to "approved"; that is the subject's own blessing, recorded separately.
- **Sensitivity:** the sensitive list is honored on every real-person render.
- **Idempotent:** locked passers are never regenerated.

## Not this skill
- Authoring the entity or its prompts (that is the `add-*` skills).
- Rendering a story's spreads (that is a renderer).
```

- [ ] **Step 2: Commit**

```bash
cd /Users/garysheng/Documents/github-repos/agenticstory
git add skills/lock-references/SKILL.md
git commit -m "feat(skill): lock-references (generate + read-back + lock the matrix)"
```

---

## Task 4: Verify the lock mechanics + skills (no image gen)

`lock-references` end-to-end needs an image model and (for real people) a subject; a full art run happens when Gary runs it on a real character. This task verifies the deterministic mechanics + skill presence.

- [ ] **Step 1: Engine suite green**

Run: `cd /Users/garysheng/Documents/github-repos/agenticstory/engine && python3 -m unittest discover -s tests -p 'test_*.py' 2>&1 | tail -2`
Expected: OK (22 tests).

- [ ] **Step 2: Full lock cycle with dummy files reaches `locked`**

Run:
```bash
cd /Users/garysheng/Documents/github-repos/agenticstory/engine
T=$(mktemp -d)/x-universe && python3 -m agenticstory.cli init "$T" --name x >/dev/null
python3 -m agenticstory.cli add-entity "$T" character mia --name Mia >/dev/null
mkdir -p "$T/reference/mia"
for s in face-neutral face-3q expressions forward-fullbody profile-left profile-right back signature-pose; do
  : > "$T/reference/mia/$s.png"
  python3 -m agenticstory.cli lock-shot "$T" mia "$s" "reference/mia/$s.png" >/dev/null
done
python3 -m agenticstory.cli validate "$T" | head -1
echo -n "final lock-level: "; python3 -m agenticstory.cli lock-level "$T" mia
rm -rf "$(dirname "$T")"
```
Expected: `validate ... OK`; `final lock-level: locked`.

- [ ] **Step 3: Skills present with valid frontmatter**

Run: `cd /Users/garysheng/Documents/github-repos/agenticstory && for s in render-readback lock-references; do head -3 skills/$s/SKILL.md | grep -q "^name: $s" && echo "  $s OK" || echo "  $s BAD"; done`
Expected: both OK.

- [ ] **Step 4: No universe hardcodes**

Run: `grep -il "nation of fire\|nof-universe\|\baitx\b" skills/render-readback/SKILL.md skills/lock-references/SKILL.md && echo "HARDCODE" || echo "  clean (generic)"`
Expected: clean.

- [ ] **Step 5: Back-compat**

Run: `cd /Users/garysheng/Documents/github-repos/nation-of-fire/nof-universe && python3 scripts/verify_selfcontained.py 2>&1 | grep -E '^A\.|^B\.|^C\.'; rm -f scripts/moved_by_book.json; rm -rf scripts/__pycache__`
Expected: A=0, B=0, C=0.

## Out of scope (Phase E+)

- Migrating the 9 NoF skills (Phase E) and retiring the NoF plugin (Phase F). Note: this phase authored a generic `render-readback`, so Phase E's gate work is now `canon-resolve`, `casting-sweep`, `voice-gate` (three, not four) plus retiring NoF's duplicate readback.
- A real art-generation run of `lock-references` on an actual character (needs the image model + a real subject + blessing).
- Flipping a real person's approval to "approved" (a human blessing act, never automated).
