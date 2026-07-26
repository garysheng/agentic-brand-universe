#!/usr/bin/env python3
"""Generate an entity's reference matrix as a GOLDEN CHAIN. Kind-agnostic.

ONE meta-process for every entity kind (character, setting, visual-metaphor,
prop, motif), because the problem is identical in all of them: a reference matrix
is a set whose entire purpose is AGREEING WITH ITSELF, so its shots are not
independent jobs and must never be fanned out concurrently. Text alone cannot
hold a room or a face still; N shots generated in parallel from the same prose
come back as N different subjects that merely share a description.

An image model has no persistent geometry, so AN ACCEPTED IMAGE HAS TO SERVE AS
THE GEOMETRY:

    seed (hero shot, human-blessed)
      -> shot 2   conditioned on [seed]
      -> shot 3   conditioned on [seed, 2]
      -> shot 4   conditioned on [seed, 2, 3]
    the accumulated, mutually-consistent set IS the matrix.

Only ACCEPTED shots enter the conditioning set; a defect regenerates and does not
propagate, or drift compounds down the chain.

GOLDEN IS A HUMAN GATE. This script refuses to chain off a seed nobody blessed.
Bless it explicitly (after looking at it) with --bless-seed.

Usage:
  chain_matrix.py <universe> <entity-id> --print-plan
  chain_matrix.py <universe> <entity-id> --bless-seed <shot>
  chain_matrix.py <universe> <entity-id> [--seed <shot>] [--shots a,b,c]
                  [--size WxH] [--max-conditioning N] [--skip-existing] [--dry-run]
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

GEN = os.path.expanduser("~/.agents/skills/chatgpt-images/scripts/generate_image.py")

# Which shot seeds the chain, per kind: the view exposing the MOST geometry, so
# the least is left for the model to invent downstream. First match wins.
HERO_BY_KIND = {
    "character":       ["turnaround", "forward-fullbody", "man", "front", "gabr", "face-3q", "face-neutral"],
    "setting":         ["c1-wide", "wide", "establishing", "turnaround", "master", "gabr"],
    "visual-metaphor": ["master", "wide", "turnaround", "hero"],
    "prop":            ["hero", "master", "sheet", "turnaround"],
    "motif":           ["hero", "master", "sheet", "gabr"],
}

SAME_SUBJECT = (
    "CRITICAL: every reference image after the first shows THE SAME SINGLE SUBJECT, already locked. "
    "Reproduce it EXACTLY as those images show it: the same shapes, proportions, materials, colors, "
    "markings, and the same relative placement of every element. Do NOT redesign, restyle, recolor, "
    "resize, add, or remove anything. Change ONLY the camera position and framing."
)

# For a real-person entity the PHOTOGRAPHS are the ground truth, and the accepted
# goldens are only paintings OF that truth. Without this the chain builds every
# downstream shot from a painting of a painting and the likeness drifts off the
# real face while every plate still looks internally consistent, which is the
# worst kind of failure because nothing looks wrong until someone who knows the
# person sees it.
REAL_PERSON = (
    "IDENTITY GROUND TRUTH: the PHOTOGRAPHS among the reference images are the REAL PERSON this "
    "subject depicts. Build the likeness faithfully and exactly from those photographs: bone "
    "structure, hairline, hair colour and texture, eye shape, nose, mouth, and the way the face "
    "creases when it smiles. Where a painted reference and a photograph disagree about the face, "
    "THE PHOTOGRAPH WINS. Keep the painterly rendering of the painted references and the likeness "
    "of the photographs."
)


class Refuse(Exception):
    pass


def load(p: Path):
    with open(p) as f:
        return json.load(f)


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def _split_ids(s: str) -> list[str]:
    return [x.strip().strip("`") for x in re.split(r"[,\s]+", s) if x.strip().strip("`")]


def parse_prompts(md: Path) -> dict:
    """reference/<id>/prompts.md -> {shot: prompt}. A shot is an '## <name>' or
    '## <label> -> `reference/<id>/<name>.png`' heading; its body is the prompt."""
    return parse_prompts_full(md)["prompts"]


def parse_prompts_full(md: Path) -> dict:
    """Parse prompts.md into {prompts, negatives, refs}.

    Beyond the shot bodies, the file may declare two things the chain must honour:

      **Negatives (every shot):** a, b, c
          Entity-specific negatives, MERGED with the universe's rejectedPoles.
          Before this was read, a prompts.md could state a negative that never
          reached the model, so the file implied a guarantee it did not provide.

      **Refs (every shot):** other-entity-id, ...     (header, applies to all shots)
      REFS: other-entity-id, ...                      (inside a shot body, that shot only)
          CROSS-ENTITY references. A spread or plate that shows another canon
          entity must be conditioned on THAT entity's locked art, never redrawn
          from prose. REFS lines are stripped out of the prompt text.
    """
    if not md.exists():
        raise Refuse(f"no prompts.md at {md}")
    text = md.read_text()

    negatives: list[str] = []
    m = re.search(r"^\*\*Negatives[^:]*:\*\*\s*(.+)$", text, flags=re.M)
    if m:
        negatives = [n.strip().rstrip(".") for n in m.group(1).split(",") if n.strip()]

    header_refs: list[str] = []
    m = re.search(r"^\*\*Refs[^:]*:\*\*\s*(.+)$", text, flags=re.M)
    if m:
        header_refs = _split_ids(m.group(1))

    out, refs, sizes, cur, buf, cur_refs = {}, {}, {}, None, [], []
    # A shot's body is every line until the NEXT level-2 heading, so ANY trailing
    # prose, sub-heading, or horizontal rule after the last shot is silently
    # appended to that shot's prompt. That failure is invisible in the plan and
    # only shows up in the art: on 2026-07-26 four era-shot sections parked at
    # "###" after the last shot turned signature-pose into a 4397-char prompt
    # describing nine different images, and the model returned a 3x3 contact
    # sheet that leaked a child, a superseded era wardrobe, and a banned pendant
    # shape into a base-matrix plate. Refuse loudly instead: non-matrix content
    # belongs in its own file.
    contaminated = {}
    for line in text.splitlines():
        m = re.match(r"^##\s+(.*)$", line)
        if m:
            if cur:
                out[cur] = " ".join(buf).strip()
                refs[cur] = list(dict.fromkeys(header_refs + cur_refs))
            head = m.group(1)
            path = re.search(r"reference/[^/]+/([A-Za-z0-9._-]+)\.png", head)
            cur = path.group(1) if path else head.split("—")[0].split("->")[0].strip()
            # PER-SHOT SIZE, declared in the heading as "(WxH)". A reference matrix
            # legitimately MIXES aspects: full-body and profiles want portrait, while
            # multi-panel sheets (expressions, era/turnaround rows) want landscape.
            # One --size for the whole matrix letterboxes the sheets into the wrong
            # canvas with dead bands, wasting most of the frame. The sizes were
            # already written here; the chain just was not reading them.
            sz = re.search(r"\((\d{3,5})\s*[xX×]\s*(\d{3,5})\)", head)
            if sz:
                sizes[cur] = f"{sz.group(1)}x{sz.group(2)}"
            buf, cur_refs = [], []
        elif cur:
            r = re.match(r"^\s*REFS:\s*(.+)$", line, flags=re.I)
            if r:
                cur_refs += _split_ids(r.group(1))
            else:
                stripped = line.strip()
                if re.match(r"^#{3,}\s+\S", stripped) or re.fullmatch(r"-{3,}|\*{3,}|_{3,}", stripped):
                    contaminated.setdefault(cur, []).append(stripped[:60])
                buf.append(stripped)
    if cur:
        out[cur] = " ".join(buf).strip()
        refs[cur] = list(dict.fromkeys(header_refs + cur_refs))

    prompts = {k: v for k, v in out.items() if v}
    if contaminated:
        detail = "; ".join(f"{k} swallowed {v!r}" for k, v in contaminated.items())
        raise Refuse(
            "prompts.md has non-shot content inside a shot body, which is silently appended to that "
            f"shot's prompt and corrupts its art: {detail}. A shot body runs until the NEXT '## ' "
            "heading, so sub-headings, appendices, and horizontal rules cannot live after the last "
            "shot. Move that content to its own file (e.g. prompts-era.md for alt-look shots, which "
            "lock with `lock-shot --look <key>` and are never base-matrix shots).")
    return {"prompts": prompts,
            "negatives": negatives,
            "sizes": {k: sizes[k] for k in prompts if k in sizes},
            "refs": {k: refs.get(k, []) for k in prompts}}


def entity_ref_images(uroot: Path, eid: str) -> list[str]:
    """Absolute paths of another entity's LOCKED reference art, for cross-entity conditioning.

    Refuses on an unlocked/missing entity: passing prose instead of real art is the
    exact failure this exists to prevent (a mark rendered without its mark).
    """
    ent_path = uroot / "canon" / "entities" / f"{eid}.json"
    if not ent_path.exists():
        raise Refuse(f"REFS names '{eid}', which is not a canon entity")
    ent = load(ent_path)
    st = ent.get("structured") or {}
    sheets = st.get("sheets") or {}
    wanted = [s for s in (st.get("requiredForRender") or []) if sheets.get(s)]
    if not wanted:
        for k in ("master", "hero", "forward-fullbody", "sheet", "turnaround"):
            if sheets.get(k):
                wanted = [k]
                break
    if not wanted:
        raise Refuse(f"REFS names '{eid}', which has no locked reference art to pass")
    paths = []
    for s in wanted:
        p = (uroot / sheets[s]).resolve()
        if not p.exists():
            raise Refuse(f"REFS '{eid}.{s}' -> {p} (NOT ON DISK)")
        paths.append(str(p))
    return paths


def pick_seed(kind: str, shots: list[str], override: str | None) -> str:
    if override:
        if override not in shots:
            raise Refuse(f"--seed '{override}' is not one of: {', '.join(shots)}")
        return override
    for pref in HERO_BY_KIND.get(kind, []):
        for s in shots:
            if s == pref or s.startswith(pref):
                return s
    return shots[0]


def marker(refdir: Path, shot: str) -> Path:
    return refdir / f"{shot}.golden.json"


def build_plan(uroot: Path, eid: str, seed_override=None, shots_override=None):
    uni = load(uroot / "universe.json")
    reg = (uni.get("identity") or {}).get("register") or {}
    anchor = reg.get("anchor")
    if not anchor:
        raise Refuse("identity.register.anchor is null: the universe style is not locked; do not generate")

    ent = load(uroot / "canon" / "entities" / f"{eid}.json")
    kind = ent.get("kind", "character")
    refdir = uroot / "reference" / eid
    parsed = parse_prompts_full(refdir / "prompts.md")
    prompts = parsed["prompts"]

    shots = shots_override or list(prompts.keys())
    missing = [s for s in shots if s not in prompts]
    if missing:
        raise Refuse(f"no prompt block for: {', '.join(missing)}")

    if not shots:
        raise Refuse(
            f"no shot blocks found in {refdir / 'prompts.md'}.\n"
            "Every shot MUST be a level-2 heading of the form:\n"
            "  ## <shot-name> -> `reference/<entity>/<shot-name>.png`"
        )

    # The shot headings in prompts.md MUST be the entity's declared sheet names.
    # Without this check a prompts.md authored with '###' shot blocks parses its
    # PROSE headings as the shot list, and the chain silently generates garbage
    # conditioned on nothing instead of failing. Refuse loudly instead.
    declared = set((ent.get("structured") or {}).get("sheets") or {})
    if declared:
        bogus = [s for s in shots if s not in declared]
        if bogus:
            raise Refuse(
                f"prompts.md shot headings do not match {eid}'s declared sheets.\n"
                f"  parsed:   {', '.join(shots)}\n"
                f"  declared: {', '.join(sorted(declared))}\n"
                f"  unknown:  {', '.join(bogus)}\n"
                "Every shot MUST be a level-2 heading of the form:\n"
                "  ## <shot-name> -> `reference/<entity>/<shot-name>.png`\n"
                "Prose sections must be level-3 or deeper, or they are read as shots."
            )

    # A real person's photo stack is ground truth for the likeness and must ride
    # along on EVERY shot, not just the seed. Refuse on a declared-but-missing
    # photo, the same discipline as a missing cross-entity ref: a path that does
    # not resolve is a silent downgrade to "invent the face from prose".
    photos = []
    for rel in ((ent.get("realPerson") or {}).get("photoStack") or []):
        p = (uroot / rel).resolve()
        if not p.exists():
            raise Refuse(f"{eid}.realPerson.photoStack -> {p} (NOT ON DISK)")
        if p.is_dir():
            raise Refuse(f"{eid}.realPerson.photoStack -> {p} is a DIRECTORY, not an image")
        photos.append(str(p))

    seed = pick_seed(kind, shots, seed_override)
    rest = [s for s in shots if s != seed]
    return {
        "entity": eid, "kind": kind, "anchor": anchor, "refdir": refdir,
        "photos": photos,
        "seed": seed, "order": [seed] + rest, "prompts": prompts,
        # universe rejectedPoles FIRST, then the entity's own negatives from
        # prompts.md. Both reach the model; neither is silently dropped.
        "negatives": list(dict.fromkeys(
            list(reg.get("rejectedPoles", [])) + parsed["negatives"])),
        "refs": parsed["refs"],
        "sizes": parsed.get("sizes", {}),
        "uroot": uroot,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("universe")
    ap.add_argument("entity")
    ap.add_argument("--seed")
    ap.add_argument("--shots")
    ap.add_argument("--size", default="1536x1024",
                    help="FALLBACK size only. A shot whose prompts.md heading declares "
                         "'(WxH)' uses that instead, so one matrix can mix portrait "
                         "full-bodies with landscape multi-panel sheets.")
    ap.add_argument("--max-conditioning", type=int, default=4, metavar="N",
                    help="Cap on accepted goldens passed as conditioning (default 4). "
                         "The blessed SEED is always kept and the most recent N-1 "
                         "accepted shots ride along. Unbounded accumulation makes every "
                         "step a larger upload than the last until the final shots of a "
                         "big matrix time out. 0 disables the cap.")
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--print-plan", action="store_true")
    ap.add_argument("--bless-seed", metavar="SHOT",
                    help="record HUMAN approval of the seed so the chain may proceed")
    args = ap.parse_args()

    uroot = Path(args.universe)
    try:
        plan = build_plan(uroot, args.entity, args.seed,
                          args.shots.split(",") if args.shots else None)
    except Refuse as e:
        print(f"REFUSE: {e}", file=sys.stderr)
        return 2

    refdir, seed = plan["refdir"], plan["seed"]

    if args.bless_seed:
        shot = args.bless_seed
        img = refdir / f"{shot}.png"
        if not img.exists():
            print(f"REFUSE: cannot bless '{shot}': {img} does not exist", file=sys.stderr)
            return 2
        marker(refdir, shot).write_text(json.dumps(
            {"shot": shot, "sha256_16": sha(img), "blessedBy": "human",
             "note": "Golden is a human gate. This marker records that a person looked at this "
                     "seed and approved it; the chain conditions every later shot on it."}, indent=1))
        print(f"blessed seed: {shot}")
        return 0

    if args.print_plan or args.dry_run:
        print(f"entity={plan['entity']} kind={plan['kind']}")
        print(f"seed (hero) = {seed}")
        for i, s in enumerate(plan["order"]):
            # Show the ACTUAL conditioning window, not every prior shot: a plan that
            # advertises conditioning the run will not perform is worse than no plan.
            prior = plan["order"][:i]
            if args.max_conditioning and len(prior) > args.max_conditioning:
                prior = [prior[0], "..."] + prior[-(args.max_conditioning - 1):]
            cond = "HUMAN-BLESSED SEED" if i == 0 else \
                   "anchor + " + ", ".join(prior)
            xrefs = plan["refs"].get(s) or []
            if xrefs and i > 0:
                cond += " + refs(" + ", ".join(xrefs) + ")"
            sz = plan["sizes"].get(s, args.size)
            print(f"  {i+1}. {s:<18} [{sz}] conditioned on: {cond}")
        if plan["negatives"]:
            print("negatives: " + ", ".join(plan["negatives"]))
        blessed = marker(refdir, seed).exists()
        print(f"seed blessed: {blessed}" + ("" if blessed else "  <-- chain will REFUSE"))
        return 0

    # The human gate. Golden is not something the agent may award itself.
    if not marker(refdir, seed).exists():
        print(f"REFUSE: seed '{seed}' is not blessed. Generate/iterate it alone, have a human look "
              f"at it, then: chain_matrix.py <universe> {plan['entity']} --bless-seed {seed}",
              file=sys.stderr)
        return 2

    goldens = [str((refdir / f"{seed}.png").resolve())]
    if not Path(goldens[0]).exists():
        print(f"REFUSE: blessed seed image missing: {goldens[0]}", file=sys.stderr)
        return 2

    neg = ("NEGATIVES: " + ", ".join(plan["negatives"]) + ".") if plan["negatives"] else ""
    anchor_abs = str((uroot / plan["anchor"]).resolve())

    for shot in plan["order"][1:]:
        out = refdir / f"{shot}.png"
        if args.skip_existing and out.exists():
            print(f"{shot}: exists, skip")
            goldens.append(str(out.resolve()))
            continue
        prompt = " ".join(x for x in [plan["prompts"][shot], SAME_SUBJECT,
                                      REAL_PERSON if plan["photos"] else "", neg] if x)
        # Per-shot size when prompts.md declared one; --size is only the fallback.
        shot_size = plan["sizes"].get(shot, args.size)
        # CONDITIONING WINDOW. Identity is carried by the blessed seed plus the few
        # most recent accepted shots, NOT by every golden ever made: the back view
        # adds payload, not likeness. Passing all of them grows the request at every
        # step until the tail of a big matrix dies on an API timeout, which is the
        # worst place to fail because those shots are the most expensive to redo.
        cond = goldens
        if args.max_conditioning and len(goldens) > args.max_conditioning:
            cond = [goldens[0]] + goldens[-(args.max_conditioning - 1):]
        cmd = ["uv", "run", GEN, "--prompt", prompt, "--filename", str(out),
               "--size", shot_size, "--quality", "high", "--no-open",
               "--input-image", anchor_abs]
        # photographs BEFORE the painted goldens: the likeness is the thing the
        # chain must not drift on, and later references carry more weight.
        for ph in plan["photos"]:
            cmd += ["--input-image", ph]
        for g in cond:
            cmd += ["--input-image", g]
        # Cross-entity refs: another entity in frame is conditioned on ITS locked
        # art, never redrawn from prose.
        for other in plan["refs"].get(shot, []):
            for p in entity_ref_images(plan["uroot"], other):
                cmd += ["--input-image", p]
        rc = subprocess.run(cmd).returncode
        if rc != 0 or not out.exists():
            print(f"{shot}: FAILED rc={rc}; chain STOPS (a defect must not propagate)", file=sys.stderr)
            return 1
        # provenance travels with the asset (nothing is a mystery)
        (refdir / f"{shot}.recipe.json").write_text(json.dumps({
            "shot": shot, "entity": plan["entity"], "kind": plan["kind"],
            "model": "gpt-image-2", "size": shot_size, "prompt": prompt,
            "anchor": {"path": plan["anchor"], "sha256_16": sha(Path(anchor_abs))},
            "photoStack": [{"path": p, "sha256_16": sha(Path(p))} for p in plan["photos"]],
            "conditionedOn": [{"path": g, "sha256_16": sha(Path(g))} for g in cond],
            "method": ("golden-chain (sequential; each shot conditions on the blessed seed "
                       f"plus the most recent accepted shots, window={args.max_conditioning or 'unbounded'})"),
        }, indent=1))
        print(f"{shot}: OK (conditioned on {len(cond)} golden(s), size {shot_size})")
        goldens.append(str(out.resolve()))

    print(f"CHAIN COMPLETE: {len(goldens)} mutually-consistent shot(s). "
          f"Read back each, then lock-shot the passers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
