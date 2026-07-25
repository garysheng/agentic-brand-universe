---
name: evolve-agentic-story
description: Evolve the Agentic Story framework itself — its skills, engine, spec, templates, and plugin — instead of hand-rolling around its gaps. Invoke mid-session the moment you catch yourself (or Gary catches you) doing framework-shaped work by hand: a bespoke generate/provenance script, a manual step you keep repeating, a missing scaffolder (e.g. no create-style-pack), a look with no Style Pack, provenance saved by memory instead of by tool. The framework is young and WILL be missing things; hand-rolling once is fine, hand-rolling twice is a bug in the framework. This skill promotes the hand-rolled thing UP into the framework, bumps the version, re-syncs + delivers the plugin, logs it, and updates itself. Use when Gary says "why are we hand-rolling this", "update the framework/templates/skills", "fix the generator", "we know better", "/evolve-agentic-story", or is visibly frustrated that a repeated manual action should be a tool.
---

# Evolve Agentic Story (the meta-skill)

The framework at `~/Documents/github-repos/agenticstory` is a **work in progress**. It is normal to hit a gap mid-build and hand-roll a step to keep moving. What is NOT normal is letting that hand-rolled thing calcify. This skill is the forcing function that turns "I wrote a one-off script / did a manual step" into "the framework now owns it, versioned and delivered, so no universe ever hand-rolls it again."

## The Promotion Rule (the "fix the generator" principle)

> When you catch yourself doing framework-shaped work by hand, STOP. Ask: *is this specific to this universe, or would every universe want it?* If every universe would want it, it is a framework gap — promote it. Do not ship the one-off.

Framework-shaped work = anything about **how** universes are built, not **what** a particular one contains: generating an image, saving provenance, scaffolding an entity/style-pack/universe, locking a golden, gating a render, syncing the plugin. Universe-shaped work = this universe's canon, assets, identity, craft-canon.

The tell you are hand-rolling a framework gap: you write a script or do a manual step, and renaming/deleting the universe would not change it. That belongs in a skill, the engine, or the spec — not in the universe repo.

Hand-rolling **once, consciously, to keep momentum** is fine — the framework is fresh. Hand-rolling the **same** thing a second time, or leaving the one-off in place, is the failure this skill exists to catch.

## When to invoke

- Gary is frustrated that a repeated manual action should be a tool ("why are we hand-rolling this", "update the templates/skills", "we know better", "fix the generator").
- You just wrote a bespoke script that duplicates or should live in the framework (e.g. a universe-local `gen.py` that re-implements `on-brand-image` + `lock-references` provenance).
- A needed primitive does not exist yet (observed gaps: **no `create-style-pack` scaffolder** — `pack.json` + `refs/` is hand-made; a look with no Style Pack; provenance saved by memory rather than at lock).
- The framework's own update process changed (then this skill updates itself — see step 8).

## Repos and the delivery chain (know these cold)

- **Framework source:** `~/Documents/github-repos/agenticstory` — `SPEC.md` (the contract, versioned vX.Y), `engine/` (Python + tests), `skills/` (every `agenticstory:*` skill), `registry/`, `SAVE-LOG.md` (changelog), `run-tests.sh`, `sync-plugin.sh`.
- **Plugin / marketplace repo:** `~/Documents/github-repos/garysheng-claude-plugins/plugins/agenticstory/` — `.claude-plugin/plugin.json` holds the **plugin `version`** (currently 0.6.3); `skills/` is a **copy** of the source skills (not a symlink).
- **Installed plugin cache:** what `agenticstory:*` invocations actually run — a separate clone of the marketplace remote, under a versioned hash dir.

**COPYING IS NOT DELIVERING.** The chain is `agenticstory/skills → marketplace repo → git remote → installed cache`. A change is only live after: synced, committed AND pushed in BOTH repos, plugin `version` bumped, and `/plugin update` run. `sync-plugin.sh` enforces this and reports STALE for anything short of the remote — trust its exit code, do not eyeball it.

## The evolution loop

1. **Name the gap in one line** (what was hand-rolled, why the framework should own it). If it is genuinely universe-specific, STOP — it does not belong here; keep it in the universe.
2. **Pick the level:**
   - *A skill is missing or wrong* → add/edit `agenticstory/skills/<name>/SKILL.md` (+ `scripts/`). New skill: match the frontmatter shape (`name` + a dense `description` with trigger phrases), keep it universe-agnostic (takes a target universe/pack; hardcodes nothing).
   - *The engine is missing a capability* → `agenticstory/engine/agenticstory/` (+ a test in `engine/tests/`). Run `./run-tests.sh`; stay green.
   - *A contract/invariant changed* → `SPEC.md` (this is what forces a **spec** version bump and updates `conformsTo` strings).
   - *A new scaffolder/template is missing* (e.g. `create-style-pack`) → it is a skill; author it so it emits the same shape the consumers expect (read `on-brand-image`'s `pack.json` fields; read `lock-references`'s `recipe.json`).
3. **Register the skill** in the plugin manifest `description` catalog (`.claude-plugin/plugin.json`) if you added one, so it is discoverable.
4. **Bump the version(s):**
   - Plugin: `.claude-plugin/plugin.json` `version` — patch for a fix/new-skill, minor for a spec/contract change.
   - Spec: if `SPEC.md` changed the contract, bump its `vX.Y` and every `conformsTo`/`SPEC_VERSION` reference (engine `__init__`, init scaffolder). Universes conform to a spec version; do not break that silently.
5. **Test:** `./run-tests.sh` (engine green) if you touched the engine or spec-driven scaffolding.
6. **Sync + DELIVER:** run `./sync-plugin.sh`. Then commit AND push BOTH repos (agenticstory source + garysheng-claude-plugins marketplace). Re-run `./sync-plugin.sh` until it prints in-sync-and-delivered (not STALE). Tell Gary to run `/plugin update` (only he can); the change is not live until he does.
7. **Log it:** append a timestamped one-liner to `SAVE-LOG.md` (what promoted, version, why), matching the existing entry style. No em dashes; Gary is sole author (no Claude co-author on framework content).
8. **Update THIS skill** if the process itself changed (new repo in the chain, new version file, a new recurring gap worth naming). The meta-skill must always describe the current reality — a stale updater is the worst kind.

## Session-awareness (why this is callable mid-frustration)

When invoked because Gary is frustrated we are hand-rolling, first **take stock of the session**: list what was done by hand that is framework-shaped (bespoke scripts, manual provenance, missing scaffolders, a look with no pack). Separate reusable-everywhere from this-universe-only. Promote the reusable set through the loop above, in priority order (the thing blocking the current work first). Then return to the universe work using the now-real framework tools. The goal is to shrink the hand-rolled surface every session until it is zero.

## Definition of done

- The gap is a real framework artifact (skill/engine/spec/template), universe-agnostic, tested where applicable.
- Versions bumped; `sync-plugin.sh` reports delivered (committed + pushed in both repos), not STALE; Gary prompted to `/plugin update`.
- `SAVE-LOG.md` has the entry; if the process changed, this skill was updated too.
- The universe that triggered this no longer hand-rolls the thing — it calls the framework.
