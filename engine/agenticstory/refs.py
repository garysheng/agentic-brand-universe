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
from .model import Entity, SETTING_CONTRACT_FIELDS
from .matrix import matrix_for


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
    if e.raw.get("status") != "locked":
        problems.append(f"setting '{eid}' status is '{e.raw.get('status')}' (not 'locked') — "
                        f"lock turnaround + emptyPlates + blueprint + map + blocking + dressing first")
    root = store.asset_root
    contract = e.raw.get("contract", {}) or {}
    # File fields must resolve on disk; descriptor fields (prose passed in prompts) must be non-empty.
    file_fields = ("turnaround", "blueprint")
    descriptor_fields = ("map", "blocking", "dressing")
    for f in file_fields:
        v = contract.get(f)
        if v in (None, ""):
            problems.append(f"{eid}.{f} is null (required image; the drawn plate/blueprint)")
        elif not (root / v).exists():
            problems.append(f"{eid}.{f} -> {v} (NOT ON DISK)")
    plates = contract.get("emptyPlates") or []
    if not plates:
        problems.append(f"{eid}.emptyPlates is empty (need per-angle EMPTY plates)")
    else:
        for rel in plates:
            if not (root / rel).exists():
                problems.append(f"{eid}.emptyPlates -> {rel} (NOT ON DISK)")
    for f in descriptor_fields:
        if not (contract.get(f) or "").strip():
            problems.append(f"{eid}.{f} is empty (required descriptor: prose passed in every prompt)")
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


def assert_spread(store: CanonStore, characters: list[str], location: str | None) -> list[str]:
    """Single-unit gate (one spread): named characters + optional location must resolve."""
    problems: list[str] = []
    for cid in characters:
        _, missing = resolve_entity_assets(store, cid)
        problems += missing
    if location:
        problems += resolve_setting(store, location)
    return problems
