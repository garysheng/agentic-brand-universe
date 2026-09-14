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

And one leak, read RETROSPECTIVELY:
  - COMMANDS SHOWN TO THE OPERATOR. SPEC v0.49 made the front door's one hard rule --
    a person never sees a shell command -- real in code, on every path where the
    FRAMEWORK hands a string to a person: `workspace.command_in()` is the detector and
    `humanize()` drops anything command-shaped. That closes the framework's half. The
    other half is the agent speaking on its own account, in its own prose, which no
    framework string passes through and no gate can see from inside the run.

    So it is caught afterwards, in the transcript, where the evidence already sits.
    Retrospective on purpose: it adds no surface, polices nothing mid-run, and fits the
    sweep this skill already is. The detector is IMPORTED rather than rewritten, because
    two opinions about what counts as a command is exactly how one of them goes stale --
    and it means a script by name, a flag and a shell operator all count here for the
    same reason they count at the front door.

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


def _abu_root(start=None) -> Path:
    """Walk up for a marker, never count parents: a fixed depth encodes ONE layout and
    this runs from a clone and from a plugin cache. Same finder as next_actions.py."""
    p = Path(start or __file__).resolve()
    for c in [p, *p.parents]:
        if (c / "engine" / "agenticstory").is_dir():
            return c
    raise SystemExit("review_run: cannot locate the ABU root from " + str(p))


sys.path.insert(0, str(_abu_root() / "engine"))
from agenticstory.workspace import command_in  # noqa: E402

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


def _excerpt(text: str, span: str, width: int = 90) -> str:
    """The sentence around the leak, so a reader can see what was being said.

    A bare span ("`abu validate`") is not enough to act on: the fix depends on whether the
    agent was instructing the operator, narrating itself, or quoting a refusal.
    """
    flat = " ".join(str(text).split())
    i = flat.find(span)
    if i < 0:
        return flat[:width]
    start = max(0, i - width // 3)
    out = flat[start:start + width]
    return ("..." if start else "") + out + ("..." if start + width < len(flat) else "")


def shown_to_operator(ev: dict) -> list[str]:
    """Every TEXT block of one assistant event: what the operator actually read.

    Tool inputs are excluded on purpose. A command the agent RUNS is the job; a command the
    agent TYPES AT THE OPERATOR is the rule broken. Thinking blocks are excluded for the
    same reason: nobody reads them.
    """
    return [b.get("text") or "" for b in (ev.get("message") or {}).get("content") or []
            if isinstance(b, dict) and b.get("type") == "text"]


def score(path: Path) -> dict:
    total = 0
    hist: Counter[str] = Counter()
    first_touch = first_gen = None
    duration_ms = cost = num_turns = None
    bad_lines = 0
    messages = 0
    leaks: list[dict] = []

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
                for text in shown_to_operator(ev):
                    messages += 1
                    span = command_in(text)
                    if span:
                        leaks.append({"message": messages, "span": span,
                                      "excerpt": _excerpt(text, span)})
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
        "messagesToOperator": messages,
        "commandsShownToOperator": leaks,
        "commandVerdict": command_verdict(leaks, messages),
        "verdict": verdict,
    }


def command_verdict(leaks: list[dict], messages: int) -> str:
    """The front door's one hard rule, scored after the fact.

    Says what to DO, because the fix differs by case and naming the count alone reads as
    trivia: a command in a REPORT should have been the outcome in plain language, and a
    command as an INSTRUCTION is a verb the operator should never have had to type.
    """
    if not leaks:
        return f"clean: no shell command reached the operator across {messages} message(s)"
    spans = ", ".join(sorted({str(x["span"]) for x in leaks})[:4])
    return (f"{len(leaks)} of {messages} message(s) showed the operator a shell command "
            f"({spans}). The front door's rule is that a person never sees one: say the "
            f"outcome instead, or route the work through the verb that owns it.")


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
    print(f"COMMANDS SHOWN: {s['commandVerdict']}")
    # Show the first few verbatim. A count is a number to nod at; the sentence the operator
    # actually read is the thing somebody can fix.
    for leak in s["commandsShownToOperator"][:5]:
        print(f"  msg #{leak['message']}  {leak['span']}\n      {leak['excerpt']}")
    if len(s["commandsShownToOperator"]) > 5:
        print(f"  ...and {len(s['commandsShownToOperator']) - 5} more; --json has them all.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
