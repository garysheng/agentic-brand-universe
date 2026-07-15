"""
Agentic Story — load-bearing references.

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
    for f in SETTING_CONTRACT_FIELDS:
        v = contract.get(f)
        if f == "emptyPlates":
            if not v:
                problems.append(f"{eid}.emptyPlates is empty (need per-angle EMPTY plates)")
            else:
                for rel in v:
                    if not (root / rel).exists():
                        problems.append(f"{eid}.emptyPlates -> {rel} (NOT ON DISK)")
        elif v in (None, ""):
            problems.append(f"{eid}.{f} is null (required by the setting contract)")
        elif not (root / v).exists():
            problems.append(f"{eid}.{f} -> {v} (NOT ON DISK)")
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
    # every beat's declared location must be a locked, on-disk setting
    for b in story.beats:
        loc = b.get("location")
        if loc:
            problems += [f"beat {b.get('n')}: {m}" for m in resolve_setting(store, loc)]
    return problems


def assert_spread(store: CanonStore, characters: list[str], location: str | None) -> list[str]:
    """Single-unit gate (one spread): named characters + optional location must resolve."""
    problems: list[str] = []
    for cid in characters:
        _, missing = resolve_entity_assets(store, cid)
        problems += missing
    if location:
        problems += resolve_setting(store, location)
    return problems
