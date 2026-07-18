"""
Agentic Story — universe scaffolder.

`init` lays down a schema-valid, empty universe (universe.json + canon/ + stories/
+ the pre-render gate wrapper + a canon README). With --example it also drops one
character, one unlocked setting, one story, and one relation so the shape is obvious
and the load-bearing gate is self-demonstrating: the example `validate`s green, but
`assert-story` REFUSES until you supply the character's real reference art — which is
the whole point (references are load-bearing; absence is a crash, not a drift).

Stdlib only. Every file it writes is either structured data the engine validates or
prose in a known slot — nothing load-bearing lives only in a human's head.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import SPEC_VERSION, SPEC_WIKI, SPEC_URL


def engine_dir() -> Path:
    """Absolute path to the engine dir (contains the `agenticstory` package)."""
    return Path(__file__).resolve().parent.parent


def _assert_sh(baked_engine: Path) -> str:
    """The pre-render GATE a renderer/gen-script calls before drawing a unit.

    Delegates to the engine so there is ONE load-bearing system. The engine dir is
    resolved from $AGENTICSTORY_ENGINE (override) or the path baked at init time.
    """
    return f'''#!/usr/bin/env bash
# Load-bearing PRE-RENDER GATE for this universe, via the Agentic Story engine.
#
# A renderer/gen-script MUST call this BEFORE generating a unit. If a required
# character sheet is missing or a spread's setting is not locked, this exits
# non-zero and the render is refused. That refusal is the feature.
#
# Usage:
#   assert.sh validate
#   assert.sh spread --characters hero,guide [--location the-hall]
#   assert.sh story  the-first-step
set -euo pipefail
HERE="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
UNIVERSE="$(cd "$HERE/../.." && pwd)"                 # <universe> (this file is at <universe>/canon/scripts/)
ENGINE="${{AGENTICSTORY_ENGINE:-{baked_engine}}}"     # override with $AGENTICSTORY_ENGINE if the engine moves
[ -d "$ENGINE" ] || {{ echo "agenticstory engine not found at $ENGINE — set AGENTICSTORY_ENGINE" >&2; exit 3; }}

[ $# -ge 1 ] || {{ echo "usage: assert.sh validate|spread|story ..." >&2; exit 2; }}
mode="$1"; shift
cd "$ENGINE"
case "$mode" in
  validate) exec python3 -m agenticstory.cli validate     "$UNIVERSE" ;;
  spread)   exec python3 -m agenticstory.cli assert-spread "$UNIVERSE" "$@" ;;
  story)    exec python3 -m agenticstory.cli assert-story  "$UNIVERSE" "$@" ;;
  *) echo "usage: assert.sh validate|spread|story ..." >&2; exit 2 ;;
esac
'''


def _canon_readme(name: str) -> str:
    return f'''# {name} — canon

Typed, git-versioned canon for the **{name}** universe (agenticstory schema).
The structured record is the source of truth; prose is a first-class field on it,
never a separate document that can drift.

**Conforms to:** [agenticstory spec]({SPEC_URL}) v{SPEC_VERSION} · canonical: [{SPEC_WIKI}]({SPEC_WIKI})
(provenance also recorded in `../universe.json` `spec`).

## Layout

- `entities/*.json` — one Entity per file (`character | setting | visual-metaphor |
  doctrine | motif | beat | prop | group`). A renderer-consumed entity (a character,
  a renderable motif) carries `structured.sheets` + `requiredForRender`; a `setting`
  / `visual-metaphor` carries a `status` + a `contract` and is REFUSED until locked.
- `relations/*.json` — one Relation per file, or a list (`appears-in`, `derived-from`,
  `crossover-with`, `contradicts`, `supersedes`). A relation side may be an entity OR
  a story id.
- `../stories/*.json` — one StorySpec per file (`spine`, `features`, `beats`,
  `provenance`); a `status: "stub"` story is a registered placeholder (title + spine)
  exempt from the beats/provenance requirements until filled in.

## The gate

```bash
canon/scripts/assert.sh validate                       # structural validation of all canon
canon/scripts/assert.sh story  <story-id>              # THE pre-render gate for a whole story
canon/scripts/assert.sh spread --characters a,b [--location X]
```

No renderer may generate a unit whose `assert` has not passed. See the framework
SPEC.md for the full field contracts.
'''


# --- example records (schema-valid; the character intentionally has a placeholder
#     sheet so the gate self-demonstrates — see module docstring) ---

def _example_files() -> dict[str, object]:
    protagonist = {
        "id": "protagonist",
        "kind": "character",
        "originStory": "the-first-step",
        "authority": {"lockedBy": "TODO-you", "lockedOn": None},
        "structured": {
            "sheets": {"body": "assets/protagonist-body.png", "face": "assets/protagonist-face.png"},
            "requiredForRender": ["body", "face"],
            "invariants": ["EXAMPLE-replace-me"],
        },
        "prose": {
            "voice": "TODO — how they speak / what they want",
            "rules": "EXAMPLE ENTITY. The sheet paths above are PLACEHOLDERS — `assert-story` "
                     "will refuse to render until you drop the real reference art at those paths "
                     "(under the universe's assetRoot). That refusal is the load-bearing gate working.",
        },
    }
    the_crossroads = {
        "id": "the-crossroads",
        "kind": "setting",
        "originStory": "the-first-step",
        "status": "unlocked",
        "contract": {
            "turnaround": None, "emptyPlates": [], "blueprint": None,
            "map": "", "blocking": "", "dressing": "",
        },
        "prose": {
            "rules": "EXAMPLE SETTING, deliberately UNLOCKED. A setting is refused until every "
                     "contract field is filled and status is 'locked': a drawn turnaround + empty "
                     "plates + blueprint, and the map/blocking/dressing prose passed in every prompt.",
        },
    }
    the_first_step = {
        "id": "the-first-step",
        "logline": "EXAMPLE story — replace with your first property.",
        "spine": "testimony",
        "refrain": "Every journey has a first step.",
        "status": "full",
        "register": {
            "id": "TODO-register-id",
            "anchor": None,
            "anchoredToRealArt": None,
            "rejectedPoles": [],
        },
        "features": ["protagonist"],
        "beats": [
            {"n": 1, "text": "The protagonist takes the first step.",
             "location": None, "characters": ["protagonist"],
             "provenance": "EXAMPLE — every beat cites a real source (testimony, research, the author's words)."}
        ],
        "writesBack": [],
        "gates": {"wordsBlessed": None, "subjectApproval": None},
    }
    relations = [
        {"from": "protagonist", "rel": "appears-in", "to": "the-first-step",
         "note": "EXAMPLE relation — the graph is queryable and contradictions are explicit records."}
    ]
    return {
        "canon/entities/protagonist.json": protagonist,
        "canon/entities/the-crossroads.json": the_crossroads,
        "canon/relations/example-relations.json": relations,
        "stories/the-first-step.json": the_first_step,
    }


def scaffold_universe(
    target: str | Path,
    name: str,
    asset_root: str = ".",
    example: bool = False,
    force: bool = False,
    baked_engine: Path | None = None,
) -> list[str]:
    """Create a schema-valid universe at `target`. Returns the list of files written.

    Raises FileExistsError if a universe.json already exists and force is False.
    """
    root = Path(target).resolve()
    manifest = root / "universe.json"
    if manifest.exists() and not force:
        raise FileExistsError(f"{manifest} already exists (use force=True to overwrite)")

    baked_engine = baked_engine or engine_dir()
    written: list[str] = []

    def write(rel: str, content: str) -> None:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        written.append(str(p))

    # 1. manifest — carries spec PROVENANCE: which framework version this universe
    #    conforms to + the canonical wiki that defines it (like a BOOMERANG.md).
    write("universe.json", json.dumps({
        "name": name,
        "assetRoot": asset_root,
        "spec": {
            "framework": "agenticstory",
            "version": SPEC_VERSION,
            "wiki": SPEC_WIKI,
            "conformsTo": f"{SPEC_URL} v{SPEC_VERSION}",
        },
        # IDENTITY — the universe's own constants (SPEC v0.3 §11). Generic framework
        # skills read these instead of hardcoding a universe. Fill them in; a skill
        # must NEVER hardcode a universe's name, mark, theme, or voice terms. A new
        # universe ships DATA (this block + canon + assets); the framework ships the
        # skills, parameterized by the target universe.
        "identity": {
            "mark": f"A {name.replace('-', ' ').upper()} story",  # the "made in this universe" byline
            "platformUniverseId": name,          # registry id when shipping to a shared platform
            "theme": None,                        # brand token set / palette id (fill in)
            "closingOrnament": None,              # a recurring closing motif, if any (e.g. a flame)
            "voice": {"capitalize": [], "oneWord": []},  # voice-gate term rules for this universe
            "subjectApproval": {"realLivingPerson": "requires-blessing"},
        },
        # SELF-CONTAINMENT (SPEC v0.3, principle 3a): assetRoot is "." and EVERY asset
        # a canon entity references lives inside THIS repo. Never point canon at a
        # sibling folder or another repo — a universe you can clone alone, whose refs
        # all resolve, is the load-bearing guarantee.
        "note": f"Typed canon for the {name} universe (agenticstory schema v{SPEC_VERSION}). "
                f"Structured/load-bearing records live here; prose narrative canon may live in "
                f"CANON.md. Self-contained: every referenced asset resolves under assetRoot "
                f"inside this repo. Validated by the agenticstory engine; the canonical spec is "
                f"defined at {SPEC_WIKI}.",
    }, indent=2) + "\n")

    # 2. canon dirs (keep empty dirs in git)
    for d in ("canon/entities", "canon/relations", "stories"):
        write(f"{d}/.gitkeep", "")

    # 3. the gate + canon README
    write("canon/scripts/assert.sh", _assert_sh(baked_engine))
    (root / "canon" / "scripts" / "assert.sh").chmod(0o755)
    write("canon/README.md", _canon_readme(name))

    # 4. optional worked example
    if example:
        for rel, data in _example_files().items():
            write(rel, json.dumps(data, indent=2) + "\n")

    return written
