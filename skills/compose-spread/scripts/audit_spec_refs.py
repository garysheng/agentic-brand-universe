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
        for cid in cast_ids:
            if cid not in contributing:
                problems.append(
                    f"{sid}: casts {cid!r} but NO reference image from "
                    f"reference/{cid}/ was passed. Its plates are not reaching the model, "
                    "so it is being drawn from prose. Check the entity's "
                    "requiredForRender, or name a `plate`/`pose` that exists.")
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
