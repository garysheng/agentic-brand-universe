#!/usr/bin/env python3
"""The words-before-art gate, as a REFUSAL instead of a paragraph.

`voice-gate` shipped as a SKILL.md and nothing else, which means it was prose, and
prose does not bind. Every rule this framework lost during a real book run was prose;
every rule it kept was a refusal in code. A gate described in a markdown file is a gate
an agent carrying a book's momentum reads, agrees with, and does not run.

So this is the same checks, exiting non-zero.

Two of the four checks are DELIBERATELY ADVISORY, and that is not laziness. Nation of
Fire's own `capitalizeNote` says the `Spirit` rule inverts on the possessive ("his
spirit" is a man's own spirit-man and capitalizing it is a doctrinal error, not a style
win), and its `neverDisparage` list needs to know whether the narrator holds the
attitude or is attributing it to the world. Neither is decidable by grep. A checker that
BLOCKS on those trains the author to pass `--force`, and a gate everyone forces is worse
than no gate, because it also lies about having checked. So they print as REVIEW and the
exit code stays clean; the hard rules fail the build on their own.

  python3 voice_gate.py <universe> <text-file> [...]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Straight quotes and apostrophes are fine. These are the four hard rules.
EM_DASH = re.compile(r"[—–]")
FILLER = re.compile(r"\b(really|just|very|truly)\b", re.I)
# `just` has senses that are not filler and deleting them changes the meaning:
# comparative ("just as our master did"), temporal ("just then", "just before"),
# spatial ("just past the gate"), and limiting ("just enough", "just short of").
# Flagging those trains the author to ignore the gate, and an ignored gate is worse
# than no gate. Checked on the word AFTER, which is where the sense lives.
JUST_OK = re.compile(
    r"\bjust\s+(as|like|then|now|before|after|past|beyond|inside|outside|over|under|"
    r"off|above|below|short|enough|about|barely|shy)\b", re.I)
# "not X but Y" / "not X, but Y" / "isn't X, it's Y" — the performative inversion.
INVERSION = re.compile(
    r"\bnot\s+(?:only\s+)?[^.;:!?]{2,60}?,?\s+but\s+(?:rather\s+)?[^.;:!?]{2,60}",
    re.I)
QUOTED = re.compile(r"[\"“][^\"”]{0,400}[\"”]")


def rules(universe: Path) -> dict:
    try:
        return (json.loads((universe / "universe.json").read_text())
                .get("identity", {}).get("voice") or {})
    except (OSError, ValueError):
        return {}


def outside_quotes(line: str) -> str:
    """Blank out quoted spans.

    A verbatim quotation from a real person is never edited to satisfy a style rule.
    Apostle Delmar's "I just spoke it" keeps its "just", which means MERELY and is not
    filler; Jim Woodford's own words are the whole provenance of this book. Checking
    inside quotes would flag the source material and reward paraphrasing a real
    testimony into house style, which is the opposite of what provenance is for.
    """
    return QUOTED.sub(lambda m: " " * len(m.group(0)), line)


def check(path: Path, voice: dict) -> tuple[list[str], list[str]]:
    hard, review = [], []
    for n, raw in enumerate(path.read_text().split("\n"), 1):
        line = outside_quotes(raw)
        where = f"{path.name}:{n}"
        if EM_DASH.search(line):
            hard.append(f"{where}: em dash. Use a colon, a period, parentheses, or two sentences.\n    {raw.strip()[:110]}")
        ok = {m.start() for m in JUST_OK.finditer(line)}
        for m in FILLER.finditer(line):
            if m.start() in ok:
                continue
            hard.append(f"{where}: filler {m.group(0)!r}.\n    {raw.strip()[:110]}")
        if m := INVERSION.search(line):
            hard.append(f"{where}: performative 'not X but Y' inversion. State the claim.\n    {m.group(0)[:110]}")
        for term in voice.get("oneWord") or []:
            if re.search(rf"\b{re.escape(term[:6])}[ -]\w", line, re.I):
                hard.append(f"{where}: {term!r} must be one word.\n    {raw.strip()[:110]}")
        for term in voice.get("capitalize") or []:
            for m in re.finditer(rf"\b{re.escape(term.lower())}\b", line):
                # The possessive is the documented exception and is a doctrinal
                # distinction, not a typo. Report it, never block on it.
                before = line[max(0, m.start() - 24):m.start()].lower()
                poss = bool(re.search(r"\b(my|your|his|her|their|our|its|a|the man's)\s+$", before))
                review.append(f"{where}: lowercase {term.lower()!r}"
                              + (" (looks possessive, so lowercase is probably RIGHT)" if poss else
                                 " (if this means the Holy Spirit it must be capitalized)")
                              + f"\n    {raw.strip()[:110]}")
        for term in voice.get("neverDisparage") or []:
            if re.search(rf"\b{re.escape(term)}\b", line, re.I) and re.search(
                    r"\b(ridiculous|silly|absurd|pointless|embarrassing|foolish|stupid|badly|awkwardly|poorly)\b",
                    line, re.I):
                review.append(f"{where}: an act of faith ({term}) sits beside a dismissive word. "
                              f"The narrator never joins in; a character or the world may.\n    {raw.strip()[:110]}")
    return hard, review


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    universe = Path(sys.argv[1]).expanduser()
    voice = rules(universe)
    hard, review = [], []
    for f in sys.argv[2:]:
        h, r = check(Path(f).expanduser(), voice)
        hard += h
        review += r

    for label, items in (("REVIEW (not blocking, a human must read the sense)", review),
                         ("BLOCKING", hard)):
        if items:
            print(f"\n{label}: {len(items)}")
            for i in items:
                print(f"  - {i}")

    if hard:
        print(f"\nvoice-gate: BLOCKED on {len(hard)} violation(s). "
              f"Words do not lock and audio does not render until these are gone.")
        return 1
    print(f"\nvoice-gate: PASS ({len(review)} advisory item(s) to read).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
