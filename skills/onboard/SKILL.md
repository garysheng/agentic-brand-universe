---
name: onboard
description: Install Agentic Brand Universe for someone, as a conversation rather than a list of commands they have to run. Clones or locates the repo, links every skill into their harness, verifies the image providers and API keys, runs the test suite, and reports what is ready and what is genuinely blocked, all in plain language. Use when someone says "install this", "set me up", "how do I start", "get me running", "I want to try this", when a friend has been handed the framework and needs it working, or when `abu` finds no universes and nothing installed. Never prints shell commands at the user.
---

# Onboard

Somebody wants to use this. Your job is to make it work and tell them what happened,
not to hand them a list of things to type.

## The rule this skill exists to enforce

**You run the commands. They run nothing.** A quickstart full of bash addresses the
wrong reader: in a cartridge model the human states intent and the console operates.
The only things a harness genuinely cannot do on their behalf are installing the
console itself and holding an API key, because both are credentials and consent.
Everything else is yours.

## Procedure

**1. Find or place the repo.** If it is already on disk, use it. Otherwise clone
`https://github.com/garysheng/agentic-brand-universe` somewhere sensible and say
where you put it, because a file they cannot find later is a file they do not own.

**2. Run the installer.**

```
python3 <skill>/scripts/install.py --json
```

It links every skill into `~/.claude/skills`, resolves both image providers, checks
for the API keys and for `git` and `uv`, runs the full suite, and returns a verdict
with an explicit `blockers` list. Pass `--check` first if you want to report the
current state without changing anything. It is idempotent, so a partial install is
fixed by running it again.

**3. Report in outcomes, not output.** Three sentences: what is working, what is
blocked, what happens next. Translate every blocker into a human action:

| Blocker | What you say |
|---|---|
| no API key set | "You'll need an OpenAI or Google image key. Once you paste one in, I'll take it from there." |
| `uv` missing | Offer to install it. Do not print the command and wait. |
| `git` missing | Same. |
| tests failing | Do not proceed. Report honestly and debug; an install that half-works wastes more of their time than one that refuses. |

**4. Hand off to the first real thing.** An install with no first win is an anticlimax.
Ask what they are making, then go:

- A look, no recurring characters (a zine, a deck, page heroes) goes to
  `create-style-pack` and then `on-brand-image`. This needs no universe and is the
  smallest path to a first image.
- Something that must appear identically everywhere goes to
  `start-new-story-universe`.

Then run `abu` so they see where they stand and what is next. That is the loop they
will live in from now on, and the sooner it becomes familiar the better.

## What to tell a non-technical person up front

Two sentences, no more: this runs inside their AI harness, and they will talk to it in
plain language. Do not explain canon, goldens, registers, gates, or the spec. The
vocabulary arrives when a specific decision needs it, which is what makes it stick.

## Definition of done

- The suite is green, both providers resolve, and at least one API key is present.
- They have made one real artifact, or know exactly what the next step produces.
- They never saw a command.
