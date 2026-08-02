"""
Agentic Brand Universe — load-bearing references.

The layer that makes a reference load-bearing: an entity's asset, or a story's
setting, either resolves to a real file on disk or it is a HARD problem. This is
the universe-agnostic generalization of Nation of Fire's resolve_gabr.py.

assert_story() is THE pre-render gate: no renderer may generate a unit whose
assertions have not passed.
"""
from __future__ import annotations

from pathlib import Path

from .store import CanonStore
from .model import (Entity, SETTING_GATE_FILE_FIELDS, setting_contract_gaps,
                    sheet_parts)
from .matrix import matrix_for


IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp")


def expand_ref(root: Path, p: str) -> list[str]:
    """Resolve one ref path to a LIST of on-disk image files.

    A path may be absolute, universe-relative, or relative to the universe's PARENT
    (cross-repo anchors live beside the universe). **A DIRECTORY expands to the image
    files directly inside it, sorted**, which is the form SPEC §12 calls idiomatic for a
    `realPerson.photoStack` (`["reference/<id>/photos"]`).

    Raises `FileNotFoundError` on a path that does not resolve, and on a directory that
    holds no images. A ref that silently resolves to nothing is a silent downgrade to
    "invent it from prose", which is the failure the whole refs layer exists to stop.
    """
    cand = Path(p)
    tries = [cand] if cand.is_absolute() else [root / p, root.parent / p, cand]
    for t in tries:
        if t.exists():
            if t.is_dir():
                imgs = sorted(str(f.resolve()) for f in t.iterdir()
                              if f.suffix.lower() in IMG_EXTS)
                if not imgs:
                    raise FileNotFoundError(f"ref directory has no images: {p}")
                return imgs
            return [str(t.resolve())]
    raise FileNotFoundError(f"ref does not resolve on disk: {p}")


def photo_stack(entity_raw: dict, root: Path) -> list[str]:
    """A real person's photographs: EXPANDED first, then capped by `realPerson.photoLimit`.

    THE ONE implementation of the rule for the whole framework (v0.21). It existed twice
    before, and only one copy was right: `compose-spread`'s assembler expanded directories
    and applied the cap after expansion, while `shoot-references` REFUSED a directory
    outright with "is a DIRECTORY, not an image" and never read `photoLimit` at all. So the
    form the SPEC calls idiomatic rendered a book fine and could not shoot the matrix that
    book renders from, and an entity that declared a ceiling had it honored at render time
    and ignored at shoot time. Earned 2026-08-01 on christofuturism `gary`.

    The cap applies AFTER expansion, deliberately: a one-entry directory stack sliced
    before expansion sails past any ceiling, which is the defect SPEC v0.17 records.

    A STRING `photoStack` is treated as one path rather than iterated character by
    character, which is the authoring mistake the SPEC already records.
    """
    rp = entity_raw.get("realPerson") or {}
    stack = rp.get("photoStack")
    if not stack:
        return []
    if isinstance(stack, str):
        stack = [stack]
    out: list[str] = []
    for entry in stack:
        for q in expand_ref(root, entry):
            if q not in out:
                out.append(q)
    limit = rp.get("photoLimit")
    if isinstance(limit, int) and limit >= 0:
        out = out[:limit]
    return out


def resolve_entity_assets(store: CanonStore, eid: str) -> tuple[dict[str, str], list[str]]:
    """Return (resolved {key: abspath}, missing[]) for an entity's REQUIRED sheets."""
    e = store.entity(eid)
    if e is None:
        return {}, [f"unknown entity '{eid}'"]
    root = store.asset_root
    resolved, missing = {}, []
    for key in e.required_sheet_keys():
        rel = e.sheet_path(key)
        if not rel:
            missing.append(f"{eid}.{key}: no path in index")
            continue
        ap = root / rel
        if ap.exists():
            resolved[key] = str(ap)
        else:
            missing.append(f"{eid}.{key} -> {rel} (NOT ON DISK)")
    return resolved, missing


def resolve_setting(store: CanonStore, eid: str) -> list[str]:
    """Return a list of problems; empty means the setting is renderable."""
    e = store.entity(eid)
    if e is None:
        return [f"unknown setting '{eid}'"]
    if e.kind not in ("setting", "visual-metaphor"):
        return [f"'{eid}' is kind '{e.kind}', not a setting/visual-metaphor"]
    problems: list[str] = []
    # NESTED SETTINGS (v0.29): refuse a broken `partOf` chain HERE, at the gate, rather
    # than letting the renderer discover it. A cycle or a missing parent is named.
    from .nesting import problems as _nest_problems
    problems += _nest_problems(lambda i: (store.entity(i).raw if store.entity(i) else None), eid)
    if e.raw.get("status") != "locked":
        problems.append(f"setting '{eid}' status is '{e.raw.get('status')}' (not 'locked') — "
                        f"lock turnaround + emptyPlates + blueprint + map + blocking + dressing first")
    root = store.asset_root
    contract = e.raw.get("contract", {}) or {}
    # THE SAME PREDICATE THE PROMOTER USES (v0.29). `setting_contract_gaps` owns which
    # fields are load-bearing (file fields non-null, emptyPlates present and up to any
    # declared count, descriptors non-empty); this function adds the one thing a pure
    # predicate cannot know, which is whether the files are actually on disk.
    problems += [f"{eid}.{g}" for g in setting_contract_gaps(contract)]
    for f in SETTING_GATE_FILE_FIELDS:
        v = contract.get(f)
        if v and not (root / v).exists():
            problems.append(f"{eid}.{f} -> {v} (NOT ON DISK)")
    for rel in contract.get("emptyPlates") or []:
        if not (root / rel).exists():
            problems.append(f"{eid}.emptyPlates -> {rel} (NOT ON DISK)")
    return problems


def assert_story(store: CanonStore, story_id: str) -> list[str]:
    """THE pre-render gate. Returns [] if the whole story is renderable, else every problem."""
    story = store.stories.get(story_id)
    if story is None:
        return [f"unknown story '{story_id}'"]
    problems = list(story.validate())
    # every featured entity that has required sheets must resolve them on disk
    # (characters, but also renderable motifs/props like the wisp)
    for fid in story.features:
        e = store.entity(fid)
        if e is None:
            problems.append(f"story features unknown entity '{fid}'")
            continue
        if e.required_sheet_keys():
            _, missing = resolve_entity_assets(store, fid)
            problems += missing
        else:
            # AN ENTITY THAT DECLARES NOTHING USED TO PASS TRIVIALLY, which made this gate
            # unable to refuse the single most common pre-render state: a cast scaffolded by
            # add-entity and not yet shot. The gate verified that DECLARED sheets exist, so an
            # empty requiredForRender skipped the check entirely and a story whose whole new
            # cast had zero art on disk returned OK. Earned on knowledge-shall-increase
            # 2026-07-30: eight new entities, no plates, gate green.
            # An entity with no sheet slots at all (a doctrine, a pure-prose motif) is still
            # fine; what is refused is one that HAS slots and has filled none of them.
            slots = (e.structured.get("sheets") or {})
            if slots and not any(slots.values()):
                problems.append(
                    f"'{fid}' declares {len(slots)} reference slot(s) and has filled none of "
                    f"them, and requiredForRender is empty, so nothing about it is locked. "
                    f"Shoot its matrix (shoot-references) before rendering."
                )
        # A setting or visual-metaphor carries its own lock flag, and an unlocked one is
        # explicitly not renderable. Nothing checked it here before.
        if e.kind in ("setting", "visual-metaphor") and e.raw.get("status") == "unlocked":
            problems.append(
                f"'{fid}' is status 'unlocked' and may not be rendered against. Lock it once "
                f"its plates pass read-back."
            )
    # every beat's declared location must be a locked, on-disk setting
    for b in story.beats:
        loc = b.get("location")
        if loc:
            problems += [f"beat {b.get('n')}: {m}" for m in resolve_setting(store, loc)]
    return problems


def archived_casts(store: CanonStore, story_id: str) -> list[str]:
    """Every ARCHIVED entity this story still casts, as actionable one-liners.

    Deliberately NOT part of assert_story. Archiving must never retroactively break a
    book that already shipped: the whole point of an archive is that history stays
    renderable and its provenance stays honest. So this is a WARNING channel that
    authoring tools read, and the refusal lives at the point of NEW casting (the
    casting sweep and the spread compiler), not at the pre-render gate.
    """
    story = store.stories.get(story_id)
    if story is None:
        return [f"unknown story '{story_id}'"]
    seen: list[str] = []
    # Ids arrive from three places and REAL canon is not uniformly typed: a beat's
    # `characters` may hold plain ids or {"id": ...} objects, and `features` may hold
    # either. Normalise instead of assuming, or this raises on the first mixed story.
    def _ids(v) -> list[str]:
        out = []
        for x in v or []:
            if isinstance(x, str):
                out.append(x)
            elif isinstance(x, dict) and isinstance(x.get("id"), str):
                out.append(x["id"])
        return out

    ids = _ids(story.features)
    for b in story.beats:
        loc = b.get("location")
        if isinstance(loc, str) and loc:
            ids.append(loc)
        elif isinstance(loc, dict) and isinstance(loc.get("id"), str):
            ids.append(loc["id"])
        ids += _ids(b.get("characters"))
    for eid in dict.fromkeys(ids):
        e = store.entity(eid)
        if e is not None and e.is_archived:
            seen.append(e.archive_note())
    return seen


def archived_entities(store: CanonStore) -> list[str]:
    """Every archived entity in the universe, newest-archived first where dated."""
    out = []
    for eid, e in store.entities.items():
        if e.is_archived:
            out.append(((e.raw.get("archived") or {}).get("on") or "", e.archive_note()))
    return [n for _, n in sorted(out, reverse=True)]


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
        try:
            problems = resolve_setting(store, eid)
        except (TypeError, AttributeError):
            return "partial"   # malformed contract: has a contract block but not clean-lockable
        if not problems:
            return "locked"
        contract = e.raw.get("contract", {}) or {}
        if not isinstance(contract, dict):
            return "stub"
        has_any = any(
            isinstance(contract.get(f), str) and (store.asset_root / contract[f]).exists()
            for f in ("turnaround", "blueprint")
        )
        return "partial" if has_any else "stub"

    root = store.asset_root
    sheets = (e.raw.get("structured") or {}).get("sheets") or {}
    if not isinstance(sheets, dict):
        return "stub"
    if not sheets:
        return "stub"

    aliases = (e.raw.get("structured") or {}).get("sheetAliases") or {}
    if not isinstance(aliases, dict):
        aliases = {}

    def on_disk(key: str) -> bool:
        # A slot is a bare path or {path, role} (SPEC v0.23); normalise before testing,
        # or every typed slot would silently report as unfilled and drop the entity's
        # lock level. A declared sheetAlias resolves one hop, the same fallback
        # Entity.sheet_path applies, so the grader and the resolver agree.
        slot = sheets.get(key)
        if slot is None and key in aliases:
            slot = sheets.get(aliases[key])
        p = sheet_parts(slot)[0]
        return isinstance(p, str) and (root / p).exists()

    req = e.required_sheet_keys()
    req_ok = bool(req) and all(on_disk(k) for k in req)

    m = matrix_for(e.kind)
    if m is None:
        return "locked" if req_ok else "partial"
    if all(on_disk(k) for k in m["shots"]):
        return "locked"
    return "partial" if req_ok else "stub"


def assert_spread(store: CanonStore, characters: list[str], location: str | None) -> list[str]:
    """Single-unit gate (one spread): named characters + optional location must resolve."""
    problems: list[str] = []
    for cid in characters:
        _, missing = resolve_entity_assets(store, cid)
        problems += missing
    if location:
        problems += resolve_setting(store, location)
    return problems
