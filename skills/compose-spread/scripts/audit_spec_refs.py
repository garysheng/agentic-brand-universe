#!/usr/bin/env python3
"""Audit a WHOLE render-spec's references before a single spread is rendered.

WHY THIS EXISTS. `assemble_prompt.py` already computes the refs for ONE spread, and a
human is told to "dry-run and LOOK AT THE REF COUNT". Looking is the part that fails. The
documented cost: Looked Like Hate assembled all five of its candle spreads, cover
included, with ZERO of its spine object's plates, and it surfaced only because somebody
dumped the refs by hand. The same defect recurred on God Does Not Need Our Help
(2026-08-03), where all 26 spreads named the arch via the spread-level `plate` key and not
one of them passed an arch plate.

That second case is the sharp one and is mechanically detectable, so this tool detects it:

    spread-level `plate` selects the SETTING's plate. On a spread with no `setting` it is
    SILENTLY IGNORED.

Nothing errored. The spec read as though the arch was selected on every spread. The book's
entire spine object would have been improvised from prose, drifting between states, and
the only signal was a ref count of 1 on a picture whose whole subject was that object.

Zero cost: no model, no network. Run it after compose-spec and after any spec edit.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assemble_prompt as ap  # noqa: E402


def entities_in_refs(uroot: Path, refs: list[str]) -> set[str]:
    """Which entity folders contributed a reference image."""
    out = set()
    root = (uroot / "reference").resolve()
    for r in refs:
        try:
            rel = Path(r).resolve().relative_to(root)
        except (ValueError, OSError):
            continue
        if rel.parts:
            out.add(rel.parts[0])
    return out


def declared_paths(ent: dict) -> list[str]:
    """EVERY reference path this entity itself declares, across all four homes.

    `structured.sheets` (including a typed {path, role} slot), every `altLooks.<key>`
    anchorPhoto and sheet, the `contract` slots a setting / visual-metaphor hangs its
    art off, and a realPerson's `photoStack`. This is deliberately a UNION and not a
    resolution: the question here is only "which folders is this entity's art in", so
    a plate that a given spread would not select still counts.
    """
    st = ent.get("structured") or {}
    out: list[str] = []

    def take(v):
        p = ap._sheet_path(v)
        if p:
            out.append(p)

    for v in (st.get("sheets") or {}).values():
        take(v)
    for al in (st.get("altLooks") or {}).values():
        if not isinstance(al, dict):
            continue
        take(al.get("anchorPhoto"))
        for v in (al.get("sheets") or {}).values():
            take(v)
    con = ent.get("contract") or st.get("contract") or {}
    if isinstance(con, dict):
        for k in ("turnaround", "master", "blueprint", "scalePlate"):
            take(con.get(k))
        for v in (con.get("plates") or {}).values():
            take(v)
        for v in con.get("emptyPlates") or []:
            take(v)
    rp = ent.get("realPerson") or st.get("realPerson") or {}
    if isinstance(rp, dict):
        ps = rp.get("photoStack")
        if isinstance(ps, str):
            out.append(ps)
        elif isinstance(ps, list):
            out.extend(x for x in ps if isinstance(x, str))
    return out


def declared_ref_dirs(uroot: Path, eid: str) -> set[str]:
    """The reference FOLDERS this entity's own canon points at, never its id.

    AN ENTITY'S ID IS NOT A PROMISE ABOUT WHERE ITS ART LIVES. This check used to
    assume `reference/<entity-id>/` and warn whenever no ref came out of that exact
    folder, so an entity whose art was deliberately re-foldered was reported as
    "drawn from prose" on every spread that cast it, while the audit's own ref line
    listed its plates two columns to the left.

    Earned 2026-08-04 on An Amazing Sex Life (nation-of-fire). The Apostle is one man
    in one folder by explicit universe law — all his art is under
    `reference/apostle-delmar-lee-coward-jr/` while the canon id stays `apostle-lee`,
    which is the id every story and every render-spec casts. The warning fired four
    times in one book, on a book where all ten of his plates reached the model. A
    check that is wrong every time it fires trains its operator to ignore it, and this
    one is otherwise load-bearing: the true positive it exists to catch (a cast entity
    whose plates never arrive) looks identical.

    Falls back to the id when the entity declares no paths at all, which is the
    plateless-setting case: there is nothing else to compare against, and an entity
    with no art anywhere still deserves the warning.
    """
    ent = ap.load_entity(uroot, eid)
    dirs = set()
    for p in declared_paths(ent):
        parts = Path(str(p)).parts
        if "reference" in parts:
            i = parts.index("reference")
            if len(parts) > i + 1:
                dirs.add(parts[i + 1])
    return dirs or {eid}


def audit(uroot: Path, spec: dict) -> tuple[list[dict], list[str]]:
    rows, problems = [], []
    anchor_dir = None
    reg = (ap.load(uroot / "universe.json").get("identity", {}).get("register") or {})
    if reg.get("anchor"):
        anchor_dir = Path(reg["anchor"]).parts[1] if len(Path(reg["anchor"]).parts) > 1 else None

    for sp in spec.get("spreads", []):
        sid = sp.get("id", "?")
        cast_ids = [c.get("id") for c in (sp.get("cast") or []) if c.get("id")]

        # The silent-ignore trap, caught from the SPEC alone.
        if sp.get("plate") and not sp.get("setting"):
            problems.append(
                f"{sid}: has `plate: {sp['plate']!r}` but NO `setting`. The spread-level "
                "`plate` key selects the SETTING's plate and is silently ignored here, so "
                "this selects nothing. Cast the entity instead: "
                '{"id": "<entity>", "plate": "<sheet>"} inside `cast`.')

        try:
            built = ap.build(uroot, spec, sid)
        except ap.Refuse as e:
            problems.append(f"{sid}: REFUSE: {e}")
            rows.append({"id": sid, "refs": 0, "entities": [], "cast": cast_ids})
            continue

        refs = built["refs"]
        ents = entities_in_refs(uroot, refs)
        contributing = {e for e in ents if e != anchor_dir}
        rows.append({"id": sid, "refs": len(refs),
                     "entities": sorted(contributing), "cast": cast_ids})

        # A spread carrying only the style anchor takes its whole subject from that
        # anchor, which is how the anchor's own subject leaks into the picture.
        if len(refs) <= 1:
            problems.append(
                f"{sid}: only {len(refs)} reference image(s), the style anchor alone. "
                "Everything in this picture will be improvised, and the anchor's subject "
                "leaks. Cast the entities this spread is actually about.")

        # Declared in cast, absent from refs: the canon exists and never arrived.
        # Compared against the folders the ENTITY declares, not against its id, and
        # against every folder that contributed (the anchor's included), because an
        # entity that IS the register anchor did reach the model.
        for cid in cast_ids:
            try:
                want = declared_ref_dirs(uroot, cid)
            except ap.Refuse:
                continue  # unregistered id: build() already refused and said so
            if not (want & ents):
                where = ", ".join(f"reference/{d}/" for d in sorted(want))
                problems.append(
                    f"{sid}: casts {cid!r} but NO reference image from {where} was "
                    "passed. Its plates are not reaching the model, so it is being "
                    "drawn from prose. Check the entity's requiredForRender, or name a "
                    "`plate`/`pose` that exists.")
    return rows, problems


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("universe")
    p.add_argument("render_spec")
    p.add_argument("--json", action="store_true", help="machine-readable rows")
    a = p.parse_args()

    uroot = Path(a.universe)
    spec = ap.load(Path(a.render_spec))
    rows, problems = audit(uroot, spec)

    if a.json:
        print(json.dumps({"rows": rows, "problems": problems}, indent=2))
    else:
        for r in rows:
            ents = ",".join(r["entities"]) or "-"
            print(f"  {r['id']:<12} refs={r['refs']:<3} from: {ents}")
        print()
        if problems:
            print(f"audit-spec-refs: {len(problems)} problem(s):")
            for pr in problems:
                print(f"  - {pr}")
        else:
            print(f"audit-spec-refs: OK ({len(rows)} spreads, every cast entity reached "
                  "the model)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
