# Quickstart

The smallest useful slice of this framework is **a look plus a gate**, and it needs no universe, no
canon, and no entities. If you are making a zine, a deck, a set of page heroes, or anything else
where the *subject changes every time but the style must not*, that slice is the whole thing you
need. Start there. Add canon later, and only if something must render **identically** everywhere.

## What you need

| | Why |
|---|---|
| **Python 3.10+** | The engine. Stdlib only, no install, no network. |
| **Claude Code** | The skills are Claude Code skills; the agent reads them and drives the engine. |
| **An image API key** | `OPENAI_API_KEY` for `gpt-image-2`, or `GEMINI_API_KEY` for `nano-banana-pro`. |
| **`uv`** | How the provider scripts are invoked. |
| **git** | Not optional. A canon you cannot diff is not version-controlled, which is the point. |

## Install

```bash
git clone https://github.com/garysheng/agentic-brand-universe.git
cd agentic-brand-universe
./run-tests.sh          # no API key, no network, generates nothing. Expect ALL GREEN.
```

Then make the skills visible to Claude Code:

```bash
mkdir -p ~/.claude/skills
for s in skills/*/; do ln -sfn "$PWD/$s" ~/.claude/skills/"$(basename "$s")"; done
```

> **Known gap (2026-07-30).** The provider adapter at
> `skills/on-brand-image/scripts/generate.py` resolves two image-generation scripts by absolute
> path (`~/.agents/skills/chatgpt-images/`, `~/.claude/skills/nano-banana-pro/`) and the engine
> path by another. Those are not vendored in this repo yet, so image generation will not run on a
> fresh clone until you supply them or edit those paths. Everything else — the engine, the gates,
> validation, the whole test suite — runs clean. Tracked as the portability fix.

## The zine path, end to end

**1. Bless 3-8 images you already like.** They can come from anywhere, including a chat session.
The look lives in the references, not in the wording, so this step is the real work.

**2. Turn them into a Style Pack.** Ask Claude Code:

> use create-style-pack on these images

You will be asked for the style line, palette, **rejected poles** (what this is NOT), and the
**gate** (checkable assertions about the pixels). The gate is the load-bearing half; the scaffolder
refuses to write a pack without one, because a pack with no gate is a mood board.

Two rules that will save you a rebuild:

- **The anchor must be content-neutral** — a swatch of palette, light and finish with no subject. A
  busy anchor leaks its content into every render.
- **Reject a specific failure, never a whole visual mode.** A pole broad enough to name a capability
  deletes that capability, and no amount of prompting gets it back.

**3. Generate every plate from the pack.**

> use on-brand-image with my pack to make: <the scene>

The anchor goes in first, the rejected poles are compiled into negatives, and the output is read
back against your gate. A defect means regenerate from scratch, never stack an edit pass. Each image
writes a `.recipe.json` beside it as a side effect of generating, so provenance is not a step you
have to remember.

**4. Commit after every accepted image.** That is the version control that makes the look
recoverable when issue 4 drifts from issue 1.

## When to graduate to a universe

Only when a **specific thing must render identically everywhere** — a recurring character, a
location you return to, an object with a load-bearing detail. Then:

```bash
cd engine
python3 -m agenticstory.cli init ../my-universe --name my-universe --example
```

and reach for `add-character`, `shoot-references`, and `assert-story`. The gate will refuse to
render until the references actually exist on disk, which is the behavior you are paying for: a
render that proceeds without its subject's locked plates produces a plausible picture of the wrong
person, and that passes review.

## Where to go next

- [`docs/REFERENCE.md`](./docs/REFERENCE.md) — every skill, verb, form and provider (generated).
- [`docs/GLOSSARY.md`](./docs/GLOSSARY.md) — the vocabulary.
- [`SPEC.md`](./SPEC.md) — the contract.
- [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — how the six layers fit.
