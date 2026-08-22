"""Deterministic entity scaffolding (SPEC v0.4 §12 reference matrix).

The `add-*` skills call this so authoring is tested machinery, not hand-written
JSON. A scaffolded entity validates green immediately with lock_level == "stub":
its reference-matrix slots are null and requiredForRender is empty until the art
step (shoot-references) fills paths and promotes the required set.
"""
from __future__ import annotations

import sys

import datetime as _dt
import hashlib
import json
import pathlib

from .matrix import matrix_for, known_shots_for
from .model import setting_contract_gaps


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
    states: list[str] | None = None,
) -> dict:
    """A schema-valid entity stub for `kind`. Raises ValueError on an unknown kind.

    - character/prop/motif: `structured.sheets` carries the kind's matrix keys as
      null slots; `requiredForRender` is [] (populated when art locks).
    - setting: an `unlocked` `contract` (refused until locked).
    - visual-metaphor: the same contract PLUS `states` (v0.31) — see below.
    - a non-empty `photo_stack` (character only) adds a `gated` `realPerson` block.

    `states` (visual-metaphor only) names the states the object is argued across.
    SPEC 12 defines this kind's matrix as "a locked master plus `state` plates", and
    until v0.31 there was no way to say either word: the scaffolder emitted a SETTING's
    room slots (`empty-c1`, `scale`), wrote `structured.houseRules` (a rule set for a
    BUILDING with rooms inside it), and wrote no `structured.sheets` at all, which is the
    one key the compiler resolves plates from. Every state, sheet key, pose selector and
    invariant of `the-shelter-he-held-up` was therefore hand-authored in a throwaway
    script, and the residue is visible across nation-of-fire: five visual-metaphors carry
    hand-written state blocks and their `prompts.md` files still hold orphan `empty-c1`
    and `scale` sections nobody will ever shoot.
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
            "sheets": {s: None for s in shots},   # null slots -> filled by shoot-references
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
        # SPEC v0.29: a ROOM is a setting that is `partOf` a building. Scaffolded as an
        # explicit null rather than omitted, because a field nobody can see is a field
        # nobody uses, and the failure this prevents is silent: a house modelled as ONE
        # setting has a single flat contract, so a per-room rule has nowhere to live and
        # every room gets read-back against the other rooms' rules. Leave it null for a
        # standalone place; set it to the parent's id for a room, and put the genuinely
        # building-wide rules in the PARENT's `structured.houseRules`.
        ent["partOf"] = None
        ent["contract"] = {
            "turnaround": None, "emptyPlates": [], "blueprint": None,
            # SPEC v0.9: emptyPlates are people-free so a reference never bakes a face into a
            # room, which means nothing in them proves how BIG the room is. scalePlate is the
            # same room with anonymous scale figures; scale states the size in human terms and
            # is passed in every prompt like dressing (prose survives a re-render, a plate does not).
            "scalePlate": None,
            # SPEC v0.19: blockingPlate is the SEATING CHART AS A PICTURE. `blocking` is
            # prose the model may paraphrase and `structured.seating` is a sentence, but
            # neither shows the model a geometry it can copy. This plate does: the room
            # with featureless mannequins in the LEGAL seat positions at correct relative
            # size. Advisory, so no existing setting un-locks; passed automatically by
            # compose-spread whenever the setting is cast.
            "blockingPlate": None,
            "map": "", "blocking": "", "dressing": "", "scale": "",
        }
        if kind == "visual-metaphor":
            # A VISUAL-METAPHOR IS A MASTER PLUS STATES, NOT A ROOM (v0.31).
            #
            # It shares the `contract` SHAPE with a setting because the anchor plate and
            # the per-view plates are the same two ideas, and it shares nothing else:
            # there are no fixed cameras, no seating, and no rooms nested inside it, so
            # `houseRules` and `partOf` are removed rather than scaffolded as fields an
            # author is invited to fill.
            ent.pop("partOf", None)
            sts = list(dict.fromkeys(states or []))
            # `states` is the ordered PLATE list, matching the shape both hand-authored
            # visual-metaphors in nation-of-fire converged on independently: the
            # code-drawn blueprint, the master, then each argued state.
            ent["contract"]["states"] = ["blueprint", "master"] + sts
            if sts:
                # SPEC v0.29's declared COUNT, which is what stops a three-state object
                # promoting itself to `locked` after the first state plate and then
                # improvising the other two, differently, at render time.
                ent["contract"]["emptyPlatesExpected"] = len(sts)
            ent["structured"] = {
                # THE KEY THE COMPILER ACTUALLY RESOLVES PLATES FROM. Scaffolding the
                # contract alone is the v0.30 `LOCKED-BUT-NO-SHEETS` defect built in at
                # birth: the entity looks finished, and `compose-spec` reports
                # `available: NONE` mid-book.
                "sheets": {s: None for s in ent["contract"]["states"]},
                "requiredForRender": [],
                "invariants": [],
                # ONE POSE PER STATE, so a spread can SELECT a state by name. A spread
                # naming a pose the entity does not declare is a hard refusal in the
                # compiler (`<id> has no render pose '<key>'`), so states without poses
                # are states no spread can ask for. Each pose passes its own plate and
                # nothing else; the `bake` sentence is the author's to write, and is
                # left absent rather than stubbed so no TODO text can reach a prompt.
                "render": {"poses": {s: {"sheets": [s]} for s in ["master"] + sts}},
            }
        else:
            # The other half of v0.29. Only these two keys are inherited by a child that
            # declares `partOf` this entity: `invariants` (which become the child's read-back
            # checks) and `dressing` (which reaches the model). Anything else here is REFUSED,
            # because `always` and `qa` read like they should work and were verified dead.
            # Leave empty unless this entity is a BUILDING with rooms nested inside it.
            ent.setdefault("structured", {})["houseRules"] = {"invariants": [], "dressing": ""}
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
    # THE FILE MUST ACTUALLY EXIST. Locking is the approval act, and approving art that
    # is not on disk mints a sheet pointing at nothing. Nothing downstream catches it:
    # `validate` and `assert-story` both pass, because they check that a required sheet has
    # a VALUE, not that the value resolves. The entity then looks locked and gate-real for
    # as long as no story happens to cast that pose.
    #
    # Earned 2026-08-21 (nation-of-fire, `the-wingman.coordinating`): the plate had been
    # moved aside for a re-roll that was then approved as-is, so the file was in /tmp when
    # the lock ran and when the commit that should have captured it ran. Canon carried a
    # dangling sheet for hours and it only surfaced when a spread finally cast the pose and
    # the compiler refused mid-batch.
    # ONLY when the path is actually resolvable. A relative path with no root cannot be
    # resolved to anywhere real, and checking it against the process's CWD would refuse
    # legitimate callers that lock symbolically (every unit test that builds an entity in
    # memory does exactly that). Resolvable means: absolute, or relative with a root.
    _abs = pathlib.Path(path)
    if not _abs.is_absolute():
        _abs = (pathlib.Path(root) / path) if root else None
    if _abs is not None and not _abs.exists():
        raise ValueError(
            f"refusing to lock {entity.get('id')}.{shot}: no file at {_abs}. Locking is the "
            f"approval act, so it cannot approve art that is not on disk. Nothing downstream "
            f"would catch this: validate and assert-story check that a required sheet has a "
            f"value, not that the value resolves, so the entity would look locked until a "
            f"story cast the pose. If the plate was moved aside for a re-roll, put it back "
            f"first."
        )

    if look is not None:
        _looks = (entity.get("structured") or {}).get("altLooks") or {}
        if look not in _looks:
            raise ValueError(
                f"{entity.get('id')} has no altLook {look!r}. Author the look first "
                f"(add-character step 4b); creating it here would let a typo mint a "
                f"look that nothing selects and no read-back ever checks. "
                f"Known looks: {sorted(_looks) or 'none'}"
            )

    # STORE THE PATH RELATIVE TO assetRoot, ALWAYS.
    # Every sheet in a canon record is assetRoot-relative, and self-containment
    # (SPEC §3a) depends on it: an absolute path pins the record to one machine's
    # home directory, so the repo stops resolving the moment anyone else clones it.
    # This took whatever the caller typed, and a CLI invocation naturally supplies
    # an absolute path, which then sat in `structured.sheets` beside eight relative
    # siblings (caught on gary-sheng-art `jesus`, 2026-07-27). Normalise here rather
    # than in the CLI, so every caller of lock_shot gets it.
    if root and pathlib.Path(path).is_absolute():
        try:
            path = str(pathlib.Path(path).resolve().relative_to(pathlib.Path(root).resolve()))
        except ValueError:
            raise ValueError(
                f"{path!r} is outside the universe root {root!r}. A locked golden must "
                f"live inside the repo, or the universe is not self-contained (SPEC 3a). "
                f"Copy the file in first, then lock it."
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
        # `scale` is an ALIAS for `scale-plate`, and it is load-bearing rather than a
        # convenience: the prompts.md skeleton this same module writes (see the slot list
        # in prompts_skeleton below) tells the author the shot is called `scale`, while
        # only `scale-plate` was mapped here. Following the framework's own scaffold
        # therefore filed the plate under emptyPlates and left contract.scalePlate null.
        # Earned 2026-08-02 on the-lit-pulpit, where it was diagnosed by hand and patched
        # with a throwaway script.
        # `seating` is the same defect a FOURTH time (2026-08-05, nation-of-fire
        # `russes-cadillac`). A seating chart IS the blocking plate for a vehicle or a
        # table: SPEC v0.19 calls it "the seating chart as a picture", and a book that
        # needs fixed places (who drives, who rides, who sits where) shoots it under
        # that name because that is what it is. Unmapped, it filed the chart into
        # `emptyPlates`, left `contract.blockingPlate` null, and the operator curated
        # the list by hand and declared a `sheetAliases` entry to get past lint.
        slot = {"scale-plate": "scalePlate", "scale": "scalePlate",
                "blocking-plate": "blockingPlate",
                "blocking": "blockingPlate",
                "seating": "blockingPlate", "seating-chart": "blockingPlate"}.get(shot, shot)
        # `master` IS a visual-metaphor's turnaround (v0.31). SPEC 12 defines the kind's
        # matrix as "a locked master plus `state` plates", so `master` is the anchor plate
        # this contract calls `turnaround` -- and it was absent from the map above, so
        # `abu lock-shot <u> <vm> master <path>` filed the anchor into `contract.emptyPlates`,
        # left `contract.turnaround` null, and therefore could never satisfy
        # `setting_contract_gaps`. The entity stayed `unlocked` after a complete, correct
        # shoot with no error anywhere, and the only way out was hand-editing the JSON.
        #
        # Same defect as the `scale` alias two lines up and the same cause: the vocabulary
        # SPEC and the scaffolder hand the author is not the vocabulary the locker accepts.
        # Earned 2026-08-03 on nation-of-fire `the-shelter-he-held-up` (What a Relief), where
        # all four plates were locked, `status` never flipped, and the JSON was hand-edited
        # to match its already-hand-edited sibling `the-broken-cisterns`.
        #
        # Scoped to the KIND rather than added to the shared map, because a `setting` has no
        # `master` in its matrix and silently promoting one to its turnaround would invent a
        # slot the spec does not give that kind.
        if kind == "visual-metaphor" and shot == "master":
            slot = "turnaround"
        if slot in ("turnaround", "blueprint", "scalePlate", "blockingPlate"):
            c[slot] = path
        else:
            # EVERY INSTANCE OF THIS DEFECT WAS A SILENCE, NOT A WRONG ANSWER (v0.34).
            # Four times now (`scale`, `blocking`, `master`, `seating`) an author locked a
            # plate under a reasonable name, the name was not in the map above, the plate
            # fell through to `emptyPlates`, the contract field stayed null, `status` never
            # flipped, and the ONLY way out was hand-editing the JSON. Each time the tool
            # reported success. The fix for instance N is a map entry; the fix for the CLASS
            # is that the fall-through stops being quiet.
            #
            # A warning rather than a refusal, deliberately: a populated camera plate under
            # a custom name (`frontglass`, `backseat`, `singleRuss` on nation-of-fire's
            # vehicles) is a legitimate use of this branch, and refusing would break shipped
            # universes. `empty`-prefixed names are the documented idiom and stay silent.
            if not shot.startswith("empty"):
                print(f"NOTE: {entity.get('id')}: '{shot}' is not a contract slot name, so it "
                      f"was filed under contract.emptyPlates. If this plate IS the "
                      f"turnaround / blueprint / scale plate / blocking plate, lock it under "
                      f"that name (or a known alias: scale, scale-plate, blocking, "
                      f"blocking-plate, seating, seating-chart, master) so the contract field "
                      f"is set and `status` can promote. If it is genuinely another plate, "
                      f"ignore this.", file=sys.stderr)
            plates = c.setdefault("emptyPlates", [])
            if path not in plates:
                plates.append(path)
        # Promote to locked only when the RENDER GATE would accept it, mirroring how
        # requiredForRender is recomputed for sheet-matrixed kinds. Partial art must
        # never open the gate.
        #
        # THE PROMOTER AND THE GATE MUST ASK THE SAME QUESTION (v0.29). This used to
        # require every SETTING_CONTRACT_FIELDS entry including the advisory `scalePlate`,
        # which `refs.resolve_setting` never checks and which SPEC 12 says is advisory. A
        # setting that legitimately must not carry a painted scale plate could therefore
        # never be promoted by this tool and had to be hand-flipped in the JSON, which is
        # the hand-editing this module exists to remove. `setting_contract_gaps` is now the
        # single definition, shared with the gate and with `Entity.is_locked_setting`.
        if not setting_contract_gaps(c):
            entity["status"] = "locked"
    else:
        st = entity.setdefault("structured", {})
        sheets = st.setdefault("sheets", {})
        sheets[shot] = path
        m = matrix_for(kind)
        if m:
            # NEVER LET A LOCK LOWER AN ENTITY'S OWN GATE (v0.24).
            #
            # This recomputed the gate from the KIND minimum alone, so any entity that
            # legitimately required MORE than its kind demanded was silently demoted on
            # its next lock. Proven on christofuturism's `north-star-cross`, a motif whose
            # required set was ["hero","detail","in-context"] because that entity's own
            # authority note records that one view of the mark reads as an equilateral
            # star and only three views prove it is a cross. Locking any new material
            # plate rewrote it to ["hero"], and the field that exists to rescue exactly
            # this case, `requiredForRenderOnLock`, REFUSED `in-context` because it is not
            # a matrix shot name. So the escape hatch was closed against the case it was
            # built for, and the entity guarding a filed trademark would have quietly
            # stopped guarding it.
            #
            # A lock is an act of ADDING art. It may raise a gate and must never lower
            # one, so anything the entity already required and still resolves is kept.
            required = required_set_for(entity, kind)
            prior = list(st.get("requiredForRender") or [])
            keys = list(dict.fromkeys(required + prior))
            st["requiredForRender"] = [k for k in keys if sheets.get(k)]
    if recipe is not None:
        abspath = str(pathlib.Path(root) / path) if root and not pathlib.Path(path).is_absolute() else path
        recipe_sidecar_path(abspath).write_text(
            json.dumps(freeze_recipe(path, recipe, root=root), indent=2, sort_keys=True) + "\n")
    return entity


def prompts_skeleton(entity: dict, register: dict | None = None) -> str:
    """The `reference/<id>/prompts.md` skeleton for a freshly scaffolded entity.

    Every `add-*` skill promises "ready-to-run generation prompts", and
    `shoot-references` reads this file as its input, but nothing wrote it: the
    step between scaffolding and shooting was hand-rolled in every universe.
    This emits the STRUCTURE (one section per matrix slot, the register-anchor
    preamble, the output path) and leaves the prose body to the author, because
    the engine can know which shots exist and cannot know what they depict.
    """
    eid, kind = entity["id"], entity.get("kind")
    register = register or {}
    anchor = register.get("anchor")
    poles = register.get("rejectedPoles") or []
    name = register.get("name") or "the universe register"

    out = [f"# {eid} — generation prompts", ""]
    if anchor:
        out.append(f"Register anchor (`{anchor}`) is passed FIRST as the style anchor on every "
                   f"shot. {name}" + (f"; never {', '.join(poles)}." if poles else "."))
    else:
        out.append("STOP: this universe has no `identity.register.anchor`. Lock the register "
                   "before shooting anything, or every shot will be off-style.")
    out += ["", "TODO(author): replace each body below. A prompt must (a) lead with the register "
            "anchor, (b) bake the rejected poles as negatives, (c) state the invariants that must "
            "not drift, and (d) contain no legible text unless the design calls for it.", ""]

    if kind == "visual-metaphor":
        # A VISUAL-METAPHOR'S SLOTS ARE ITS OWN (v0.31). This used to emit a SETTING's
        # room slots -- `empty-c1` and `scale`, for cameras and a room size an object
        # does not have -- so every visual-metaphor in the reference universe still
        # carries orphan sections nobody will ever shoot, and the states the object is
        # actually argued across had to be hand-written in a throwaway script.
        slots = list((entity.get("contract") or {}).get("states")
                     or (entity.get("structured", {}).get("sheets") or {})
                     or ["blueprint", "master"])
        out += [
            "### SHOOT ORDER",
            "",
            "1. **`blueprint` is CODE-DRAWN, not prompted. Build it BEFORE you shoot anything "
            "else**, with `abu elevation` or `abu massing` from a declarative spec in "
            "`canon/blueprints/`, so the geometry is a number rather than a guess. Once it is on "
            "disk with its recipe, `shoot-references` never regenerates it and passes it as "
            "conditioning to EVERY shot automatically (SPEC 12), and its section below is never "
            "used. The section is only the fallback for an object with no fixed geometry, and it "
            "is what you will get by default if you skip this step.",
            "2. **`master` is the seed** and the plate the human blesses. Shoot it with "
            "`--shoot-seed`, look at it, then `--bless-seed master`.",
            "3. **Every state chains off `master`, never off a sibling state.** Pass `--star`. "
            "States differ in light, weather, season, or the presence of something, and a "
            "reference image outranks any negative: chained serially, one state's night walks "
            "into the next state's noon.",
            "",
            "### WHAT MUST NOT DRIFT",
            "",
            "TODO(author): the object's geometry in NUMBERS, and what is identical in every "
            "state versus what each state changes. Put the same facts on the entity as "
            "`structured.invariants` so read-back can check them.",
            "",
            "Every heading below is a SHOT and every one above is level-3 prose. A level-2 "
            "heading that is not a shot is parsed as one and shot as garbage.",
            "",
        ]
    elif kind == "setting":
        slots = ["turnaround", "blueprint", "empty-c1", "scale"]
        out.append("Lock `turnaround` and `blueprint` FIRST, then chain each empty plate off them "
                   "so the geometry cannot drift between cameras. Add one `empty-<c>` section per "
                   "fixed camera. Empty plates carry NO people; `scale` is the same room with "
                   "anonymous figures for size.")
        out.append("")
    else:
        m = matrix_for(kind)
        slots = list((m or {}).get("shots") or entity.get("structured", {}).get("sheets", {}).keys())
        required = list((m or {}).get("required") or [])
        if required:
            out.append(f"REQUIRED before any render: {', '.join(f'`{s}`' for s in required)}. "
                       f"Shoot those first, then chain the rest off them so identity holds.")
            out.append("")

    for s in slots:
        out += [f"## {s}  -> reference/{eid}/{s}.png", "TODO(author): the prompt for this shot.", ""]
    return "\n".join(out)


def required_set_for(entity: dict, kind: str | None = None) -> list[str]:
    """The shots that must exist before this entity is renderable.

    SPEC v0.11: `structured.requiredForRenderOnLock` overrides the kind's matrix
    minimum for THIS entity. Authors in several universes independently invented
    this field to demand a stricter gate (a character whose face-3q carries a
    signature the front view cannot show); nothing read it, so the intent was
    silently dropped, and `lock_shot` then recomputed the gate from the kind
    default and clobbered the stricter set on the next lock. It may only ADD to
    the kind minimum: dropping below it would make "locked" mean less for that
    kind than for its peers.
    """
    kind = kind or entity.get("kind")
    m = matrix_for(kind) or {}
    base = list(m.get("required") or [])
    override = (entity.get("structured") or {}).get("requiredForRenderOnLock")
    if not override:
        return base
    # Validate names against matrix + OPTIONAL shots, not `shots` alone. `shots` is
    # the completeness list; a legitimate extra plate (character `face-neutral-color`)
    # must be nameable here without being forced into completeness, or the framework
    # has no way to express "this entity needs one more plate than its peers".
    # Validate against the kind's known shots PLUS the keys this entity actually
    # declares (v0.24). The typo check is the point of this validation and it stays, but
    # keying it on the kind matrix alone closed the hatch against its own use case: a
    # motif requiring an `in-context` plate it has genuinely locked was refused, because
    # `in-context` is not a motif matrix shot. A key with real art behind it is not a
    # typo, and refusing it forced hand-editing the entity JSON, which is precisely the
    # hand-rolling this module exists to remove.
    known = list(dict.fromkeys(
        known_shots_for(kind) + list(((entity.get("structured") or {}).get("sheets") or {}))))
    unknown = [s for s in override if known and s not in known]
    if unknown:
        raise ValueError(
            f"{entity.get('id')}: requiredForRenderOnLock names shot(s) that are neither "
            f"known for kind {kind} nor declared in this entity's sheets: {unknown}. "
            f"Known: {known}")
    return list(dict.fromkeys(list(override) + base))  # override first, kind minimum always kept
