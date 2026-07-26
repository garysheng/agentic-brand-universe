"""Deterministic entity scaffolding (SPEC v0.4 §12 reference matrix).

The `add-*` skills call this so authoring is tested machinery, not hand-written
JSON. A scaffolded entity validates green immediately with lock_level == "stub":
its reference-matrix slots are null and requiredForRender is empty until the art
step (lock-references) fills paths and promotes the required set.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import pathlib

from .matrix import matrix_for
from .model import SETTING_CONTRACT_FIELDS


def _digest(path) -> str | None:
    """Short content hash of a file, or None if it does not resolve.

    None is recorded rather than omitted: a reference that failed to resolve at
    approval time is a fact about the approval, and dropping it would make an
    unresolved input look like an input that was never wanted.
    """
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except Exception:
        return None


def recipe_sidecar_path(golden_path) -> pathlib.Path:
    """Where a golden's provenance lives: alongside it, as `<golden>.recipe.json`.

    A sidecar, not a field inside the entity, for three reasons. It travels with the
    asset file so a moved or copied golden keeps its provenance. It is git-diffable on
    its own. And it does not touch the `sheets[shot] = path` string contract that the
    compiler and resolver depend on.
    """
    p = pathlib.Path(golden_path)
    return p.with_name(p.name + ".recipe.json")


def freeze_recipe(golden_path, recipe: dict, root=None) -> dict:
    """Stamp a golden's provenance AT APPROVAL: what made it, and what it was made
    against, by exact bytes.

    This is what turns the golden library into an auditable eval set. An approval that
    records only a path cannot answer the one question the whole divergence loop rests
    on: what did the human actually approve, and against which inputs? Two things are
    frozen here that a bare recipe does not carry:

      * `goldenDigest` - the exact bytes the human blessed. A golden re-locked in place
        under the same filename changes these bytes; the approval was of the old ones.
      * `inputs[].digest` re-stamped NOW - the bytes each input had at approval. Later,
        `lint-universe` re-hashes those paths and flags a golden whose inputs have
        since moved, because an approval made against inputs that no longer exist is an
        approval that may no longer hold.

    `root` joins universe-relative input paths so the digests are taken from the real
    files, not from strings that only resolve in one working directory.
    """
    def resolve(p):
        if root and not pathlib.Path(p).is_absolute():
            return str(pathlib.Path(root) / p)
        return p
    raw_inputs = recipe.get("refs") or recipe.get("inputs") or []
    inputs = []
    for r in raw_inputs:
        p = r["path"] if isinstance(r, dict) else r
        inputs.append({"path": p, "digest": _digest(resolve(p))})
    return {
        "goldenDigest": _digest(resolve(golden_path)),
        "provider": recipe.get("provider") or recipe.get("model"),
        "prompt": recipe.get("prompt"),
        "specVersion": recipe.get("specVersion"),
        "inputs": inputs,
    }


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
            # SPEC v0.9: emptyPlates are people-free so a reference never bakes a face into a
            # room, which means nothing in them proves how BIG the room is. scalePlate is the
            # same room with anonymous scale figures; scale states the size in human terms and
            # is passed in every prompt like dressing (prose survives a re-render, a plate does not).
            "scalePlate": None,
            "map": "", "blocking": "", "dressing": "", "scale": "",
        }
        ent["prose"] = {"rules": ""}
    else:  # doctrine, beat, group
        ent["structured"] = {"sheets": {}, "requiredForRender": []}
        ent["prose"] = {"rules": ""}

    return ent


def lock_shot(entity: dict, shot: str, path: str, recipe: dict | None = None,
              root=None, look: str | None = None) -> dict:
    """Lock a generated reference shot into an entity (mutates + returns it).

    For sheet-matrixed kinds (character/prop/motif) this sets
    `structured.sheets[shot] = path` and recomputes `requiredForRender` to the
    kind's matrix-required shots that now have a path. This keeps `validate` green at
    every step (a required key always resolves) and promotes the entity to gate-real
    only once its required shots are locked. Non-matrixed kinds keep any existing
    requiredForRender untouched.

    When `recipe` is supplied, provenance is frozen alongside the golden as
    `<path>.recipe.json`. Locking IS the approval act, so it is the correct and only
    place to capture what the human blessed and what it was blessed against. A golden
    locked without a recipe is still a valid golden, but it is un-auditable: no
    divergence check can ever run against it, which `lint-universe` flags.
    """
    # Locking IS the approval act, so this is the only moment the record of WHO approved
    # it is guaranteed to be knowable. The scaffolder writes `lockedBy: "TODO-you"` and
    # nothing used to force it to be filled, so entities accumulated locked art with a
    # placeholder approver. Caught twice in one session (2026-07-25), the second time on a
    # motif created that same hour by the person who had just fixed the first one. Stamp
    # the date, which is always knowable, and say something loud about the name, which is not.
    # VALIDATE BEFORE MUTATING ANYTHING. The authority stamp below is a mutation, so
    # doing it first meant a REFUSED lock still moved `lockedOn` and printed an
    # approver warning for an operation that never happened.
    if look is not None:
        _looks = (entity.get("structured") or {}).get("altLooks") or {}
        if look not in _looks:
            raise ValueError(
                f"{entity.get('id')} has no altLook {look!r}. Author the look first "
                f"(add-character step 4b); creating it here would let a typo mint a "
                f"look that nothing selects and no read-back ever checks. "
                f"Known looks: {sorted(_looks) or 'none'}"
            )

    au = entity.setdefault("authority", {})
    if not au.get("lockedOn"):
        au["lockedOn"] = _dt.date.today().isoformat()
    if not au.get("lockedBy") or str(au.get("lockedBy")).startswith("TODO"):
        print(f"  WARNING: {entity.get('id')} is being locked with authority.lockedBy="
              f"{au.get('lockedBy')!r}. A golden with no recorded approver cannot be attributed. "
              f"Set it before this ships; `lint-universe` fails on it.")

    # AN ALT-LOOK'S ART LOCKS INTO THE LOOK, NOT THE DEFAULT MATRIX (v0.10).
    # Without this there was no verb at all for era/alt-look art: `altLooks` could
    # declare a different body but only `structured.sheets` could be locked, so the
    # only way to register an era plate was to hand-edit the entity JSON, which is
    # the hand-rolling this engine exists to remove. It deliberately does NOT touch
    # `requiredForRender`: that is the DEFAULT look's gate, and an era look must
    # never be able to satisfy or break it.
    if look is not None:
        looks = entity["structured"]["altLooks"]
        looks[look].setdefault("sheets", {})[shot] = path
        if recipe is not None:
            abspath = (str(pathlib.Path(root) / path)
                       if root and not pathlib.Path(path).is_absolute() else path)
            recipe_sidecar_path(abspath).write_text(
                json.dumps(freeze_recipe(path, recipe, root=root), indent=2,
                           sort_keys=True) + "\n")
        return entity

    kind = entity.get("kind", "")
    if kind in ("setting", "visual-metaphor"):
        # Settings/visual-metaphors are matrixed via their `contract`, NOT sheet keys
        # (see matrix.py and refs.resolve_setting). Writing them into structured.sheets
        # silently produced a parallel structure the render gate never reads, so a
        # locked setting still failed assert_story with no error. Fixed 2026-07-25.
        c = entity.setdefault("contract", {})
        # A setting needs BOTH: `contract` is the render GATE's checklist
        # (refs.resolve_setting) and `structured.sheets` is the RENDERER's
        # selector, which picks a plate by key per spread. Writing only one of
        # them leaves the entity half-usable: contract-only passes assert-story
        # and then crashes the compiler on KeyError 'structured' (hit live on
        # encounter-school, 2026-07-25), and sheets-only was the original bug.
        st = entity.setdefault("structured", {})
        st.setdefault("sheets", {})[shot] = path
        slot = {"scale-plate": "scalePlate"}.get(shot, shot)
        if slot in ("turnaround", "blueprint", "scalePlate"):
            c[slot] = path
        else:
            plates = c.setdefault("emptyPlates", [])
            if path not in plates:
                plates.append(path)
        # Promote to locked only when the WHOLE contract is satisfied, mirroring how
        # requiredForRender is recomputed for sheet-matrixed kinds. Partial art must
        # never open the gate.
        if all(
            (c.get(f) not in (None, "")) and not (f == "emptyPlates" and not c.get(f))
            for f in SETTING_CONTRACT_FIELDS
        ):
            entity["status"] = "locked"
    else:
        st = entity.setdefault("structured", {})
        sheets = st.setdefault("sheets", {})
        sheets[shot] = path
        m = matrix_for(kind)
        if m:
            required = m.get("required", [])
            st["requiredForRender"] = [k for k in required if sheets.get(k)]
    if recipe is not None:
        abspath = str(pathlib.Path(root) / path) if root and not pathlib.Path(path).is_absolute() else path
        recipe_sidecar_path(abspath).write_text(
            json.dumps(freeze_recipe(path, recipe, root=root), indent=2, sort_keys=True) + "\n")
    return entity
