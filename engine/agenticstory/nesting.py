"""Nested settings: a room is a setting that is `partOf` another setting.

WHY THIS EXISTS (SPEC v0.29, earned 2026-08-02 on nation-of-fire).

A setting carries exactly ONE flat contract: one `map`, one `blocking`, one
`dressing`, one `scale`, for the whole entity. That is correct for a shed and
wrong for a house. `christofuturist-home` had accumulated twelve plates covering
nine distinct rooms, all sharing a single room-agnostic `blocking` string, and
the consequences were not theoretical:

  * SPEC v0.13 added `contract.scalePlate` after "christofuturist-home, whose
    hearth room rendered small." One room's scale problem, unfixable on a
    nine-room entity, so it became a new field for everybody.
  * 2026-08-02, Movies Are Sermons: the sunken pit needed FIXED LETTERED SEATING
    (SEAT A / SEAT B). There was nowhere to put it. A `blocking` naming two seats
    would have been a lie about the other eight rooms, which have none. The room
    had to be promoted OUT of the house into a top-level sibling entity, which
    then lost the containment relationship entirely: nothing in the data said the
    pit is IN the home.
  * The same promotion silently dropped the house rules. The house-slipper rule
    lives on `christofuturist-home`; a SIBLING inherits nothing, so
    `everyone-indoors-wears-the-house-slippers` had to be hand-copied onto the
    pit. A rule duplicated by hand is a rule that will drift.

Gary named it: "A setting should be able to be nested in a setting and our engine
should be smart enough to understand how to deal with that."

WHAT INHERITS: ONLY WHAT THE PARENT EXPLICITLY SHARES.

A parent declares `structured.houseRules`, and that block ALONE is inherited:

    "houseRules": {
      "invariants": ["shoes-come-off-indoors"],
      "dressing":   "cream plaster, oak and brass throughout."
    }

TWO FIELDS, AND ONLY TWO, BECAUSE ONLY TWO DO ANYTHING. A setting's prompt block
is built by `resolve_setting` from `contract` alone (map, blocking, dressing,
scale), and a setting's read-back checks come from `structured.invariants`. So
`dressing` reaches the model and `invariants` reaches QA. `always` and `qa` were
in the first cut of this module and were verified DEAD on a real render: neither
appeared in the assembled prompt or the QA list. They are now REFUSED rather than
documented, because a field that silently does nothing is the exact failure this
codebase keeps re-earning (the hasAudio reset, the caption splitter, the `scale`
lock key). House prose goes in `dressing`; house checks go in `invariants`.

BLIND INHERITANCE WAS TRIED FIRST AND WAS WRONG, and it took ten minutes against
real canon to prove it. Folding the parent's whole `structured.invariants` into
each child handed `the-sunken-pit` two rules belonging to other rooms:
`studyNook ONLY: EXACTLY TWO armchairs...` and `hearthRotunda IS RETIRED...`.
Those are not noise, they are ACTIVE HARM: every setting invariant becomes a
render-readback QA check, so the pit would have been graded on whether it
contained two armchairs it is not supposed to have. A parent's own invariants are
about the parent; only what it nominates as a HOUSE RULE is about its children.

  UNION      houseRules.invariants -> child structured.invariants (parent first,
             deduped), which is what render-readback grades against.
  APPEND     houseRules.dressing   -> child contract.dressing (parent first),
             which is what reaches the model.
  CHILD OWNS everything else, including contract.map / blocking / scale, which
             are the ROOM's geometry and which a parent value would contradict.
  NEVER      turnaround, blueprint, scalePlate, blockingPlate, emptyPlates,
             structured.sheets, contract.plates.
             A room's art is its own. Inheriting the parent's plates would hand
             the model the hearth when it asked for the pit, which is precisely
             the drift this module exists to stop. A child must shoot its own
             matrix and satisfy the file half of the contract by itself.

Additive twice over: an entity with no `partOf` resolves byte-identically to
before, and a parent with no `houseRules` gives its children nothing.
"""
from __future__ import annotations

from typing import Any, Callable

MAX_DEPTH = 8

#: contract fields whose parent value is kept and the child's appended after it
INHERIT_APPEND_CONTRACT = ("dressing",)
#: contract fields the child alone owns. Not a code path any more: with explicit
#: houseRules a parent has no way to reach them, and that is the point. Kept named
#: so the intent survives if someone later widens what a parent may share.
CHILD_ONLY_CONTRACT = ("map", "blocking", "scale")
#: everything a child must supply itself, because art and file paths never inherit
NEVER_INHERITED = (
    "turnaround", "blueprint", "scalePlate", "blockingPlate", "emptyPlates", "plates",
)

NESTABLE_KINDS = ("setting", "visual-metaphor")


class NestingError(ValueError):
    """A `partOf` chain that cannot be resolved: cycle, missing, wrong kind, too deep."""


def _pid(ent: dict | None) -> str:
    if not isinstance(ent, dict):
        return ""
    v = ent.get("partOf")
    return v.strip() if isinstance(v, str) else ""


def parent_chain(load: Callable[[str], dict | None], eid: str,
                 *, max_depth: int = MAX_DEPTH) -> list[str]:
    """Ancestor ids for `eid`, nearest parent first. `[]` when it nests in nothing.

    Refuses a cycle by NAMING it, because "maximum recursion depth exceeded" tells
    an author nothing about which two rooms point at each other.
    """
    chain: list[str] = []
    seen = [eid]
    cur = load(eid)
    if cur is None:
        raise NestingError(f"unknown entity '{eid}'")
    while True:
        pid = _pid(cur)
        if not pid:
            return chain
        if pid in seen:
            loop = " -> ".join([*seen, pid])
            raise NestingError(f"partOf cycle: {loop}")
        if len(chain) >= max_depth:
            raise NestingError(
                f"partOf chain deeper than {max_depth} from '{eid}': {' -> '.join(seen)}")
        parent = load(pid)
        if parent is None:
            raise NestingError(f"'{seen[-1]}' is partOf unknown entity '{pid}'")
        pkind = parent.get("kind")
        if pkind not in NESTABLE_KINDS:
            raise NestingError(
                f"'{seen[-1]}' is partOf '{pid}', which is kind '{pkind}'. "
                f"A setting may only nest inside {' or '.join(NESTABLE_KINDS)}.")
        chain.append(pid)
        seen.append(pid)
        cur = parent


def _dedup(xs):
    out, seen = [], set()
    for x in xs:
        k = x if isinstance(x, str) else repr(x)
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out


def _join(parent: Any, child: Any) -> str:
    a = parent.strip() if isinstance(parent, str) else ""
    b = child.strip() if isinstance(child, str) else ""
    return " ".join(p for p in (a, b) if p)


#: the only keys that have an effect. See the module docstring.
HOUSE_RULE_KEYS = ("invariants", "dressing")


def house_rules(ent: dict | None) -> dict:
    """The block a parent shares with its children. `{}` when it shares nothing.

    REFUSES an unknown key instead of ignoring it. `always` and `qa` read like they
    should work and do not, so an author who writes them gets an error naming the
    field that does work, rather than a render that quietly drops their rule.
    """
    hr = ((ent or {}).get("structured") or {}).get("houseRules")
    if not isinstance(hr, dict):
        return {}
    bad = [k for k in hr if k not in HOUSE_RULE_KEYS]
    if bad:
        raise NestingError(
            f"'{(ent or {}).get('id')}' houseRules has no-op key(s) {sorted(bad)}. "
            f"Only {list(HOUSE_RULE_KEYS)} are inherited: a setting's prompt block is built "
            "from contract.dressing and its read-back checks come from structured.invariants. "
            "Put house prose in houseRules.dressing and house checks in houseRules.invariants.")
    return hr


def merge_pair(parent: dict, child: dict) -> dict:
    """One inheritance step. Returns a new dict; neither input is mutated.

    Reads ONLY `parent.structured.houseRules`. The parent's own invariants,
    dressing and plates are about the parent and stay there.
    """
    hr = house_rules(parent)
    out = {k: v for k, v in child.items() if k != "partOf"}

    cc = child.get("contract") or {}
    con = dict(cc)
    for f in INHERIT_APPEND_CONTRACT:
        joined = _join(hr.get(f), cc.get(f))
        if joined:
            con[f] = joined
    for f in NEVER_INHERITED:
        # belt and braces: a parent value must never leak in even if a future
        # merge rule is added carelessly above.
        if f not in cc:
            con.pop(f, None)
    if con:
        out["contract"] = con

    cs = child.get("structured") or {}
    st = dict(cs)
    inv = _dedup(list(hr.get("invariants") or []) + list(cs.get("invariants") or []))
    if inv:
        st["invariants"] = inv
    out["structured"] = st
    # provenance for a human reading the resolved view, and for lint
    out["_inheritedFrom"] = [parent["id"]] + list(child.get("_inheritedFrom") or [])
    return out


def resolve(load: Callable[[str], dict | None], eid: str,
            *, max_depth: int = MAX_DEPTH) -> dict:
    """The entity as the renderer should see it, with every ancestor folded in.

    Returns the entity UNCHANGED (a copy) when it declares no `partOf`, so this is
    safe to call unconditionally on every setting in every universe.
    """
    ent = load(eid)
    if ent is None:
        raise NestingError(f"unknown entity '{eid}'")
    chain = parent_chain(load, eid, max_depth=max_depth)
    if not chain:
        return dict(ent)
    merged = dict(ent)
    for pid in chain:                       # nearest parent first, then outward
        parent = load(pid)
        merged = merge_pair(parent, merged)
    merged["id"] = ent["id"]
    merged["kind"] = ent.get("kind")
    return merged


def problems(load: Callable[[str], dict | None], eid: str) -> list[str]:
    """Validation strings for the gate. Empty means the nesting is sound."""
    try:
        parent_chain(load, eid)
    except NestingError as e:
        return [str(e)]
    return []
