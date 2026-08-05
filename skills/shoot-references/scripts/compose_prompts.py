#!/usr/bin/env python3
"""compose_prompts.py — write a NEW entity's prompts.md bodies FROM ITS OWN CANON.

THE HOLE THIS FILLS. `add-entity` scaffolds every shot body as `TODO(author)`, and
`chain_matrix.py` correctly REFUSES to shoot while any body still says that: a
prompt that lives only in a throwaway script is gone when the session ends, so the
art has no recorded intent and can never be reproduced. Both halves are right.

What was missing is the verb in between. `backfill_prompts.py` is the repair verb
for art that ALREADY EXISTS (it reads each plate's recipe), so it can do nothing
for an entity that has no art yet — which is every entity anyone ever adds. The
result is that every single new entity forces a human or an agent to hand-type
several near-identical multi-paragraph prompts, and each one is a fresh chance to
type an invariant slightly differently from the one the read-back will check
against. That is the actual failure: not the typing, the DIVERGENCE.

So this composes each body from the entity JSON itself:

    SHOT     <- the shot's framing (face plates get a head-and-shoulders framing)
    WHO      <- structured.render.always            (verbatim)
    POSE     <- structured.render.poses[<pose>].bake (verbatim)
    RULES    <- structured.invariants                (verbatim, one per line)

Nothing here is invented. A prompt composed this way CANNOT disagree with the
invariants the entity will be judged against, because it is the same strings.

Three rules it will not break, matching backfill_prompts.py:

  1. **It never overwrites an authored body.** A shot already present in
     prompts.md is left exactly as it is, whatever it says.
  2. **It never invents.** A pose that is not in the entity, or a sheet key that
     is not in structured.sheets, is an error and not a guess.
  3. **It writes the register line and the shot's target path** the way
     chain_matrix expects to read them, including the optional `(WxH)` size.

The framework RE-ADDS the register style line, the same-subject clause and the
negatives block on every shoot, so those are deliberately NOT written here; see
FRAMEWORK_OWNED in backfill_prompts.py for the matching list.

  python3 compose_prompts.py <universe> <entity-id> <shot>[=<pose>][:WxH] ...
  python3 compose_prompts.py <universe> <entity-id> --all      # every sheet key
  python3 compose_prompts.py <universe> <entity-id> ... --dry-run

`--all` maps each sheet key to the pose of the same name when one exists, which is
the convention every kind already follows, and falls back to the neutral framing.

Earned 2026-08-04 on nation-of-fire/learning-serpent-wisdom, where three new
entities (esther-hadassah, abraham-lincoln, and a youth era for daniel-of-babylon)
each needed this and it was hand-rolled in the book's scratchpad, which is exactly
the script that would have rotted.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _abu_root(start=None):
    """The ABU root, found by walking UP for a marker instead of counting parents.

    A fixed `parents[N]` encodes one directory layout, and this runs from at least two
    (a git clone and a plugin cache under ~/.claude/plugins). Same walker as
    `chain_matrix`; `test_installable` fails the suite on a fixed-depth lookup."""
    p = Path(start or __file__).resolve()
    for c in [p, *p.parents]:
        if (c / "engine" / "agenticstory").is_dir():
            return c
    raise SystemExit(
        "abu: cannot locate the ABU root from " + str(p) + ".\n"
        "  Looked upward for engine/agenticstory. If ABU was installed as a plugin,\n"
        "  reinstall it: /plugin marketplace add garysheng/agentic-brand-universe")


def _engine_on_path():
    eng = str(_abu_root() / "engine")
    if eng not in sys.path:
        sys.path.insert(0, eng)
    return eng


FACE_KEYS = {"face", "face-neutral", "portrait", "head"}

FACE_FRAMING = ("Head and shoulders only, close, three-quarter view, face fully lit and "
                "completely legible.")
BODY_FRAMING = ("Full body, standing, head to feet, three-quarter view, filling the frame "
                "vertically.")
NEUTRAL_POSE = "Calm neutral expression, mouth closed, looking slightly off camera."

PREFIX = """A single {kind} reference plate for a picture-book universe. ONE image only, no panels.

Rendered in the style of the FIRST reference image, which is a STYLE ANCHOR ONLY and whose contents must never be drawn.

SHOT: {shot}

WHO THEY ARE: {always}

POSE: {pose}

THESE RULES ARE BINDING AND EVERY ONE MUST HOLD:
{rules}

BACKGROUND: a plain soft warm neutral studio field, gently graded, completely empty.

ONE single image only: no panels, no grid, no contact sheet, no multiple views. No stray or invented lettering anywhere."""

# A SETTING OR VISUAL-METAPHOR IS NOT A PERSON, and composing it from the character
# template produced a prompt that asked for "Full body, standing, head to feet" and a
# "plain soft warm neutral studio field" for a stone wall on a mound (SPEC v0.34).
# Both are wrong and the second is dangerous: `warm` in a register that already pulls
# every light toward amber, injected into an entity whose central invariant is that it
# carries no gold anywhere. Earned 2026-08-05 on nation-of-fire's `the-stronghold`.
PLACE_PREFIX = """A single {kind} reference plate for a picture-book universe. ONE image only, no panels.

Rendered in the style of the FIRST reference image, which is a STYLE ANCHOR ONLY and whose contents must never be drawn.

WHAT THIS IS: {always}

THIS PLATE: {pose}

THESE RULES ARE BINDING AND EVERY ONE MUST HOLD:
{rules}

ONE single continuous image of ONE scene: no panels, no grid, no contact sheet, no multiple views, no before-and-after. No stray or invented lettering anywhere."""

CONTRACT_SHAPED = {"setting", "visual-metaphor"}
TODO_MARKER = "TODO(author)"

HEADER = """# {eid} — generation prompts

Register anchor is passed FIRST as the style anchor on every shot; the shooter adds the register
line, the same-subject clause and the negatives block itself, so they are not repeated below.

REQUIRED before any render: {req}. Shoot those first, then chain the rest off them so identity holds.
"""


def _entity(universe: Path, eid: str) -> dict:
    p = universe / "canon" / "entities" / f"{eid}.json"
    if not p.exists():
        sys.exit(f"no such entity: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def compose_body(ent: dict, shot: str, pose_id: str | None) -> str:
    s = ent.get("structured", {})
    render = s.get("render", {}) or {}
    always = (render.get("always") or "").strip()
    if not always:
        sys.exit(f"{ent['id']}: structured.render.always is empty. Fill it before composing "
                 f"prompts; it is the sentence that actually steers the model, and an entity "
                 f"without it silently loses its prompt-craft on every render.")
    if pose_id:
        poses = render.get("poses", {}) or {}
        if pose_id not in poses:
            sys.exit(f"{ent['id']}: no pose {pose_id!r}. Declared: {sorted(poses)}")
        pose = (poses[pose_id].get("bake") or "").strip() or NEUTRAL_POSE
        framing = BODY_FRAMING
    else:
        pose = NEUTRAL_POSE
        framing = FACE_FRAMING if shot in FACE_KEYS else BODY_FRAMING
    invs = s.get("invariants", []) or []
    if not invs:
        sys.exit(f"{ent['id']}: no invariants. Read-back has nothing to check and the prompt "
                 f"has nothing binding to state. Fill structured.invariants first.")
    kind = ent.get("kind", "character")
    rules = "\n".join("- " + i for i in invs)
    if kind in CONTRACT_SHAPED:
        # A place has no body and no expression, so it takes neither the framing line
        # nor the studio-field background. Its pose bake already says what the plate is.
        return PLACE_PREFIX.format(kind=kind, always=always, pose=pose, rules=rules)
    return PREFIX.format(kind=kind, shot=framing, always=always,
                         pose=pose, rules=rules)


def main() -> int:
    ap = argparse.ArgumentParser(prog="compose_prompts")
    ap.add_argument("universe")
    ap.add_argument("entity")
    ap.add_argument("shots", nargs="*", metavar="SHOT[=POSE][:WxH]")
    ap.add_argument("--all", action="store_true",
                    help="compose every key in structured.sheets, mapping each to the pose of "
                         "the same name when one exists")
    ap.add_argument("--dry-run", action="store_true", help="report and write nothing")
    a = ap.parse_args()

    universe = Path(a.universe).expanduser()
    ent = _entity(universe, a.entity)
    sheets = (ent.get("structured", {}) or {}).get("sheets", {}) or {}
    poses = ((ent.get("structured", {}) or {}).get("render", {}) or {}).get("poses", {}) or {}

    specs: list[tuple[str, str | None, str | None]] = []
    if a.all:
        for key in sheets:
            specs.append((key, key if key in poses else None, None))
    for raw in a.shots:
        shot, _, rest = raw.partition("=")
        pose_id, _, size = rest.partition(":")
        specs.append((shot, pose_id or None, size or None))
    if not specs:
        sys.exit("nothing to compose: pass shot names or --all")

    _engine_on_path()
    from agenticstory.refs import entity_ref_dir
    refdir_name = entity_ref_dir(ent, a.entity)
    path = universe / "reference" / refdir_name / "prompts.md"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""

    # A `TODO(author)` STUB IS NOT AUTHORED (SPEC v0.34). `add-entity` scaffolds
    # prompts.md with a heading per shot and a TODO body, so treating "heading present"
    # as "a human wrote this" made the composer a no-op on exactly the file it exists to
    # fill, and the operator then wrote the prompts in a throwaway script instead.
    # Earned 2026-08-05 on nation-of-fire's `the-stronghold`.
    present, stubs = set(), []
    for block in existing.split("\n## ")[1:]:
        name = block.split()[0] if block.split() else ""
        if not name:
            continue
        (present.add(name) if TODO_MARKER not in block else stubs.append(name))

    # A recomposed stub REPLACES its section. Appending beside it would leave two
    # `## <shot>` headings for one shot, and `chain_matrix` refuses a prompts.md whose
    # headings do not match the declared sheets one-for-one.
    if stubs:
        head, *blocks = existing.split("\n## ")
        existing = "\n".join([head] + ["## " + b.rstrip() for b in blocks
                                        if (b.split()[0] if b.split() else "") not in stubs])

    out: list[str] = []
    if existing.strip():
        out.append(existing.rstrip() + "\n")
    else:
        req = (ent.get("structured", {}) or {}).get("requiredForRender") or list(sheets)[:1]
        out.append(HEADER.format(eid=a.entity, req=", ".join(f"`{r}`" for r in req) or "the seed"))

    kind = ent.get("kind", "character")
    wrote, skipped, code_drawn = [], [], []
    for shot, pose_id, size in specs:
        if shot not in sheets:
            sys.exit(f"{a.entity}: {shot!r} is not in structured.sheets. Declared: {sorted(sheets)}. "
                     f"Add the sheet key in the same edit as the pose, or the compiler hard-exits "
                     f"on a pose naming a sheet that does not exist.")
        if shot in present:
            skipped.append(shot)
            continue
        # A CODE-DRAWN PLATE IS NOT PROMPTED. A blueprint or scale plate rendered by
        # `abu massing`/`abu elevation` is deterministic art; composing a prompt for it
        # invites someone to overwrite computed geometry with a guess.
        recipe = universe / "reference" / refdir_name / f"{shot}.png.recipe.json"
        if recipe.exists():
            try:
                r = json.loads(recipe.read_text(encoding="utf-8"))
            except Exception:
                r = {}
            if r.get("deterministic") or str(r.get("generator") or "").startswith("agenticstory"):
                code_drawn.append(shot)
                continue
        if not size:
            # A SITE IS LANDSCAPE AND A BODY IS PORTRAIT. One portrait default
            # letterboxed every wall, room and vista into a tall canvas.
            size = ("1024x1024" if shot in FACE_KEYS
                    else "1536x1024" if kind in CONTRACT_SHAPED else "1024x1536")
        # A SCAFFOLDED SHEET IS `null`, which is the CORRECT state before its art
        # exists; emitting the literal string None as the target taught the file to
        # point nowhere. Fall back to the conventional path the shooter will write.
        target = sheets[shot] or f"reference/{refdir_name}/{shot}.png"
        out.append(f"\n## {shot} ({size})  -> {target}\n{compose_body(ent, shot, pose_id)}\n")
        wrote.append(shot)

    if code_drawn:
        print(f"  code-drawn, not composed (deterministic art): {', '.join(code_drawn)}")
    if a.dry_run:
        print(f"[dry-run] would write {len(wrote)}: {wrote or '-'}")
        print(f"[dry-run] would leave authored/existing alone: {skipped or '-'}")
        return 0

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out), encoding="utf-8")
    print(f"composed {len(wrote)} shot prompt(s) -> {path}")
    if wrote:
        print("  " + ", ".join(wrote))
    if skipped:
        print(f"  left alone (already present, a human's words always win): {', '.join(skipped)}")
    print("  Read them before shooting. Every sentence came from the entity, which means an "
          "invariant that is wrong here is wrong in canon.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
