#!/usr/bin/env python3
"""Scaffold and RE-SYNC a render-spec from a StorySpec.

The gap this fills: a story knows its beats, their locations and who is in them, and a
render-spec restates all of it by hand. Every book therefore grew a bespoke authoring
script, and those scripts rot: the spec gets hand-edited afterwards, the script does not,
and re-running it silently reverts the edits. That happened on 2026-07-30 in
nation-of-fire, where the stale generator still carried an identity-overriding `bake` and
crowd prose that six hours of fixes had removed.

So this is NOT a spec generator. It fills what canon DETERMINES, enumerates what canon
merely CONSTRAINS, and never touches what a human AUTHORED.

  derived   id, setting, cast membership, preamble, size    refreshed on every run
  chosen    plate, pose, look                               enumerated, never chosen for you
  authored  scene, negatives, bake, flags                   never modified without --force

Re-running after adding a beat inserts the new spread and leaves every authored scene
alone. A spread present in the spec but not in the story (a cover, a closing plate, a beat
you removed) is REPORTED and never deleted.

  python3 compose_spec.py <universe> <story-id> --book <folder> --out render-spec.json
"""
import argparse, json, os, sys

DERIVED = ("id", "setting")
AUTHORED = ("scene", "negatives", "size", "style", "anchorRef", "settingRule",
            "allowUncast", "allowMultiPanel", "allowPlatelessSetting", "allowIdentityOverride")
CHOSEN = ("plate", "pose", "look", "bake")

def jload(p):
    with open(p) as f:
        return json.load(f)

def entity(uroot, eid):
    p = os.path.join(uroot, "canon", "entities", f"{eid}.json")
    return jload(p) if os.path.exists(p) else None

def plates_for(ent):
    if not ent:
        return []
    sheets = (ent.get("structured") or {}).get("sheets") or {}
    return [k for k in sheets if k not in ("blueprint", "scalePlate")]

def poses_for(ent):
    if not ent:
        return []
    return list((((ent.get("structured") or {}).get("render") or {}).get("poses") or {}).keys())

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("universe"); ap.add_argument("story")
    ap.add_argument("--book", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--provider", default="gpt-image-2")
    ap.add_argument("--size", default="1536x1024")
    ap.add_argument("--no-hints", action="store_true",
                    help="omit the _caption/_choices advisory keys from the emitted spec")
    ap.add_argument("--force", action="store_true",
                    help="also overwrite AUTHORED fields from scratch. Destroys hand-written scenes.")
    a = ap.parse_args()

    uroot = os.path.expanduser(a.universe)
    story = jload(os.path.join(uroot, "stories", f"{a.story}.json"))
    beats = story.get("beats") or []
    if not beats:
        sys.exit(f"compose-spec: story '{a.story}' has no beats")

    out = os.path.expanduser(a.out)
    prior = jload(out) if os.path.exists(out) else {}
    by_id = {s.get("id"): s for s in prior.get("spreads", []) if isinstance(s, dict)}

    spreads, created, refreshed, notes = [], [], [], []
    for b in beats:
        sid = f"spread-{int(b['n']):02d}"
        old = {} if a.force else dict(by_id.get(sid) or {})
        sp = {"id": sid}
        # SETTING IS CARRIED FORWARD, NOT BLINDLY REFRESHED.
        #
        # It was classed as derived, so a re-sync rewrote it from beat.location every run.
        # A render-spec legitimately diverges from its story: a beat says "their house" and
        # the book stages it in one specific room that did not exist when the beat was
        # written. Refreshing silently reverted 16 spreads of gain-everything-lose-nothing
        # to a banned room, and the run REPORTED "plates altered: NONE" because only the
        # setting had moved. Earned 2026-07-30, by this tool, on the book it was built for.
        #
        # So: fill it when absent, keep it when present, and REPORT the divergence loudly.
        loc = b.get("location")
        existing = old.get("setting")
        if existing and loc and existing != loc:
            notes.append(f"{sid}: DIVERGENCE, spec stages this in '{existing}' but the beat "
                         f"says '{loc}'. Keeping '{existing}'. Fix the story's beat.location "
                         "if the spec is right, or the spec if the story is right.")
        chosen_setting = existing or loc
        if chosen_setting:
            sp["setting"] = chosen_setting
        ent = entity(uroot, chosen_setting) if chosen_setting else None

        # CHOSEN: carried forward if already chosen, never chosen on the author's behalf.
        sp["plate"] = old.get("plate") if "plate" in old else None
        if chosen_setting and sp.get("plate") and sp["plate"] not in plates_for(ent):
            notes.append(f"{sid}: plate '{sp['plate']}' is NOT a sheet of setting "
                         f"'{chosen_setting}' (has: {plates_for(ent) or 'none'}). The render "
                         "will refuse, or silently fall back to a filename that may not exist.")
        if chosen_setting and not sp.get("plate"):
            notes.append(f"{sid}: setting '{chosen_setting}' has no plate chosen "
                         f"(available: {plates_for(ent) or 'NONE - shoot a shot list'})")

        # WHEN this spread happens (SPEC v0.18). DERIVED when the beat records it,
        # CHOSEN otherwise, and never invented: a wrong `when` is worse than none,
        # because it would refuse the correct look.
        if b.get("when") is not None:
            sp["when"] = b["when"]
        elif "when" in old:
            sp["when"] = old["when"]

        old_cast = {c.get("id"): c for c in (old.get("cast") or []) if isinstance(c, dict)}
        cast = []
        for cid in (b.get("characters") or []):
            cent = entity(uroot, cid)
            prev = old_cast.get(cid, {})
            entry = {"id": cid}
            for k in CHOSEN:
                if k in prev:
                    entry[k] = prev[k]
            # A character with ERA-WINDOWED looks and a dated spread should have its
            # look chosen deliberately. Say which look the date makes legal, rather
            # than choosing it: compose-spec never chooses.
            looks = ((cent.get("structured") or {}).get("altLooks") or {})
            if sp.get("when") is not None and not entry.get("look"):
                windows = {k: (v or {}).get("validFor") for k, v in looks.items()}
                if any(isinstance(w, dict) for w in windows.values()):
                    legal = [k for k, w in windows.items()
                             if isinstance(w, dict)
                             and (w.get("from") is None or sp["when"] >= w["from"])
                             and (w.get("to") is None or sp["when"] <= w["to"])]
                    notes.append(
                        f"{sid}: '{cid}' has era-windowed looks and this spread is set at "
                        f"when={sp['when']}; no look is selected, so the DEFAULT look renders. "
                        + (f"Legal at that date: {', '.join(legal)}." if legal
                           else "No alt look is legal at that date, so the default must be."))

            avail = poses_for(cent)
            if avail and not entry.get("pose") and not entry.get("look"):
                entry["pose"] = None
                notes.append(f"{sid}: '{cid}' has {len(avail)} poses and none selected "
                             f"({', '.join(avail[:6])}{'...' if len(avail) > 6 else ''})")
            if not a.no_hints and avail:
                entry["_choices"] = avail
            cast.append(entry)
        for cid, prev in old_cast.items():
            if cid not in (b.get("characters") or []):
                cast.append(prev)
                notes.append(f"{sid}: '{cid}' is cast in the spec but not in the beat; kept, not deleted")
        sp["cast"] = cast

        # AUTHORED: preserved verbatim.
        for k in AUTHORED:
            if k in old:
                sp[k] = old[k]
        sp.setdefault("scene", "")
        if not sp["scene"]:
            notes.append(f"{sid}: scene is empty and must be authored")
        if not a.no_hints:
            sp["_caption"] = b.get("text", "")

        (created if sid not in by_id else refreshed).append(sid)
        spreads.append(sp)

    kept = [s for sid, s in by_id.items() if sid not in {x["id"] for x in spreads}]
    for s in kept:
        spreads.append(s)
        notes.append(f"{s.get('id')}: in the spec but not in the story; kept, not deleted")

    spec = dict(prior)
    spec.update({"book": a.book, "story": a.story,
                 "provider": prior.get("provider", a.provider),
                 "size": prior.get("size", a.size),
                 "preamble": prior.get("preamble", {}), "spreads": spreads})
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    with open(out, "w") as f:
        json.dump(spec, f, indent=2)

    print(f"[compose-spec] {len(spreads)} spread(s) -> {out}")
    print(f"  created {len(created)}, refreshed {len(refreshed)}, carried {len(kept)}")
    if notes:
        print(f"  {len(notes)} thing(s) need a human:")
        for n in notes:
            print(f"    - {n}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
