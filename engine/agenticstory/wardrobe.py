"""Wardrobe resolution (SPEC v0.28 §4.7.1, §12.4): what a figure is WEARING.

Lookbooks were specified in v0.12 and consumed by nobody. `on-brand-image --lookbook`
wrote the lookbook's NAME into the recipe after the image already existed, and the
engine held zero lines about them. Meanwhile craft-canon rules across two universes
said, in so many words, "pass --lookbook X so the renderer samples 2-4 exemplars,
applies the varietyRule and gates the output" — describing three behaviours that had
never been implemented. The canon was correct and unexecutable, which is the same
defect class as v0.23 through v0.26 and the fifth instance of it.

The visible cost, Gary 2026-08-01: two locked characters with nine blessed plates
between them had NO wardrobe binding of any kind, and the one prose instruction that
gestured at one (`WARDROBE is drawn from realPerson.wardrobeEras`) pointed at a field
that was null. So every good clothing decision reached the model only when an agent
happened to read the craft canon and retype it into a prompt by hand. That is why the
look drifted between sessions: the wardrobe was never actually attached to the person.

This module makes wardrobe RESOLVABLE:

  * `Lookbook` loads and validates a lookbook folder, and can `sample()` exemplars.
  * `structured.wardrobe` binds lookbooks, an era and garment negatives TO AN ENTITY,
    so a person carries their own clothes instead of a renderer remembering them.
  * `resolve_wardrobe()` answers the question a fresh session actually has: "I am
    rendering these people in this situation — what are they wearing?" It merges the
    universe baseline, each entity's binding, and any context-triggered lookbooks,
    and returns the refs, the aesthetic, the variety rules, the negatives and the gate.

The design rule this follows: a lookbook is the VARIED complement of a Style Pack, so
resolution must never collapse to one look. Every merge here preserves range and every
gate assertion checked is a variety assertion.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

# Where lookbooks live inside a universe, unless `universe.json` overrides it with
# `lookbookRoot`. Relative to the universe dir, matching how `assetRoot` behaves.
LOOKBOOK_ROOT_DEFAULT = "reference/lookbook"

# The typed keys `structured.wardrobe` accepts. A typo in a wardrobe block is exactly
# as dangerous as a typo in a sheet role: the author believes a constraint is in force
# and nothing is reading it. So unknown keys are a validation problem, not a shrug.
WARDROBE_KEYS = {"lookbooks", "era", "negatives", "alwaysWears", "note", "outfits"}

# `outfits` is the SELECTION half of wardrobe, added once the sampling half proved wrong
# for named characters. A lookbook is a generative vocabulary and every negative added to
# it is one more thing to route around; three rounds of constraining a named character's
# clothing from the lookbook side all failed, and naming one outfit worked immediately.
# So: crowds sample, named people select. An entry is
# `<look-id>: {look, words, blessedOn}`, produced by the `fashion-look` form and mirrored
# as an `altLooks` entry so `--entity <universe>:<id>@<look-id>` resolves it at render.

# The minimum a lookbook needs before it is a vocabulary rather than a mood board.
# `gate` is required and must be non-empty: SPEC §4.7.1 has said since v0.12 that "a
# lookbook without a variety gate is a mood board that drifts back to a uniform on the
# first render", and nothing enforced it.
LOOKBOOK_REQUIRED = ("id", "aesthetic", "varietyRule", "gate")


class Lookbook:
    """One curated, intentionally VARIED visual vocabulary on disk."""

    def __init__(self, path: str | Path, data: dict[str, Any]):
        self.dir = Path(path).resolve()
        self.raw = data

    @staticmethod
    def load(folder: str | Path) -> "Lookbook":
        p = Path(folder).resolve()
        f = p / "lookbook.json"
        if not f.exists():
            raise FileNotFoundError(f"no lookbook.json in {p}")
        return Lookbook(p, json.loads(f.read_text()))

    @property
    def id(self) -> str:
        return self.raw.get("id") or self.dir.name

    @property
    def name(self) -> str:
        return self.raw.get("name") or self.id

    @property
    def aesthetic(self) -> str:
        return self.raw.get("aesthetic") or ""

    @property
    def variety_rule(self) -> str:
        return self.raw.get("varietyRule") or ""

    @property
    def gate(self) -> list[str]:
        return list(self.raw.get("gate") or [])

    @property
    def negatives(self) -> list[str]:
        """Garment-level negatives this vocabulary forbids outright.

        Distinct from `gate`, which is checked against the OUTPUT after the fact. These
        go INTO the prompt, because some things are cheaper to never draw than to catch
        on read-back.
        """
        return list(self.raw.get("negatives") or [])

    @property
    def min_refs(self) -> int:
        try:
            return int(self.raw.get("minRefs") or 3)
        except (TypeError, ValueError):
            return 3

    @property
    def applies_when(self) -> list[str]:
        """Context tags that pull this lookbook in without anyone naming it.

        `christofuturist-children` should arrive because there are children in the
        scene, not because someone remembered a flag. Empty means the lookbook applies
        only when bound to an entity or named explicitly.
        """
        return [str(t) for t in (self.raw.get("appliesWhen") or [])]

    @property
    def always(self) -> bool:
        """True when this vocabulary governs EVERY render of a clothed figure.

        The universe baseline. One lookbook should usually carry this; several means
        no baseline at all.
        """
        return bool(self.raw.get("always"))

    def ref_paths(self) -> list[Path]:
        """Declared refs, resolved against the lookbook folder, existing ones only."""
        out = []
        for r in (self.raw.get("refs") or []):
            p = (self.dir / str(r)).resolve()
            if p.exists():
                out.append(p)
        return out

    def sample(self, n: int = 3, seed: str = "") -> list[Path]:
        """Pick `n` exemplars, varying the subset deterministically by `seed`.

        Varying the SUBSET is the whole point and is why this is not `refs[:n]`. A
        lookbook that always hands the model its first three refs has quietly become a
        Style Pack with extra steps: the range on disk stops being range the moment the
        renderer stops rotating through it.

        Deterministic rather than random so a recipe replays to the same image. The
        seed is normally the output filename, which differs per render, so successive
        renders in one batch draw different subsets while any single render is
        reproducible.
        """
        refs = self.ref_paths()
        if not refs:
            return []
        n = max(1, min(int(n), len(refs)))
        h = hashlib.sha256((seed or self.id).encode()).digest()
        # Rotate by the seed, then stride, so the subset varies in MEMBERSHIP and not
        # merely in order. A pure shuffle would do too, but rotation keeps successive
        # seeds landing on overlapping-but-different sets, which is what variety across
        # a batch of a few images actually needs.
        # The stride must be COPRIME with the ref count, or it walks a proper subgroup
        # and never visits the rest: stride 2 over 6 refs reaches only {0,2,4}, so asking
        # for 4 spins forever. The first cut did exactly that and the test run died on
        # SIGKILL. Stepping down to the nearest coprime stride makes the walk a full
        # cycle, so every ref is reachable and the loop always terminates.
        start = h[0] % len(refs)
        stride = 1 + (h[1] % len(refs))
        from math import gcd
        while gcd(stride, len(refs)) != 1:
            stride -= 1
        picked: list[Path] = []
        for k in range(len(refs)):
            if len(picked) >= n:
                break
            picked.append(refs[(start + k * stride) % len(refs)])
        return picked

    def validate(self) -> list[str]:
        p: list[str] = []
        for k in LOOKBOOK_REQUIRED:
            if not self.raw.get(k):
                p.append(f"lookbook '{self.id}': missing required '{k}'")
        if self.raw.get("kind") not in (None, "lookbook"):
            p.append(f"lookbook '{self.id}': kind must be 'lookbook', got "
                     f"'{self.raw.get('kind')}'")
        gate = self.raw.get("gate")
        if gate is not None and (not isinstance(gate, list) or not gate):
            p.append(f"lookbook '{self.id}': 'gate' must be a non-empty list. A lookbook "
                     f"without a variety gate is a mood board that drifts back to a "
                     f"uniform on the first render (SPEC 4.7.1)")
        declared = list(self.raw.get("refs") or [])
        missing = [r for r in declared if not (self.dir / str(r)).exists()]
        if missing:
            p.append(f"lookbook '{self.id}': {len(missing)} declared ref(s) not on disk: "
                     f"{', '.join(sorted(missing)[:4])}")
        live = len(self.ref_paths())
        if live < self.min_refs:
            p.append(f"lookbook '{self.id}': {live} ref(s) on disk but minRefs is "
                     f"{self.min_refs}; too few exemplars cannot express a range")
        return p


def lookbook_root(store) -> Path:
    root = (store.manifest.get("lookbookRoot") or LOOKBOOK_ROOT_DEFAULT)
    p = Path(root)
    return p if p.is_absolute() else (store.dir / p).resolve()


def lookbooks(store) -> dict[str, Lookbook]:
    """Every lookbook in a universe, keyed by id."""
    out: dict[str, Lookbook] = {}
    root = lookbook_root(store)
    if not root.is_dir():
        return out
    for f in sorted(root.glob("*/lookbook.json")):
        try:
            lb = Lookbook.load(f.parent)
        except (json.JSONDecodeError, FileNotFoundError):
            continue
        out[lb.id] = lb
    return out


def entity_wardrobe(entity) -> dict[str, Any]:
    """An entity's typed `structured.wardrobe` block, or {}."""
    st = getattr(entity, "structured", None)
    if st is None and isinstance(entity, dict):
        st = entity.get("structured") or {}
    return dict((st or {}).get("wardrobe") or {})


def validate_wardrobe(entity, known: set[str]) -> list[str]:
    """Check one entity's wardrobe block against the lookbooks that exist.

    A binding that names a lookbook which is not on disk is the same failure as a
    `requiredForRender` naming a sheet with no path: it reads as a constraint and is
    silently nothing.
    """
    eid = getattr(entity, "id", "?")
    w = entity_wardrobe(entity)
    if not w:
        return []
    p: list[str] = []
    unknown = set(w) - WARDROBE_KEYS
    if unknown:
        p.append(f"{eid}: structured.wardrobe has unknown key(s) {sorted(unknown)} "
                 f"(allowed: {sorted(WARDROBE_KEYS)})")
    lbs = w.get("lookbooks")
    if lbs is not None and not isinstance(lbs, list):
        p.append(f"{eid}: structured.wardrobe.lookbooks must be a list")
    else:
        for lb in (lbs or []):
            if lb not in known:
                p.append(f"{eid}: structured.wardrobe binds lookbook '{lb}', which does "
                         f"not exist in this universe")
    for key in ("negatives", "alwaysWears"):
        v = w.get(key)
        if v is not None and not isinstance(v, list):
            p.append(f"{eid}: structured.wardrobe.{key} must be a list")
    for key in ("era", "note"):
        v = w.get(key)
        if v is not None and not isinstance(v, str):
            p.append(f"{eid}: structured.wardrobe.{key} must be a string")
    return p


def bound_by_craft(store) -> dict[str, str]:
    """lookbook id -> the craft-canon record that binds it to this universe.

    SPEC §4.7.1 has always said a lookbook is bound to a universe through a craft-canon
    register-rule naming it. This reads that binding back, so an UNBOUND lookbook (one
    sitting on disk that no rule ever invokes) is visible rather than assumed-live.
    """
    out: dict[str, str] = {}
    for cid, c in (getattr(store, "craft", {}) or {}).items():
        raw = getattr(c, "raw", None) or {}
        # `lookbook` is the record's primary binding; `alsoBinds` covers the common case
        # of one rule governing a family of sibling vocabularies (men/women/children/
        # elders/footwear all answering to one relatability rule).
        for lb in ([raw.get("lookbook")] + list(raw.get("alsoBinds") or [])):
            if lb:
                out.setdefault(str(lb), cid)
    return out


def resolve_wardrobe(store, entity_ids: list[str] | None = None,
                     context: list[str] | None = None,
                     extra: list[str] | None = None) -> dict[str, Any]:
    """What these people, in this situation, are wearing.

    This is the question a fresh session has and could not previously ask. It merges,
    in order of increasing specificity:

      1. the universe BASELINE   — lookbooks marked `always`
      2. CONTEXT triggers        — lookbooks whose `appliesWhen` matches a context tag
      3. each entity's BINDING   — `structured.wardrobe.lookbooks`
      4. anything named EXPLICITLY by the caller

    Later layers add; nothing removes, because a wardrobe rule that a more specific
    layer could silently switch off is the lock-gate demotion bug (v0.24) wearing a
    different hat. An entity that must NOT wear something says so in its own
    `wardrobe.negatives`, which is additive too.

    BEING BOUND BY CRAFT CANON IS NOT A TRIGGER, and this was worth getting wrong once
    to learn. The first cut treated any craft-bound lookbook as baseline, and resolving
    two people standing together dragged in the MEAL vocabulary and the ROOM-DRESSING
    vocabulary, because both are legitimately bound to that universe. A craft binding
    says "this vocabulary is canon here"; it does not say "every render obeys it". So a
    bound-but-untriggered lookbook is reported under `available` — visible, so nobody
    concludes it is missing, and inert, so a portrait is not dressed like a dinner.
    """
    all_lb = lookbooks(store)
    bound = bound_by_craft(store)
    ctx = {str(t) for t in (context or [])}
    picked: list[str] = []
    why: dict[str, str] = {}

    def add(lid: str, reason: str) -> None:
        if lid in all_lb and lid not in picked:
            picked.append(lid)
            why[lid] = reason

    for lid, lb in all_lb.items():
        if lb.always:
            add(lid, "universe baseline (always)")
    for lid, lb in all_lb.items():
        hit = ctx & set(lb.applies_when)
        if hit:
            add(lid, f"context {sorted(hit)}")

    negatives: list[str] = []
    eras: dict[str, str] = {}
    always_wears: dict[str, list[str]] = {}
    missing_binding: list[str] = []
    for eid in (entity_ids or []):
        e = store.entity(eid) if hasattr(store, "entity") else None
        if e is None:
            continue
        w = entity_wardrobe(e)
        if not w:
            missing_binding.append(eid)
            continue
        for lid in (w.get("lookbooks") or []):
            add(str(lid), f"bound to entity '{eid}'")
        for n in (w.get("negatives") or []):
            if n not in negatives:
                negatives.append(str(n))
        if w.get("era"):
            eras[eid] = str(w["era"])
        if w.get("alwaysWears"):
            always_wears[eid] = [str(x) for x in w["alwaysWears"]]

    for lid in (extra or []):
        add(str(lid), "named explicitly")

    aesthetic, variety, gate = [], [], []
    for lid in picked:
        lb = all_lb[lid]
        if lb.aesthetic:
            aesthetic.append(f"[{lid}] {lb.aesthetic}")
        if lb.variety_rule:
            variety.append(f"[{lid}] {lb.variety_rule}")
        for g in lb.gate:
            if g not in gate:
                gate.append(g)
        for n in lb.negatives:
            if n not in negatives:
                negatives.append(n)

    # Canon vocabularies that exist and did not fire, with what WOULD fire them. This is
    # the difference between "this universe has no children's wardrobe" and "it has one
    # and you did not say there were children in the scene".
    available = []
    for lid in sorted(set(all_lb) - set(picked)):
        lb = all_lb[lid]
        trig = lb.applies_when
        available.append({
            "id": lid,
            "boundBy": bound.get(lid),
            "triggerTags": trig,
            "how": (f"add context {trig}" if trig else
                    "bind it to an entity's structured.wardrobe, or name it explicitly"),
        })

    return {
        "lookbooks": picked,
        "why": why,
        "aesthetic": aesthetic,
        "varietyRules": variety,
        "gate": gate,
        "negatives": negatives,
        "eras": eras,
        "alwaysWears": always_wears,
        "available": available,
        "entitiesWithNoWardrobe": missing_binding,
    }


def wardrobe_prompt_block(resolved: dict[str, Any]) -> str:
    """The resolved wardrobe as text a renderer can prepend to a prompt.

    Kept here rather than in the renderer so every consumer phrases it identically;
    two callers wording the same canon differently is how a rule ends up meaning two
    things.
    """
    parts: list[str] = []
    if resolved.get("aesthetic"):
        parts.append("WARDROBE AESTHETIC: " + "  ".join(resolved["aesthetic"]))
    if resolved.get("varietyRules"):
        parts.append("WARDROBE VARIETY: " + "  ".join(resolved["varietyRules"]))
    for eid, era in (resolved.get("eras") or {}).items():
        parts.append(f"{eid.upper()} WARDROBE ERA: {era}")
    for eid, items in (resolved.get("alwaysWears") or {}).items():
        parts.append(f"{eid.upper()} ALWAYS WEARS: " + "; ".join(items))
    if resolved.get("negatives"):
        parts.append("WARDROBE NEGATIVES (never render these): "
                     + "; ".join(resolved["negatives"]))
    return "\n".join(parts)
