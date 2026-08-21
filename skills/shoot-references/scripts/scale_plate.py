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
import re
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


def _states_large_gap(order) -> bool:
    """Does canon already NAME a large height difference for this cast?

    The calibrating paragraph below teaches the model that "a few inches" is small,
    which is right for an inches-scale relation and flatly wrong for one that says
    "a full head shorter". Written unconditionally it contradicted such a relation
    inside the same prompt.
    """
    big = ("much taller", "much shorter", "a full head", "head taller",
           "head shorter", "far taller", "far shorter", "towers over")
    for eid, ent in order:
        rel = ((ent.get("structured") or {}).get("scale") or {}).get("relativeTo") or {}
        for other, phrase in rel.items():
            if any(e == other for e, _ in order) and any(b in (phrase or "").lower() for b in big):
                return True
    return False


def _register_neutral_cast(order) -> bool:
    """True when EVERY character in the plate is a register-neutral master.

    A scale plate is a REFERENCE artifact whose only job is to fix relative height.
    Rendering it through a stylised universe register buys nothing and costs the one
    thing a real person's plate exists to carry, which is likeness. Earned 2026-08-21:
    the first larrance-dopson + clarence-avant plate came back in soft painterly oil
    and the operator's first words were "that doesn't look like Clarence at all",
    while the register-neutral matrix plates of the same man had passed at crop-zoom
    minutes earlier.
    """
    return bool(order) and all(
        (ent.get("structured") or {}).get("registerNeutral") for _, ent in order
    )



# ---------------------------------------------------------------------------
# COMPOSITE MODE (the default whenever every character has a locked full-body).
#
# A scale plate is a STUDY SHEET, and make-a-book already carries the rule for
# those: "build a multi-state study plate by COMPOSITING the locked plates in
# code, never by generating it. A generated study sheet can drift from the states
# it claims to summarize; a composite cannot. It is also free."
#
# This verb shipped as a GENERATOR and paid for it immediately. On 2026-08-21 a
# larrance-dopson + clarence-avant plate came back with a generic elderly man in
# Clarence's place -- "that doesn't look like Clarence at all" -- while the locked
# face-neutral master of the same man had passed at crop-zoom minutes before. At
# two figures on one 1024x1536 canvas each face gets around a hundred pixels, so
# the model reconstructs a face instead of copying one, and no amount of prompt
# craft fixes that.
#
# A composite cannot drift, because the pixels ARE the locked art. The height
# ratio stops being something a model estimates and becomes arithmetic.
# ---------------------------------------------------------------------------

# Relation phrases mapped to a height RATIO (shorter / taller). A head is roughly
# one seventh of an adult figure, which is where 0.87 comes from; the inch-scale
# classes are the same arithmetic against a six-foot frame.
_GAP_CLASSES = [
    (("a full head", "head shorter", "head taller", "much shorter", "much taller",
      "far shorter", "far taller", "towers over"), 0.87),
    (("several inches", "a few inches", "some inches"), 0.96),
    (("slightly", "a little", "barely", "about the same", "same height"), 0.99),
]


def _parse_height_inches(note: str):
    """Feet/inches out of a prose height note, or None. Prefers a real measurement
    over a phrase class, because arithmetic beats a bucket."""
    if not note:
        return None
    low = note.lower()
    if "not on record" in low.split(".")[0]:
        return None
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
             "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11}
    m = re.search(r"(\d+)\s*(?:'|feet|foot|ft)\s*(\d+)?", low)
    if m:
        return int(m.group(1)) * 12 + int(m.group(2) or 0)
    m = re.search(r"\b(" + "|".join(words) + r")\s+(?:feet|foot)\s+(" + "|".join(words) + r")\b", low)
    if m:
        return words[m.group(1)] * 12 + words[m.group(2)]
    m = re.search(r"\b(" + "|".join(words) + r")\s+(?:feet|foot)\b", low)
    if m:
        return words[m.group(1)] * 12
    return None


def _ratios(order) -> list:
    """One relative height per entity, tallest normalised to 1.0."""
    inches = [_parse_height_inches(_height_note(e)) for _, e in order]
    if all(inches):
        top = max(inches)
        return [i / top for i in inches]

    # No measurements: fall back to the declared relation between consecutive pairs.
    rel = [1.0]
    for (a_id, a_ent), (b_id, b_ent) in zip(order, order[1:]):
        phrase = (_relative_phrase(a_ent, b_id) or _relative_phrase(b_ent, a_id)).lower()
        ratio = 0.96
        for keys, r in _GAP_CLASSES:
            if any(k in phrase for k in keys):
                ratio = r
                break
        # Which of the pair the phrase makes SHORTER decides the direction.
        a_is_taller = True
        if _relative_phrase(a_ent, b_id):
            a_is_taller = not any(w in phrase for w in ("shorter than", "smaller than"))
        else:
            a_is_taller = any(w in phrase for w in ("shorter than", "smaller than"))
        rel.append(rel[-1] * ratio if a_is_taller else rel[-1] / ratio)
    top = max(rel)
    return [r / top for r in rel]


def _figure_bbox(im):
    """Bounding box of the figure on a studio ground.

    Two obvious approaches both failed on real plates, and the comments stay so
    the third one does not get "simplified" back into either:

      colour difference from the border  -> a PAINTED seamless backdrop is textured,
                                            so every pixel differs and the box comes
                                            back as the whole canvas.
      edge energy per row/column         -> same problem: the backdrop's brushwork
                                            carries edges everywhere.

    What actually separates a standing person from a lit backdrop is that the
    person is markedly DARKER (or lighter) than the backdrop at that height. So
    scan each row for its extreme luminance against the backdrop's own level,
    taken from the plate's corners. Earned 2026-08-21 across three attempts.
    """
    from PIL import ImageFilter
    g = im.convert("L").filter(ImageFilter.MedianFilter(3))
    w, h = g.size
    px = g.load()

    corners = []
    for cx in (0, w - 1):
        for cy in range(0, h, max(1, h // 30)):
            corners.append(px[cx, cy])
    base = sorted(corners)[len(corners) // 2]

    step = max(1, w // 300)
    def row_dev(y):
        lo = hi = px[0, y]
        for x in range(0, w, step):
            v = px[x, y]
            lo = min(lo, v); hi = max(hi, v)
        return max(base - lo, hi - base)

    devs = [row_dev(y) for y in range(h)]
    peak = max(devs) if devs else 0
    if peak < 25:
        return None
    cut = peak * 0.35
    rows = [y for y, d in enumerate(devs) if d > cut]
    if not rows:
        return None
    y0, y1 = rows[0], rows[-1]

    stepy = max(1, (y1 - y0) // 300)
    def col_dev(x):
        lo = hi = px[x, y0]
        for y in range(y0, y1 + 1, stepy):
            v = px[x, y]
            lo = min(lo, v); hi = max(hi, v)
        return max(base - lo, hi - base)

    cdevs = [col_dev(x) for x in range(w)]
    ccut = max(cdevs) * 0.35
    cols = [x for x, d in enumerate(cdevs) if d > ccut]
    x0, x1 = (cols[0], cols[-1]) if cols else (0, w - 1)

    if y1 - y0 < h * 0.25:
        return None
    return (x0, y0, x1 + 1, y1 + 1)


def composite_plate(order, out: Path, uroot: Path, plates: dict) -> None:
    from PIL import Image, ImageDraw
    figs = []
    for eid, _ in order:
        im = Image.open(uroot / plates[eid]).convert("RGB")
        box = _figure_bbox(im)
        if not box:
            sys.exit(f"REFUSE: could not find the figure in {plates[eid]} "
                     "(is the plate's background plain?). Pass --generate to fall back.")
        figs.append(im.crop(box))

    rel = _ratios(order)
    tallest_px = 1400
    heights = [int(tallest_px * r) for r in rel]
    scaled = [f.resize((max(1, int(f.width * hh / f.height)), hh), Image.LANCZOS)
              for f, hh in zip(figs, heights)]

    pad, gap = 90, 70
    ground = pad + tallest_px
    W = pad * 2 + sum(f.width for f in scaled) + gap * (len(scaled) - 1)
    H = ground + pad
    canvas = Image.new("RGB", (W, H), (214, 210, 202))
    x = pad
    for f in scaled:
        canvas.paste(f, (x, ground - f.height))
        x += f.width + gap
    # The ground line is the whole argument of the plate: it is what makes the
    # heights comparable rather than merely adjacent.
    ImageDraw.Draw(canvas).line([(pad // 2, ground), (W - pad // 2, ground)],
                                fill=(150, 145, 136), width=3)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    print(f"composited {len(scaled)} locked plate(s) -> {out}")
    for (eid, _), r in zip(order, rel):
        print(f"  {eid}: {r:.3f} of the tallest")


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
    # ...but ONLY when no relation already states a large one. The paragraph used to be
    # unconditional, so a canon relation reading "MUCH SHORTER THAN, a full head shorter"
    # was followed three sentences later by "draw them as two people of similar height",
    # and the prompt argued with itself. Earned 2026-08-21 (nation-of-fire, larrance-dopson
    # + clarence-avant). A relation that names its own magnitude is the authority.
    if not _states_large_gap(order):
        lines.append(
            "CALIBRATE THE DIFFERENCE CAREFULLY. A height difference described in INCHES "
            "is SMALL: the taller person's chin is still ABOVE the shorter person's eyes, "
            "and the gap between the tops of their heads is about the height of a "
            "FOREHEAD, never a whole head. Draw them as two people of similar height "
            "where one is somewhat taller, not as a tall person beside a short one."
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
    ap.add_argument("--out", help="output png (default: reference/<first>/scale-plate-<other-ids>.png)")
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing plate at the output path (default: refuse)")
    ap.add_argument("--generate", action="store_true",
                    help="GENERATE the plate with the image model instead of compositing "
                         "the locked full-body plates. Compositing is the default because "
                         "it cannot drift from the art it claims to summarise and costs "
                         "nothing; reach for this only when a character has no locked "
                         "forward-fullbody.")
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

    # The default filename NAMES THE WHOLE CAST. It used to be the first entity's plain
    # `scale-plate.png`, which meant a second pair sharing that entity overwrote the first
    # pair's plate with no warning and no backup. Earned 2026-08-21: a gary-sheng +
    # larrance-dopson plate was destroyed by a larrance-dopson + clarence-avant run, and
    # only survived because it happened to be committed.
    if a.out:
        out = Path(a.out)
    else:
        rest = "-".join(a.entities[1:])
        stem = "scale-plate" if len(a.entities) == 1 else f"scale-plate-{rest}"
        out = uroot / "reference" / a.entities[0] / f"{stem}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and not (a.dry_run or a.print_prompt or a.force):
        sys.exit(
            f"REFUSING: {out} already exists.\n"
            "A scale plate is a locked reference, and overwriting one loses the art and "
            "its recipe. Pass --force to replace it deliberately, or --out to write "
            "somewhere else."
        )

    # COMPOSITE FIRST. Only generate when a character has no full-body to composite,
    # or when the operator asks for a generated plate on purpose.
    def _fullbody(ent):
        v = ((ent.get("structured") or {}).get("sheets") or {}).get("forward-fullbody")
        return v.get("path") if isinstance(v, dict) else v

    plates = {eid: _fullbody(ent) for eid, ent in order}
    missing = [eid for eid, v in plates.items() if not v]
    if not a.generate and not missing:
        if a.dry_run or a.print_prompt:
            print(f"composite mode: {', '.join(plates.values())}")
            return 0
        composite_plate(order, out, uroot, plates)
        rc = 0
        if a.register:
            _register(order, out, uroot)
        return rc
    if not a.generate and missing:
        print(f"no locked forward-fullbody for {', '.join(missing)} — generating instead "
              "of compositing. Shoot their full-body plates for a plate that cannot drift.",
              file=sys.stderr)

    scene, negatives = build_scene(order)
    cast = []
    for eid, ent in order:
        entry = {"id": eid}
        pose = _default_pose(ent)
        if pose:
            entry["pose"] = pose
        cast.append(entry)

    # An all-register-neutral cast anchors on ITS OWN hyper-real master plate instead
    # of the universe's stylised register anchor. `anchorRef` is the existing override
    # for "the register anchor is unsuitable here", and it also suppresses the
    # anchorSubject negation, which is correct: the override is a person, not a prop.
    anchor_ref = None
    if _register_neutral_cast(order):
        sheets = (order[0][1].get("structured") or {}).get("sheets") or {}
        def _path(v):
            return v.get("path") if isinstance(v, dict) else v
        # forward-fullbody is the chain's own hero: the view exposing the most geometry.
        anchor_ref = _path(sheets.get("forward-fullbody")) or next(
            (_path(v) for v in sheets.values() if _path(v)), None)
        if not anchor_ref:
            sys.exit("REFUSE: register-neutral cast but no locked plate to anchor on.")
        print(f"register-neutral cast: anchoring on {anchor_ref} instead of the "
              f"universe register, so likeness survives the plate.")

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
            **({"anchorRef": anchor_ref} if anchor_ref else {}),
        }],
    }


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
        _register(order, out, uroot)

    return 0


def _register(order, out, uroot):
        cli_root = _skills_root().parent / "engine"
        rel = os.path.relpath(out, uroot)
        for eid, _ in order:
            # The sheet key names the OTHER people in the plate, for the same reason the
            # filename does: one entity can be in several pairings and each is a distinct
            # sheet. A bare "scale-plate" key made the second pairing overwrite the first.
            others = [e for e, _ in order if e != eid]
            shot = "scale-plate" if not others else "scale-plate-" + "-".join(others)
            r = subprocess.call(
                [sys.executable, "-m", "agenticstory.cli", "lock-shot", str(uroot),
                 eid, shot, rel, "--recipe", str(out) + ".recipe.json"],
                cwd=str(cli_root))
            if r != 0:
                print(f"  ! could not register scale-plate on {eid}", file=sys.stderr)
        print(f"registered scale-plate on: {', '.join(e for e, _ in order)}")


if __name__ == "__main__":
    raise SystemExit(main())
