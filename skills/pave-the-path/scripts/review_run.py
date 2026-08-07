#!/usr/bin/env python3
"""review_run.py — score a run transcript: how much of it was orientation?

The pave-the-path sweep reads WHAT a run wrote; this reads HOW the run spent its
calls. Input is a `runs/<id>/transcript.jsonl` in the stream-json format (one JSON
event per line; tool calls are `tool_use` blocks inside `type: "assistant"` events;
the closing `type: "result"` event carries duration and cost).

The metric that earned it (hyperagentic-age, run 2026-08-07-1701-chat-a98f): a
trivial closing-plate re-roll took 85 tool calls, and the first call that even
TOUCHED the render machinery was #57 — the run spent ~70% of its budget re-reading
the framework and canon to reconstruct context that sat in the slot's own
`.recipe.json`. A number like "orientation-heavy: 71/85 calls before the first
generation" is the evidence a human needs to decide WHICH gap to pave; eyeballing a
559-line transcript is not.

Two render metrics, deliberately distinct:
  - first TOUCH: the first tool call that even mentions the render machinery
    (reading render_cover.py counts). How long until the run found the right tool.
  - first GENERATION: the first call that EXECUTES a generation entrypoint.
    How long until the run did the work.

Usage:
  review_run.py <transcript.jsonl | runs/<id> dir> [--json]

Exit is 0 whenever the transcript parsed; the verdict is information, not a gate.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

# Executes a generation: a python/uv invocation whose argument is a generation
# entrypoint. Reading one of these files with sed/cat does NOT match.
GEN_EXEC = re.compile(
    r"(?:python3?|uv\s+run)\b[^\n|;&]*?"
    r"(generate\.py|render_spread\.py|render_cover\.py|generate_image\.py|"
    r"chain_matrix\.py|reroll_from_recipe\.py|plate\.py)\b")

# Touches the render machinery at all (reads, greps, dry runs included).
RENDER_TOUCH = re.compile(
    r"generate\.py|render_spread|render_cover|conform_cover|compose_spread|"
    r"assemble_prompt|generate_image|chain_matrix|reroll_from_recipe|"
    r"gpt.image|nano.?banana", re.I)

# Executing an entrypoint to ASK it something is still orientation. The incident's own
# call #57 ran `render_cover.py --help`; counting that as the first generation would
# have scored an 85-call meander "render-forward" and hidden the finding.
NOT_A_RENDER = re.compile(r"--help\b|--dry-run\b|--print-prompt\b")


def executes_generation(command: str) -> bool:
    return bool(GEN_EXEC.search(command)) and not NOT_A_RENDER.search(command)


def score(path: Path) -> dict:
    total = 0
    hist: Counter[str] = Counter()
    first_touch = first_gen = None
    duration_ms = cost = num_turns = None
    bad_lines = 0

    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                bad_lines += 1
                continue
            t = ev.get("type")
            if t == "assistant":
                for b in (ev.get("message") or {}).get("content") or []:
                    if not (isinstance(b, dict) and b.get("type") == "tool_use"):
                        continue
                    total += 1
                    name = b.get("name") or "?"
                    hist[name] += 1
                    blob = json.dumps(b.get("input") or {})
                    if first_touch is None and RENDER_TOUCH.search(blob):
                        first_touch = total
                    if (first_gen is None and name == "Bash"
                            and executes_generation((b.get("input") or {}).get("command") or "")):
                        first_gen = total
            elif t == "result":
                duration_ms = ev.get("duration_ms")
                cost = ev.get("total_cost_usd")
                num_turns = ev.get("num_turns")

    if total == 0:
        verdict = "empty run: zero tool calls"
    elif first_gen is None:
        verdict = f"no-generation run: 0 of {total} calls executed a render"
    else:
        before = first_gen - 1
        if before / total > 0.5:
            verdict = (f"orientation-heavy: {before}/{total} calls before the first "
                       f"generation (first at #{first_gen})")
        else:
            verdict = f"render-forward: first generation at call #{first_gen} of {total}"

    return {
        "transcript": str(path),
        "toolCalls": total,
        "histogram": dict(hist.most_common()),
        "firstRenderTouch": first_touch,
        "firstGeneration": first_gen,
        "durationMs": duration_ms,
        "totalCostUsd": cost,
        "numTurns": num_turns,
        "badLines": bad_lines,
        "verdict": verdict,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", help="a transcript.jsonl, or a runs/<id> directory holding one")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    a = ap.parse_args(argv)

    p = Path(a.run).expanduser()
    if p.is_dir():
        p = p / "transcript.jsonl"
    if not p.exists():
        sys.exit(f"review_run: no transcript at {p}")

    s = score(p)
    if a.json:
        print(json.dumps(s, indent=2))
        return 0

    print(f"run:        {p}")
    print(f"tool calls: {s['toolCalls']}"
          + (f"  ({s['numTurns']} turns)" if s['numTurns'] else ""))
    if s["durationMs"]:
        print(f"duration:   {s['durationMs'] / 1000:.0f}s"
              + (f"   cost: ${s['totalCostUsd']:.2f}" if s['totalCostUsd'] else ""))
    for name, n in s["histogram"].items():
        print(f"  {name:<14} {n}")
    print(f"first render touch: "
          + (f"call #{s['firstRenderTouch']}" if s['firstRenderTouch'] else "never"))
    print(f"first generation:   "
          + (f"call #{s['firstGeneration']}" if s['firstGeneration'] else "never"))
    print(f"VERDICT: {s['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
