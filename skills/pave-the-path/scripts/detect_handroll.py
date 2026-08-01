#!/usr/bin/env python3
"""detect_handroll.py — did this run route around the framework?

Hand-rolling was discouraged in prose and happened anyway, five times in one session,
because nothing looked for it. Discouragement is not detection. This is detection.

It scans a scratchpad (and optionally a universe) for the mechanical signatures of an
agent that bypassed a framework verb, and for each one it NAMES THE VERB THAT OWNS IT.

Naming the verb is the whole point of the second version (2026-07-31). The first
version reported the FACT of a hand-roll, which leaves the reader to work out what they
should have called instead, and the evidence says that is not enough:
`contact_sheet.py` was promoted into `render-readback` on 2026-07-30 with a docstring
recording that the same PIL montage had been hand-rolled TEN TIMES IN ONE SESSION, and
it was hand-rolled again the very next day, in a session that had the tool installed.
A tool nobody can find is a tool nobody has. The detector is the thing that actually
fires, so the detector has to carry the pointer.

Signatures, each earned by a real script in a real scratchpad:

  * calls a provider generate script directly        -> abu:shoot-references / on-brand-image
  * hardcodes the register/style line                -> canon already owns it
  * writes a render-spec.json by hand                -> abu:compose-spec
  * montages renders into a contact sheet with PIL   -> render-readback/contact_sheet.py
  * drives render_spread.py from another script      -> render_spread.py --all --jobs N
  * authors a massing spec inline                    -> abu massing-scaffold
  * art beside a prompts.md that still says TODO     -> shoot-references/backfill_prompts.py

Exit 1 when it finds anything, so a chain step can gate on it.

  python3 detect_handroll.py <scratchpad-dir> [--universe DIR]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TODO = "TODO(author)"

# (regex, ALSO-required regex or None, what you did, the verb that already owns it).
#
# The second regex exists because some signals are only hand-rolls when combined.
# Naming `render-spec.json` is not a hand-roll (every legitimate driver reads one);
# naming it AND writing a file is. Without the pairing the detector cries wolf, and a
# detector that cries wolf gets ignored, which is the same failure as a doctor that
# always fails.
#
# A signature earns its place by having FIRED on a real hand-rolled file. Do not add
# speculative ones.
WRITES = re.compile(r"""write_text\(|json\.dump\(|open\([^)]*["']w["']""")

SIGNATURES = [
    (re.compile(r"generate_image\.py|providers/[a-z0-9-]+/generate"), None,
     "calls a provider generate script directly",
     "abu:shoot-references (matrix art) or abu:on-brand-image (one image), both of "
     "which already write provenance"),

    (re.compile(r"NEVER impasto|storybook realism|rejectedPoles", re.I), None,
     "hardcodes the register/style line",
     "canon: identity.register in universe.json, which every verb passes for you"),

    # build_spec.py, the-power-of-obeying 2026-07-31: 48KB of hand-written render-spec.
    (re.compile(r"render-spec\.json"), WRITES,
     "writes a render-spec.json by hand",
     "abu:compose-spec, which fills what canon DETERMINES, enumerates what canon "
     "CONSTRAINS, never overwrites authored scene text, and emits _caption per spread"),

    # contact.py, the-power-of-obeying 2026-07-31. Promoted the day before and missed.
    (re.compile(r"(from PIL import|import PIL).{0,600}?(contact|sheet|montage|tile)",
                re.I | re.S), None,
     "montages renders into a contact sheet with PIL",
     "abu:render-readback scripts/contact_sheet.py, which also REFUSES a partial sheet "
     "so a short sheet cannot read as 'everything I rendered'"),

    # render.py, the-power-of-obeying 2026-07-31, and the same driver one book earlier.
    (re.compile(r"render_spread\.py"), None,
     "drives render_spread.py from another script",
     "render_spread.py's own batch mode: --all (or several ids), --out-dir, --jobs N, "
     "--skip-existing"),

    # make_massing.py, the-power-of-obeying 2026-07-31: four rooms, same boilerplate.
    (re.compile(r"""def room\s*\(|["']solids["']\s*:|["']cameras["']\s*:\s*\["""), None,
     "authors a massing spec inline",
     "abu massing-scaffold <title> --size WxDxH --out spec.json, plus the public "
     "agenticstory.massing room/box/quad helpers"),
]


def scan_scratchpad(d: Path) -> list[str]:
    out = []
    if not d.is_dir():
        return out
    for f in sorted(list(d.rglob("*.sh")) + list(d.rglob("*.py"))):
        if "detect_handroll" in f.name:
            continue
        try:
            body = f.read_text(errors="ignore")
        except OSError:
            continue
        for rx, also, what, verb in SIGNATURES:
            if rx.search(body) and (also is None or also.search(body)):
                out.append(f"{f}: {what}\n      -> {verb}")
    return out


def _recipe(plate: Path):
    for c in (plate.with_suffix(plate.suffix + ".recipe.json"),
              plate.with_suffix(".recipe.json")):
        if c.exists():
            try:
                return json.loads(c.read_text())
            except (OSError, json.JSONDecodeError):
                return {}
    return None


def _has_recipe(plate: Path) -> bool:
    """RECOVERABLE means the recipe records a PROMPT, not merely that a recipe file
    exists. A `lock-shot` provenance record can carry digests and inputs with
    `"prompt": null`, and counting those as recoverable promised a repair that
    cannot happen. Caught 2026-07-31 on nsc-pendant/hero."""
    r = _recipe(plate)
    p = (r or {}).get("prompt")
    # And not a prompt that is itself a TODO stub: `abu backfill-provenance` recovers
    # a recipe by reading prompts.md, so where that file was a stub it faithfully
    # recorded the stub. Calling that recoverable promises a repair that would only
    # write the stub back, laundering the gap into something that looks like
    # provenance.
    return bool(p) and TODO not in p


def _is_code_built(plate: Path) -> bool:
    """A blueprint drawn by `abu massing` / `elevation` has NO prompt, by design.

    Its provenance is a declarative spec plus deterministic code, which is strictly
    better than a prompt: same spec in, same pixels out, no model and no cost. So an
    unfilled prompts.md body is not a defect for one of these, and flagging it was a
    false positive that made up most of what remained after a backfill. A detector
    that reports unfixable findings is one people learn to ignore.
    """
    r = _recipe(plate)
    if r is None:
        return False
    return not r.get("prompt") and bool(r.get("generator") or r.get("deterministic"))


def scan_universe(u: Path) -> list[str]:
    """Art that exists beside an unfilled prompts.md is the loudest signal: the plate
    was made, so a prompt existed, and it was not written where the framework keeps it.

    This finding is now RECOVERABLE rather than merely reportable, so it names the
    tool: the prompt is in the plate's own `.recipe.json`, and `backfill_prompts.py`
    writes it back into prompts.md.
    """
    out = []
    ref = u / "reference"
    if not ref.is_dir():
        return out
    for prompts in sorted(ref.rglob("prompts.md")):
        try:
            text = prompts.read_text(errors="ignore")
        except OSError:
            continue
        # SCOPE TO THE SHOT BODIES, exactly as chain_matrix.parse_prompts does.
        # The scaffold's own HEADER contains the string "TODO(author): replace each
        # body below", which is guidance rather than an unfilled prompt. Scanning the
        # whole file therefore reported entities whose bodies are fully authored and
        # which shoot perfectly well, and a detector stricter than the gate it warns
        # about produces findings nobody can clear. Caught 2026-07-31 when a backfill
        # repaired 18 files and the finding count did not move.
        if "\n## " not in text:
            continue

        # MATCH THE TODO TO ITS OWN PLATE, rather than counting every plate in the
        # folder. Two different things were being conflated:
        #   * a TODO body whose plate EXISTS -> the prompt that made real art is
        #     recorded nowhere. That is this detector's business, and it is fixable.
        #   * a TODO body with no plate -> simply an unshot slot. That is
        #     `abu lock-level`'s business, and reporting it here produced findings
        #     nobody could clear, because there is nothing to recover.
        # And a plate with NO heading at all is the third case, invisible until now:
        # the entity's real matrix diverged from its scaffold.
        headed, orphan_ok = {}, []
        for m in re.finditer(r"^##\s+(.*)$", text, flags=re.M):
            head = m.group(1)
            pm = re.search(r"reference/[^/]+/([A-Za-z0-9._-]+)\.png", head)
            key = pm.group(1) if pm else head.split("—")[0].split("->")[0].strip()
            nxt = text.find("\n## ", m.end())
            headed[key] = TODO in text[m.end():nxt if nxt != -1 else len(text)]

        stale = []
        for key, is_todo in headed.items():
            plate = prompts.parent / f"{key}.png"
            if is_todo and plate.exists() and not _is_code_built(plate):
                stale.append((key, _has_recipe(plate)))
        for p in sorted(prompts.parent.glob("*.png")):
            if "photos" in p.parts or p.stem in headed:
                continue
            if _has_recipe(p) and not _is_code_built(p):
                orphan_ok.append(p.stem)

        eid = prompts.parent.name
        if stale:
            rec = sum(1 for _, r in stale if r)
            fix = (f"-> abu:shoot-references scripts/backfill_prompts.py, "
                   f"{rec}/{len(stale)} recoverable from their recipes" if rec else
                   "-> UNRECOVERABLE (no recipe either): re-author prompts.md before "
                   "this entity can ever be re-shot")
            out.append(
                f"{eid}: {len(stale)} plate(s) exist but their prompts.md body still "
                f"says {TODO} ({', '.join(k for k, _ in stale)}), so the prompt that "
                f"made them is recorded nowhere\n      {fix}")
        if orphan_ok:
            out.append(
                f"{eid}: {len(orphan_ok)} locked plate(s) have NO section in prompts.md "
                f"at all ({', '.join(orphan_ok)}), so the entity's real matrix has "
                f"diverged from its scaffold\n      -> abu:shoot-references "
                f"scripts/backfill_prompts.py adopts them from their recipes")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("scratchpad")
    ap.add_argument("--universe", default=None)
    a = ap.parse_args()

    findings = scan_scratchpad(Path(a.scratchpad).expanduser())
    if a.universe:
        findings += scan_universe(Path(a.universe).expanduser())

    if not findings:
        print("detect-handroll: clean, no bypass signatures found")
        return 0

    print(f"detect-handroll: {len(findings)} sign(s) this run routed around the framework:")
    for f in findings:
        print(f"  - {f}")
    print("\n  Each is a framework GAP, not a scolding. Route them to evolve-abu:")
    print("  the verb either does not exist, or it exists and was too hard to reach.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
