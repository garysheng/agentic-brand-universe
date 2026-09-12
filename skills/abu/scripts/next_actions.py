#!/usr/bin/env python3
"""Emit the next moves on a universe as a BOARD, ready to be shown as tappable options.

WHY THIS EXISTS. The framework already knew the answer and could not say it in the shape a
person could act on. `grade.py --json` emits every issue as `{impact, dimension, what, fix}`
where `fix` is literally the verb that closes it, and `workspace.plan` already ranks them into
a headline and a small job. All of that came out of `status.py` as three lines of PROSE, in a
verb nobody invokes mid-build, at no particular moment.

So an operator finished a fan-out, had four verbs available, and had to ask. Earned over a
twelve-hour session building continental-works: after almost every explore round Gary had to
ask or guess what could happen next. His words: "ABU should leverage askuserquestion a lot
more / I keep wondering what the next possible actions are / This should feel more like a game
idk".

WHAT MAKES IT FEEL LIKE A GAME IS NOT DECORATION, IT IS THREE THINGS THIS EMITS:
a SCORE that moved (you were 74, you are 74, last time you were 71), a RANKED set of moves with
what each is worth, and the fact that they are CHOICES rather than a wall. The grader supplies
all three; this only arranges them.

IT DOES NOT ASK. It prints a board and exits. The asking belongs to the agent, which owns the
AskUserQuestion call, because a script cannot know what else is in flight in the conversation.
This emits at most four options because that is the tool's limit, ranks the first as
recommended, and leaves the fifth answer to the operator's own head, which is usually where it
lives.

    next_actions.py <universe> [--json] [--after <verb>] [--max 4]

`--after` is the hook for a verb that just finished: it suppresses the move you have obviously
just made and promotes what naturally follows it, so the board reads as a consequence rather
than as a menu that ignored what you did.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GRADER = HERE.parents[1] / "universe-doctor" / "scripts" / "grade.py"

# What naturally follows a verb. Not a workflow graph and deliberately not one: it is the
# answer to "I just did X, what does X make possible", which is a much smaller question.
# A verb absent here simply contributes no promotion, which is the correct default.
FOLLOWS: dict[str, list[str]] = {
    "explore": ["shoot-references", "create-style-pack", "on-brand-image"],
    "shoot-references": ["judge-slot", "add-relation", "make-a-work"],
    "on-brand-image": ["render-readback", "judge-slot"],
    "add-character": ["shoot-references", "add-relation"],
    "add-prop": ["shoot-references", "add-relation"],
    "add-setting": ["shoot-references", "add-relation"],
    "create-style-pack": ["shoot-references", "on-brand-image"],
    "add-story": ["compose-spec", "make-a-work"],
    "make-a-work": ["render-readback", "judge-slot"],
    "render-readback": ["reroll-slot", "judge-slot"],
}

# A one-line answer to "what would I get out of this", in the words an operator would use.
# Unmapped verbs fall back to the grader's own `what`, which is accurate and duller.
GAIN: dict[str, str] = {
    "shoot-references": "lock its plates, so every later render stops inventing it",
    "add-story": "give the canon something to be ABOUT, which is the dimension most universes score zero on",
    "add-relation": "say how two entities are connected, so a frame with both in it has a reason",
    "create-style-pack": "fix the look in one place instead of re-describing it every render",
    "make-a-work": "turn the canon into something finished you can actually show someone",
    "judge-slot": "decide whether a roll is golden, which is the only way anything becomes blessed",
    "render-readback": "check what actually arrived in a render rather than trusting it",
    "reroll-slot": "re-run a slot exactly as it was, with one line changed",
    "compose-spec": "lay out the spreads so the book has a shape before anything renders",
    "on-brand-image": "make one image through the adapter, so it carries provenance",
    "explore": "fan out on one variable and pick a direction",
    "add-generator": "draw the thing in code, for anything whose correctness is a number",
    "voice-gate": "check the manuscript against the voice rules before anything locks",
}


def grade(universe: Path) -> dict:
    if not GRADER.is_file():
        raise SystemExit(f"next_actions: grader missing at {GRADER}")
    r = subprocess.run([sys.executable, str(GRADER), str(universe), "--json"],
                       capture_output=True, text=True)
    if r.returncode != 0 and not r.stdout.strip():
        raise SystemExit(f"next_actions: {(r.stderr or r.stdout).strip()[:300]}")
    try:
        return json.loads(r.stdout)
    except ValueError:
        raise SystemExit(f"next_actions: grader returned unparseable output: {r.stdout[:200]}")


def _group(issues: list[dict]) -> list[dict]:
    """One row per VERB, carrying its best impact and an example. The grader emits hundreds."""
    by: dict[str, dict] = {}
    for i in issues:
        fix = (i.get("fix") or "").strip()
        if not fix:
            continue
        g = by.setdefault(fix, {"fix": fix, "impact": 0, "count": 0,
                                "dimension": i.get("dimension", ""), "example": ""})
        g["count"] += 1
        imp = int(i.get("impact", 0) or 0)
        if imp >= g["impact"]:
            g["impact"] = imp
            g["example"] = i.get("what", "") or g["example"]
    return sorted(by.values(), key=lambda g: (-g["impact"], -g["count"], g["fix"]))


def board(universe: Path, after: str | None = None, max_options: int = 4) -> dict:
    g = grade(universe)
    rows = _group(g.get("issues", []))

    # `--after` does two things and both matter: it drops the move just made, which would
    # otherwise sit at the top of the board of a job just finished, and it lifts what that
    # move makes possible, so the board reads as a consequence rather than as a fresh menu.
    if after:
        rows = [r for r in rows if r["fix"] != after]
        promoted = FOLLOWS.get(after, [])
        # ADD THE ISSUELESS FOLLOW-ONS FIRST, THEN SORT. Appending them after the sort put them
        # at the BOTTOM of the board, which is the opposite of promoting them: a verb has no open
        # issue most often because nobody has reached it yet, which is exactly when it is worth
        # offering. Caught by looking at the output rather than by reasoning about it.
        have = {r["fix"] for r in rows}
        for v in promoted:
            if v not in have:
                rows.append({"fix": v, "impact": 0, "count": 0, "dimension": "",
                             "example": "", "follows": after})
        rank = {v: n for n, v in enumerate(promoted)}
        rows.sort(key=lambda r: (rank.get(r["fix"], len(promoted)), -r["impact"], r["fix"]))

    options = []
    for n, r in enumerate(rows[:max_options]):
        gain = GAIN.get(r["fix"]) or r["example"] or "close an open item on this universe"
        worth = f"worth up to {r['impact']} point(s)" if r["impact"] else "no open item scored for it yet"
        # `fix` IS A HINT, NOT ALWAYS A VERB. The grader legitimately returns things like
        # "start-new-story-universe / edit universe.json" and "abu backfill-provenance (records
        # what is knowable)". Slash-prefixing those produced "/abu:abu backfill-provenance (...)",
        # which is not a command anybody can run. So the prefix is applied only to a bare
        # verb-shaped token, and everything else is passed through as the instruction it is.
        bare = bool(re.fullmatch(r"[a-z][a-z0-9-]*", r["fix"]))
        label = (f"/abu:{r['fix']}" if bare else r["fix"])
        options.append({
            "verb": r["fix"] if bare else None,
            "instruction": None if bare else r["fix"],
            "label": label + (" (Recommended)" if n == 0 else ""),
            "description": f"{gain[0].upper()}{gain[1:]}. {worth}"
                           + (f", {r['count']} open item(s)" if r["count"] > 1 else "") + ".",
            "impact": r["impact"],
            "openItems": r["count"],
            "dimension": r["dimension"],
            "recommended": n == 0,
        })

    return {
        "universe": g.get("universe", universe.name),
        "grade": g.get("grade"),
        "score": g.get("score"),
        "to100": 100 - int(g.get("score", 0) or 0),
        "after": after,
        "options": options,
        "omitted": max(0, len(rows) - len(options)),
        "askWith": ("Render these as ONE AskUserQuestion call. The labels and descriptions are "
                    "ready to use. Do NOT add a preview: it costs the visible Other row, and the "
                    "real answer here is often the fifth one, in the operator's head."),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="The next moves on a universe, as a board.")
    ap.add_argument("universe", nargs="?", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--after", default=None,
                    help="the verb that just finished; drops it and promotes what follows it")
    ap.add_argument("--max", type=int, default=4,
                    help="AskUserQuestion allows four options; more than that is a wall")
    a = ap.parse_args()

    u = Path(a.universe).expanduser().resolve()
    b = board(u, after=a.after, max_options=max(1, min(4, a.max)))

    if a.json:
        print(json.dumps(b, indent=2))
        return 0

    head = f"{b['universe']}: {b['grade']} {b['score']}/100"
    if b["to100"]:
        head += f", {b['to100']} from 100"
    print(f"\n[next] {head}")
    if b["after"]:
        print(f"[next] after /abu:{b['after']}, what it makes possible:")
    for o in b["options"]:
        print(f"  {o['label']}\n      {o['description']}")
    if b["omitted"]:
        print(f"  ...and {b['omitted']} more verb(s) with open items; --max shows more.")
    print("[next] ASK THESE AS ONE AskUserQuestion, no preview, so Other stays visible.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
