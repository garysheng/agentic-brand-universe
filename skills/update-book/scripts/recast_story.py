#!/usr/bin/env python3
"""Recast a story: replace canon entity X with Y everywhere the story references it.

WHY THIS EXISTS
---------------
An entity swap is a MANUSCRIPT EVENT, not a data edit, and the framework had no
verb that treated it as one. Earned 2026-08-01 on will-there-be-ice-cream, which
did it twice by blanket string replacement:

  dustin -> toby                          (a character, re-aged sixteen to twelve)
  the-creamery-counter -> the-park-bench  (a setting, after the room would not
                                           hold its geometry across 26 spreads)

Both left debris that string replacement cannot see:
  * a spineNote still citing the ORIGIN BOOK of the character who was replaced
  * aimDiscipline pointing at beat numbers from before a renumber
  * a `plate` name that exists on the old entity and not on the new one
  * and the expensive one: FIVE BEATS whose prose still described the old
    setting's furniture (a bowl, a spoon, a counter tapped twice, a stool turned
    on) while the art already showed a bench and two cones

That last class is why this tool's real payload is the VOCABULARY SWEEP. The
structural swap is easy and a `sed` can do it. What no comparison-based check can
catch is prose that is stale in the story AND in the spec at the same time: the
caption-drift guard in book-doctor correctly reported all 73 captions verbatim,
because the two artifacts agreed with each other and were both wrong.

So this refuses to be a silent rewriter. It swaps what it can prove, and it
REPORTS what only a human can fix.

DRY RUN BY DEFAULT. Nothing is written without --apply.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

STOP = {
    "the", "a", "an", "and", "or", "of", "in", "on", "at", "to", "for", "with",
    "from", "is", "are", "it", "its", "this", "that", "one", "two", "never",
    "always", "no", "not", "any", "every", "left", "right", "viewer", "viewers",
    "front", "back", "side", "same", "other", "warm", "cool", "light", "dark",
    "plate", "plates", "render", "renders", "rendered", "scene", "camera",
    "frame", "image", "spread", "spreads", "book", "story", "canon", "entity",
    "colour", "color", "only", "must", "may", "can", "should", "behind",
    "above", "below", "across", "into", "onto", "over", "under", "through",
    "between", "their", "them", "they", "his", "her", "him", "you", "your",
    "our", "been", "being", "has", "have", "had", "was", "were", "will",
    "would", "there", "here", "when", "where", "what", "which", "who", "whom",
    "how", "why", "all", "both", "each", "some", "more", "most", "than",
    "then", "also", "just", "like", "very", "much", "many", "such", "own",
    "per", "via", "onto", "upon", "still", "again", "ever", "else",
}


def _load(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception as e:  # noqa: BLE001
        sys.exit(f"REFUSE: cannot read {p}: {e}")


def _describe(ent: dict) -> str:
    """What an entity says it is, in its own words, for a human or model to read."""
    con = ent.get("contract") or {}
    bits = [f"id: {ent.get('id')}", f"kind: {ent.get('kind')}"]
    for k in ("map", "dressing", "blocking", "scale"):
        if con.get(k):
            bits.append(f"{k}: {con[k]}")
    rules = ((ent.get("prose") or {}).get("rules") or "").strip()
    if rules:
        bits.append("rules: " + rules[:900] + ("..." if len(rules) > 900 else ""))
    return "\n".join(bits)


def review_packet(old_ent: dict, new_ent: dict, story: dict, spec: dict | None) -> str:
    """The judgment this tool refuses to fake.

    WHY THIS IS NOT A WORD LIST. Two heuristics were tried on the real case and both
    failed in the same direction. Sweeping every content word in the old entity's
    contract buried the two true hits (`counter`, `stool`) under `jerry`, `toby`,
    `gold`, `twelve` and `brand`, which come from character names, scale prose and
    NEGATIONS the entity states about itself ("no brand marks"). Subtracting the new
    entity's vocabulary removed those and left `whole`, `conversation`, `showing`,
    `question` and `kind`, because `prose.rules` is discursive English and furniture
    nouns are a tiny subset of it.

    The question is "does this sentence still describe the OLD place", which is a
    semantic judgment, not a string match. A sweep a human learns to ignore is worse
    than no sweep, so this stops guessing and emits the material for a real read.

    This follows `judge-slot`: the judgment is a ROLE, not a service. Fill it with a
    subagent, a fresh session, a human, or the next turn of the run doing the recast.
    """
    lines = [
        "RECAST REVIEW. An entity was replaced in this story. The ids are already",
        "swapped. What no tool can swap is PROSE: sentences whose words still describe",
        "the old entity while the art now follows the new one.",
        "",
        "Read every beat below. For each, answer only: does this sentence still",
        "describe the OLD entity, in a way that would read wrong beside art of the NEW",
        "one? Report the beat numbers that do, with the offending phrase and a",
        "suggested rewrite. Ignore beats that are simply unrelated to the setting.",
        "",
        "=== THE ENTITY THAT WAS REMOVED ===",
        _describe(old_ent),
        "",
        "=== THE ENTITY THAT REPLACED IT ===",
        _describe(new_ent),
        "",
        "=== BEATS ===",
    ]
    for b in story.get("beats", []) or []:
        lines.append(f"{b.get('n')}. {b.get('text')}")
    if spec:
        scenes = [s for s in spec.get("spreads", []) or [] if (s.get("scene") or "").strip()]
        if scenes:
            lines += ["", "=== RENDER-SPEC SCENE TEXT (art direction, same question) ==="]
            for s in scenes:
                lines.append(f"{s.get('id')}: {(s.get('scene') or '')[:400]}")
    return "\n".join(lines)


def swap(obj, old: str, new: str, counts: dict):
    """Swap ids in the places a story structurally references an entity."""
    if isinstance(obj, dict):
        return {k: swap(v, old, new, counts) for k, v in obj.items()}
    if isinstance(obj, list):
        return [swap(v, old, new, counts) for v in obj]
    if isinstance(obj, str) and obj == old:
        counts["ids"] = counts.get("ids", 0) + 1
        return new
    return obj


def illegal_plates(spec: dict, new_id: str, new_ent: dict) -> tuple[list[str], set[str]]:
    """Plate names a swap must never guess.

    Plate keys are per-entity ("master"/"empty" vs "wide"/"close-jerry"), so a
    swapped setting keeps a camera the new entity does not have, and the compiler
    refuses much later with no hint about why.
    """
    legal = set(((new_ent.get("structured") or {}).get("sheets") or {}).keys())
    bad = sorted({
        s.get("plate") for s in spec.get("spreads", []) or []
        if s.get("setting") == new_id and s.get("plate") and s.get("plate") not in legal
    })
    return bad, legal


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="recast-story")
    ap.add_argument("universe")
    ap.add_argument("story")
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--spec", default=None, help="the book's render-spec.json, also recast")
    ap.add_argument("--review-out", default=None,
                    help="write the prose-review packet here instead of stdout")
    ap.add_argument("--apply", action="store_true", help="write; default is a dry run")
    a = ap.parse_args(argv)

    uni = Path(a.universe)
    story_p = uni / "stories" / f"{a.story}.json"
    if not story_p.exists():
        sys.exit(f"REFUSE: no story at {story_p}")
    for eid in (a.old, a.new):
        if not (uni / "canon" / "entities" / f"{eid}.json").exists():
            sys.exit(f"REFUSE: {eid} is not a registered entity in {uni}. "
                     f"Scaffold it first; a recast must land on real canon.")

    old_ent = _load(uni / "canon" / "entities" / f"{a.old}.json")
    new_ent = _load(uni / "canon" / "entities" / f"{a.new}.json")
    story = _load(story_p)

    counts: dict = {}
    story2 = swap(story, a.old, a.new, counts)
    print(f"recast {a.old} -> {a.new} in {a.story}")
    print(f"  structural id references swapped: {counts.get('ids', 0)}")

    spec2 = None
    spec_p = Path(a.spec) if a.spec else None
    if spec_p and spec_p.exists():
        c2: dict = {}
        spec2 = swap(_load(spec_p), a.old, a.new, c2)
        print(f"  render-spec id references swapped: {c2.get('ids', 0)}")
        bad, legal = illegal_plates(spec2, a.new, new_ent)
        if bad:
            print(f"\n  PLATES THAT DO NOT EXIST ON {a.new}: {', '.join(bad)}")
            print(f"    legal plates: {', '.join(sorted(legal)) or '(none declared)'}")
            print("    Choose a camera per spread by hand. A swap must never guess a camera.")

    packet = review_packet(old_ent, new_ent, story2, spec2)
    if a.review_out:
        Path(a.review_out).write_text(packet)
        print(f"\n  wrote recast review packet -> {a.review_out}")
    else:
        print("\n" + packet)
    print("\n  THE PROSE REVIEW IS NOT OPTIONAL AND IS NOT AUTOMATED.")
    print("  Ids are swapped; sentences are not. Read the packet above and rewrite any")
    print("  beat still describing the old entity. On will-there-be-ice-cream that was")
    print("  FIVE beats (a bowl, a spoon, a counter tapped twice, a stool turned on, a")
    print("  bowl pushed across a counter) sitting under paintings of a bench and cones,")
    print("  and no comparison-based check could see it: the story and the spec agreed")
    print("  with each other and were both wrong.")

    if not a.apply:
        print("\nDRY RUN. Nothing written. Re-run with --apply to write.")
        return 2

    story_p.write_text(json.dumps(story2, indent=2, ensure_ascii=False) + "\n")
    print(f"\nwrote {story_p}")
    if spec2 is not None and spec_p:
        spec_p.write_text(json.dumps(spec2, indent=2, ensure_ascii=False) + "\n")
        print(f"wrote {spec_p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
