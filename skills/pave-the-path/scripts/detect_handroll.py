#!/usr/bin/env python3
"""detect_handroll.py — did this run route around the framework?

Hand-rolling was discouraged in prose and happened anyway, five times in one session,
because nothing looked for it. Discouragement is not detection. This is detection.

It scans a scratchpad (and optionally a universe) for the mechanical signatures of an
agent that bypassed a framework verb:

  * a shell/python script that calls a provider generate script directly, which is
    `shoot-references` and `on-brand-image`'s job
  * a script that hardcodes the register/style line, which canon already owns
  * an entity whose prompts.md still says TODO(author) while its art exists, meaning
    the prompt that produced that art now lives nowhere

Exit 1 when it finds anything, so a chain step can gate on it.

  python3 detect_handroll.py <scratchpad-dir> [--universe DIR]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PROVIDER = re.compile(r"generate_image\.py|providers/[a-z0-9-]+/generate")
REGISTER = re.compile(r"NEVER impasto|storybook realism|rejectedPoles", re.I)
TODO = "TODO(author)"


def scan_scratchpad(d: Path) -> list[str]:
    out = []
    if not d.is_dir():
        return out
    for f in sorted(list(d.rglob("*.sh")) + list(d.rglob("*.py"))):
        try:
            body = f.read_text(errors="ignore")
        except OSError:
            continue
        why = []
        if PROVIDER.search(body):
            why.append("calls a provider generate script directly")
        if REGISTER.search(body):
            why.append("hardcodes the register/style line")
        if why:
            out.append(f"{f}: {', '.join(why)}")
    return out


def scan_universe(u: Path) -> list[str]:
    """Art that exists beside an unfilled prompts.md is the loudest signal: the plate
    was made, so a prompt existed, and it was not written where the framework keeps it."""
    out = []
    ref = u / "reference"
    if not ref.is_dir():
        return out
    for prompts in sorted(ref.rglob("prompts.md")):
        try:
            if TODO not in prompts.read_text(errors="ignore"):
                continue
        except OSError:
            continue
        art = [p for p in prompts.parent.glob("*.png") if "photos" not in p.parts]
        if art:
            out.append(
                f"{prompts.parent.name}: {len(art)} plate(s) exist but prompts.md still "
                f"says {TODO}, so the prompt that made them is recorded nowhere"
            )
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
