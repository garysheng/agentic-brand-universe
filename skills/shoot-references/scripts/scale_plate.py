#!/usr/bin/env python3
"""Render a MULTI-CHARACTER height scale plate, and optionally register it on every
character in it.

    scale_plate.py <universe> <id> <id> [<id>...] [--out PATH] [--register]

WHY THIS EXISTS. `lint-universe` warns CHARACTER-HEIGHT-UNDEPICTED when an entity
declares `scale.height` with no `scale-plate` sheet, and SPEC v0.10 makes
`scale.relativeTo` load-bearing "because every entity is described ALONE, so without
this two people in one frame come out the same height and nobody catches it until
someone who knows them does". The framework therefore ASKED for the artifact and
shipped no verb to make it: the checker existed, the maker did not.

The consequence was predictable. A one-off render-spec gets written in a scratch
folder, rendered once, and thrown away, so the next pair of characters starts from
nothing. That happened twice in one session (nation-of-fire, 2026-08-20,
`gary-sheng` + `larrance-dopson`) before this was built.

WHY MULTI-CHARACTER IS THE POINT. A solo figure against a drawn ruler is the obvious
design and it is the weaker one, for a reason worth stating: the ruler's numbers are
TEXT, and an image model garbles a long numeric sequence. Both solo attempts in that
session failed exactly there, one rendering the subject at 5'8" when asked for 6'0"
and the next returning a rule numbered 6'0", 4'4", 2'8", 1'2", 0'2". Two people on one
ground line need no numbers at all: the men are the measure, and relative height is
the only thing a render actually has to hold.

HOW IT READS CANON. The ordering and the wording are DERIVED from each entity's
`structured.scale`, never retyped by the caller, so the plate cannot contradict the
records it exists to depict. `assemble_prompt` then injects the `relativeTo` phrases
on its own, which means the height relation reaches the model twice: once as this
scene's explicit staging and once as canon's own sentence.

This is a thin wrapper over `compose-spread/scripts/render_spread.py`, on purpose. It
writes a render-spec and hands it over, so refusals, ref resolution, the uncast-name
guard, provenance and the single-image guard are all the tested ones rather than a
second implementation that drifts.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _skills_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_entity(uroot: Path, eid: str) -> dict:
    p = uroot / "canon" / "entities" / f"{eid}.json"
    if not p.exists():
        sys.exit(f"REFUSE: no entity {eid} at {p}")
    return json.loads(p.read_text())


def _height_note(ent: dict) -> str:
    return ((ent.get("structured") or {}).get("scale") or {}).get("height") or ""


def _relative_phrase(ent: dict, other_id: str) -> str:
    rel = ((ent.get("structured") or {}).get("scale") or {}).get("relativeTo") or {}
    return (rel.get(other_id) or "").strip()


def _locked_sheets(ent: dict) -> list[str]:
    out = []
    for k, v in ((ent.get("structured") or {}).get("sheets") or {}).items():
        if isinstance(v, dict):
            v = v.get("path")
        if v:
            out.append(k)
    return out


def _default_pose(ent: dict) -> str | None:
    poses = ((ent.get("structured") or {}).get("render") or {}).get("poses") or {}
    for want in ("default", "front", "standing", "forward"):
        if want in poses:
            return want
    return next(iter(poses), None)


def build_scene(order: list[tuple[str, dict]]) -> tuple[str, str]:
    """The scene text and the negatives, derived from canon rather than authored.

    `order` is left-to-right as the caller gave it. Every adjacent pair contributes
    its own sentence, so a three-person plate states two relations rather than one
    vague "tallest to shortest".
    """
    names = [eid for eid, _ in order]
    n = len(names)
    where = ", then ".join(names)

    lines = [
        f"A {n}-PERSON HEIGHT COMPARISON REFERENCE. The {n} of them stand SIDE BY SIDE "
        "in a single row, all facing the camera, all standing straight with weight even "
        "on both feet and arms relaxed at their sides, their heels on ONE COMMON GROUND "
        "LINE, against a plain continuous warm-grey studio background under soft even "
        "light. They are the entire subject and they fill the frame from head to feet.",
        f"LEFT TO RIGHT THE ORDER IS: {where}.",
    ]

    for (a_id, a_ent), (b_id, b_ent) in zip(order, order[1:]):
        phrase = _relative_phrase(a_ent, b_id) or _relative_phrase(b_ent, a_id)
        if phrase:
            subj, obj = (a_id, b_id) if _relative_phrase(a_ent, b_id) else (b_id, a_id)
            lines.append(f"{subj} is {phrase} {obj}, and that difference must be visible.")
        else:
            lines.append(
                f"{a_id} and {b_id} have NO declared relative scale in canon, so draw "
                "them at plausible everyday heights and do not invent a dramatic "
                "difference between them."
            )

    for eid, ent in order:
        h = _height_note(ent)
        if h:
            lines.append(f"{eid}: {h}")

    # CALIBRATE THE MAGNITUDE, because "a few inches" is not a quantity a model holds.
    # The first plate built with this verb (nation-of-fire, 2026-08-20) declared "a few
    # inches taller" and rendered a gap closer to six, which reads as a different class
    # of person rather than two men of similar height. Inches do not land; a BODY PART
    # does, because it is a thing already in the picture.
    lines.append(
        "CALIBRATE THE DIFFERENCE CAREFULLY. Unless a relation above says otherwise, a "
        "height difference described in INCHES is SMALL: the taller person's chin is still "
        "ABOVE the shorter person's eyes, and the gap between the tops of their heads is "
        "about the height of a FOREHEAD, never a whole head. Draw them as two people of "
        "similar height where one is somewhat taller, not as a tall person beside a short "
        "one."
    )
    lines.append(
        "Their heads are at DIFFERENT heights and their eye lines are at DIFFERENT "
        "heights. Nobody stands on anything, nobody leans, and the camera is level with "
        "their chests so perspective does not distort the comparison. This image exists "
        "to fix relative height, so the height differences are the most important thing "
        "in it."
    )

    negatives = (
        "Do not draw them all the same height. Do not reverse the declared order. "
        "No measuring rule, no ruler, no height chart, no numbers, no lettering of any "
        "kind. Nobody stands on a step, a box or a kerb. No additional people."
    )
    return " ".join(lines), negatives


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("universe")
    ap.add_argument("entities", nargs="+",
                    help="two or more character ids, in LEFT-TO-RIGHT order")
    ap.add_argument("--out", help="output png (default: reference/<first>/scale-plate.png)")
    ap.add_argument("--size", default="1024x1536")
    ap.add_argument("--register", action="store_true",
                    help="lock the result as the 'scale-plate' sheet on EVERY listed entity")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--print-prompt", action="store_true")
    a = ap.parse_args()

    if len(a.entities) < 2:
        sys.exit("REFUSE: a scale plate needs at least TWO characters. One figure against "
                 "a drawn ruler is the weaker design and the numbers do not survive the "
                 "render; use two people and let them be the measure.")
    if len(set(a.entities)) != len(a.entities):
        sys.exit("REFUSE: the same entity is listed twice.")

    uroot = Path(a.universe).expanduser().resolve()
    order = [(eid, _load_entity(uroot, eid)) for eid in a.entities]

    for eid, ent in order:
        if (ent.get("kind") or "") != "character":
            sys.exit(f"REFUSE: {eid} is kind '{ent.get('kind')}', not a character.")
        if not _locked_sheets(ent):
            sys.exit(f"REFUSE: {eid} has no locked sheets, so there is no likeness to "
                     f"place on the ground line. Run shoot-references on {eid} first.")

    scene, negatives = build_scene(order)
    cast = []
    for eid, ent in order:
        entry = {"id": eid}
        pose = _default_pose(ent)
        if pose:
            entry["pose"] = pose
        cast.append(entry)

    spec = {
        "book": "scale-plate",
        "provider": "gpt-image-2",
        "size": a.size,
        "preamble": "",
        "spreads": [{
            "id": "scale-plate",
            "size": a.size,
            "shot": "wide",
            "cast": cast,
            "scene": scene,
            "negatives": negatives,
        }],
    }

    out = Path(a.out) if a.out else uroot / "reference" / a.entities[0] / "scale-plate.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    renderer = _skills_root() / "compose-spread" / "scripts" / "render_spread.py"
    with tempfile.TemporaryDirectory() as td:
        spec_path = Path(td) / "render-spec.json"
        spec_path.write_text(json.dumps(spec, indent=1))
        cmd = [sys.executable, str(renderer), str(uroot), str(spec_path), "scale-plate",
               "--out", str(out)]
        if a.dry_run:
            cmd.append("--dry-run")
        if a.print_prompt:
            cmd.append("--print-prompt")
        rc = subprocess.call(cmd)

    if rc != 0 or a.dry_run:
        return rc

    if a.register:
        cli_root = _skills_root().parent / "engine"
        rel = os.path.relpath(out, uroot)
        for eid, _ in order:
            r = subprocess.call(
                [sys.executable, "-m", "agenticstory.cli", "lock-shot", str(uroot),
                 eid, "scale-plate", rel, "--recipe", str(out) + ".recipe.json"],
                cwd=str(cli_root))
            if r != 0:
                print(f"  ! could not register scale-plate on {eid}", file=sys.stderr)
        print(f"registered scale-plate on: {', '.join(e for e, _ in order)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
