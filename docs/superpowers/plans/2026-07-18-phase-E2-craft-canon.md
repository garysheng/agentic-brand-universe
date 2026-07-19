# Phase E2 — Craft-canon record type + extract NoF genres Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Steps use `- [ ]`.

**Goal:** Give craft-canon a typed home. Define a `CraftCanon` record type (engine + SPEC §13), then extract Nation of Fire's genres, spine, and register rules out of the `picture-book` skill's prose INTO `nof-universe/canon/craft/` records the future generic renderer reads. Parallel-safe: additive only, the live `picture-book` skill keeps its prose until Phase F.

**Architecture:** A `CraftCanon` is a typed record in a universe's `canon/craft/*.json`, loaded and validated by the engine alongside entities/relations/stories. Kinds: `spine` (a story's arc invariant), `genre` (a book type), `register-rule` (a universe-wide visual/narrative craft law). A story's `spine` field may reference a `spine` craft record id; a renderer reads the relevant `genre` + `register-rule` records. This is the "craft-canon is data, not skill prose" principle (SPEC §11) made concrete.

**Tech Stack:** Python 3 stdlib (engine), Markdown/JSON (records). Tests via `python3 -m unittest`.

## Global Constraints

- **Parent design:** `docs/superpowers/specs/2026-07-18-framework-skill-catalog-design.md` (Phase E2).
- **Additive + parallel-safe:** the engine change is additive (a new record collection; existing validate/assert unchanged). The `nof` plugin and its `picture-book` prose are NOT edited in E2 (the records are extracted FROM it, the source stays live until Phase F).
- **Faithful extraction:** each NoF craft record captures the rule's enforceable essence accurately, with an `origin` field naming the source (`picture-book rule N`). It is fine to reference the fuller prose (which still lives in `picture-book`); do not lose the load-bearing specifics.
- **Back-compat:** a universe with NO `canon/craft/` dir still validates exactly as before (the collection is optional).
- **Version:** bump to v0.4.1 (a minor additive record type); `SPEC_VERSION` and scaffold `conformsTo` move to `0.4.1`. (The engine scaffold test reads the constant, so safe.)
- **Voice:** no em dashes in committed prose or commit messages.

**Absolute paths:** framework `/Users/garysheng/Documents/github-repos/agenticstory`; engine `.../engine`; nof-universe `/Users/garysheng/Documents/github-repos/nation-of-fire/nof-universe`; picture-book source `/Users/garysheng/Documents/github-repos/garysheng-claude-plugins/plugins/nof/skills/picture-book/SKILL.md`.

---

## File Structure

- Modify: `engine/agenticstory/model.py` — add `CraftCanon` dataclass (from_dict + validate) + `CRAFT_KINDS`.
- Modify: `engine/agenticstory/store.py` — load `canon/craft/*.json` into `self.craft`; include in `validate_canon`.
- Modify: `engine/agenticstory/cli.py` — `list-craft <universe>` subcommand.
- Modify: `engine/agenticstory/__init__.py` — export `CraftCanon`; bump `SPEC_VERSION` to `0.4.1`.
- Modify: `engine/tests/test_engine.py` — tests: craft records load + validate; a bad kind fails; no-craft-dir still validates.
- Modify: `SPEC.md` — §13 Craft-canon records + header/changelog + glossary.
- Create: `nof-universe/canon/craft/*.json` — the extracted NoF records.

---

## Task 1: Engine — `CraftCanon` record type (TDD)

**Files:** modify `model.py`, `store.py`, `cli.py`, `__init__.py`, `tests/test_engine.py`.

**Interfaces:**
- Produces: `model.CraftCanon` (fields `id`, `kind`, `raw`; `from_dict`, `validate`), `model.CRAFT_KINDS = {"spine","genre","register-rule"}`; `CanonStore.craft: dict[str, CraftCanon]` loaded from `canon/craft/*.json`; `validate_canon` reports craft problems. CLI `list-craft <universe>` prints each craft record's id + kind + name.

- [ ] **Step 1: Write the failing test**

Add to `engine/tests/test_engine.py`:

```python
def test_craft_canon_loads_and_validates(self):
    import json, tempfile
    from pathlib import Path
    from agenticstory import CanonStore
    from agenticstory.model import CraftCanon
    d = Path(tempfile.mkdtemp())
    (d / "canon" / "entities").mkdir(parents=True)
    (d / "canon" / "relations").mkdir(); (d / "stories").mkdir()
    (d / "universe.json").write_text(json.dumps({"name": "t", "assetRoot": "."}))
    # no craft dir yet -> still validates
    store = CanonStore(d)
    self.assertEqual(store.validate_canon(), [])
    self.assertEqual(store.craft, {})
    # add a craft dir with a good and a bad record
    (d / "canon" / "craft").mkdir()
    (d / "canon" / "craft" / "obedient-servant.json").write_text(json.dumps(
        {"id": "obedient-servant", "kind": "spine", "name": "Obedient Servant",
         "summary": "the servant obeys and God acts", "rules": "...", "origin": "test"}))
    (d / "canon" / "craft" / "bad.json").write_text(json.dumps(
        {"id": "bad", "kind": "not-a-kind", "name": "Bad"}))
    store = CanonStore(d)
    self.assertIn("obedient-servant", store.craft)
    self.assertIsInstance(store.craft["obedient-servant"], CraftCanon)
    problems = store.validate_canon()
    self.assertTrue(any("bad" in p and "kind" in p for p in problems))
    # a valid-only store validates clean
    (d / "canon" / "craft" / "bad.json").unlink()
    self.assertEqual(CanonStore(d).validate_canon(), [])
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/garysheng/Documents/github-repos/agenticstory/engine && python3 -m unittest tests.test_engine -v 2>&1 | tail -6`
Expected: FAIL — `ImportError: cannot import name 'CraftCanon'`.

- [ ] **Step 3: Add `CraftCanon` to `model.py`**

Read the existing `Entity`/`Relation` dataclasses first to match the file's style, then add near them:

```python
CRAFT_KINDS = {"spine", "genre", "register-rule"}


@dataclass
class CraftCanon:
    """A typed craft-canon record: a spine, a genre, or a register-rule the
    renderer honors. Craft is data, not skill prose (SPEC §11, §13)."""
    id: str
    kind: str
    raw: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "CraftCanon":
        return CraftCanon(id=d.get("id", ""), kind=d.get("kind", ""), raw=d)

    def validate(self) -> list[str]:
        p: list[str] = []
        if not self.id:
            p.append("craft record missing 'id'")
        if self.kind not in CRAFT_KINDS:
            p.append(f"{self.id}: unknown craft kind '{self.kind}' (allowed: {sorted(CRAFT_KINDS)})")
        if not (self.raw.get("rules") or self.raw.get("summary")):
            p.append(f"{self.id}: craft record needs a 'rules' or 'summary'")
        return p
```

(Ensure `Any`, `dataclass`, `field` are already imported at the top of `model.py`; they are, used by Entity.)

- [ ] **Step 4: Load craft in `store.py`**

Read how `store.py` loads entities (a `self.entities` dict from `canon/entities/*.json`) and mirror it. Add a `self.craft: dict[str, CraftCanon] = {}` and a loader for `canon/craft/*.json` (guard: only if the dir exists). In `validate_canon`, after the entity loop, add:

```python
        for c in self.craft.values():
            problems += c.validate()
```

Import `CraftCanon` from `.model` where the other model classes are imported.

- [ ] **Step 5: Export + version bump in `__init__.py`**

Add `CraftCanon` to the `from .model import ...` line. Change `SPEC_VERSION = "0.4"` to `SPEC_VERSION = "0.4.1"`.

- [ ] **Step 6: Run to verify it passes**

Run: `cd /Users/garysheng/Documents/github-repos/agenticstory/engine && python3 -m unittest tests.test_engine -v 2>&1 | tail -4`
Expected: OK (new test + all prior; 23 total).

- [ ] **Step 7: Add `list-craft` CLI**

Register `lc = sub.add_parser("list-craft"); lc.add_argument("universe")` and dispatch:

```python
    if args.cmd == "list-craft":
        store = CanonStore(Path(args.universe))
        for c in sorted(store.craft.values(), key=lambda c: (c.kind, c.id)):
            print(f"{c.kind:14} {c.id:32} {c.raw.get('name','')}")
        return 0
```

(Adapt to the file's idiom.)

- [ ] **Step 8: Commit**

```bash
cd /Users/garysheng/Documents/github-repos/agenticstory
git add engine/agenticstory/model.py engine/agenticstory/store.py engine/agenticstory/cli.py engine/agenticstory/__init__.py engine/tests/test_engine.py
git commit -m "feat(engine): CraftCanon record type + list-craft (v0.4.1)"
```

---

## Task 2: SPEC §13 — Craft-canon records

**Files:** modify `SPEC.md`.

- [ ] **Step 1: Bump header + changelog.** Change `**v0.4 ...**` line to note v0.4.1, and add a changelog bullet: "v0.4.1: §13 Craft-canon records - a typed home (`canon/craft/*.json`, kinds spine|genre|register-rule) for the genres, spines, and register rules a renderer honors, so craft is data not skill prose (§11)."

- [ ] **Step 2: Add §13.** Insert `## 13. Craft-canon records (v0.4.1)` before `## 10. Glossary`:

```markdown
## 13. Craft-canon records (v0.4.1)

Craft-canon is data, not skill prose (SPEC §11). A universe's discovered craft lives as typed records
in `canon/craft/*.json`, loaded and validated by the engine:

- **spine** - a story's arc invariant (obedient-servant, thesis, primer, testimony, ...). A story's
  `spine` field names one. Craft-canon checks a story against ITS declared spine, never one assumed shape.
- **genre** - a book type with its own format canon (e.g. the expectant biography, the visualized
  epistle). A renderer reads the genre a property declares.
- **register-rule** - a universe-wide visual or narrative law (e.g. "gold belongs to God",
  "testimony over prediction", "awe not horror") the renderer honors on every unit.

Each record: `{ id, kind, name, summary, rules, origin }`. `rules` (or `summary`) is required; `origin`
records where a rule was discovered. The collection is OPTIONAL: a universe with no `canon/craft/`
validates unchanged. This is how a genre discovered making one book (SPEC §5, craft is discovered then
encoded) is paid for once and reused by every future property and universe.
```

- [ ] **Step 3: Add a glossary entry** for "Craft-canon record". Commit.

```bash
cd /Users/garysheng/Documents/github-repos/agenticstory
git add SPEC.md && git commit -m "spec: v0.4.1 - §13 craft-canon records"
```

---

## Task 3: Extract NoF's craft-canon into `nof-universe/canon/craft/`

**Files:** create records under `/Users/garysheng/Documents/github-repos/nation-of-fire/nof-universe/canon/craft/`.

Read the source (`.../plugins/nof/skills/picture-book/SKILL.md`) and extract each named craft rule faithfully into a record. Do NOT edit picture-book (parallel-safe). Create these records (id, kind):

- [ ] **Step 1: Spines** - `obedient-servant.json` (kind `spine`): NoF's default arc, the obedient servant obeys and God acts. Capture the arc shape from picture-book.
- [ ] **Step 2: Genres** - `expectant-biography.json`, `visualized-epistle.json`, `expectant-future-present-fable.json` (kind `genre`): extract the full format canon of each from picture-book rules 6b/6c/6d (the arc shape, the tense, the testimony-over-prediction handling, the closing-plate discipline). These are the load-bearing genre definitions; capture them accurately.
- [ ] **Step 3: Register-rules** - `gold-belongs-to-god.json`, `testimony-over-prediction.json`, `awe-not-horror.json` (kind `register-rule`): each a universe-wide law from picture-book. `origin` names the source rule.
- [ ] **Step 4: Validate + list.**

```bash
cd /Users/garysheng/Documents/github-repos/agenticstory/engine
python3 -m agenticstory.cli validate /Users/garysheng/Documents/github-repos/nation-of-fire/nof-universe | head -1
python3 -m agenticstory.cli list-craft /Users/garysheng/Documents/github-repos/nation-of-fire/nof-universe
```
Expected: `validate [nation-of-fire]: 2 problem(s)` (the SAME 2 pre-existing `readier-than-a-year-ago` notes, nothing new); `list-craft` prints the 7 records grouped by kind.

- [ ] **Step 5: Commit (in nof-universe).**

```bash
cd /Users/garysheng/Documents/github-repos/nation-of-fire/nof-universe
git add canon/craft
git commit -m "canon: extract craft-canon records (spines, genres, register-rules) from picture-book prose"
```

---

## Verification (whole phase)

- [ ] Engine: `python3 -m unittest discover -s tests -p 'test_*.py'` -> OK (23 tests).
- [ ] Back-compat: a universe with no `canon/craft/` validates unchanged. AITX (no craft dir) `validate [aitx]: OK`.
- [ ] nof-universe self-containment intact: `python3 scripts/verify_selfcontained.py` -> A=0/B=0/C=0. `validate` shows only the 2 pre-existing notes.
- [ ] `list-craft` on nof-universe prints 7 records (1 spine, 3 genres, 3 register-rules), each with a name + origin.
- [ ] Parallel-safe: the `nof` plugin and `picture-book` prose are untouched (`git -C .../garysheng-claude-plugins status` clean of nof edits).

## Out of scope (E3, F)

- Generalizing the renderers to READ these craft records (Phase E3) and proving a real book.
- Retiring the `nof` plugin / deleting the picture-book prose (Phase F, after E3 proves the generic path).
- Extracting entity-specific rules (the wisp, the dark council) - those are already entity records, not craft-canon.
