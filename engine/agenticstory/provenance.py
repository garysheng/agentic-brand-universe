"""Backfilling provenance for art that predates the adapter, without lying about it.

`generate.py` writes a `.recipe.json` as a side effect of generating, so everything
made after it cannot lack provenance. Everything made BEFORE it can, and does: 835 of
1108 images in Nation of Fire carry no recipe.

`universe-doctor` proposes "regenerate via the adapter" for those, and that advice is
actively dangerous, because the set includes LOCKED GOLDENS (`hero.png`, `master.png`,
turnarounds). A golden is the visual answer of record that every downstream render is
handed. Re-rendering one produces a different image, because generation is stochastic.
You would be mutating canon to repair metadata, and every spread already citing that
golden would silently disagree with it.

So this module never invokes a model. It records what is actually knowable, at three
levels of confidence, and says which is which:

  reconstructed  a `prompts.md` beside the image declares the exact prompt for this
                 shot. The prompt is real; the refs, size and quality are not known,
                 so they are left null rather than guessed.
  attested       nothing survives but the file and its history. Records sha256 plus
                 the commit that introduced it, and sets `unrecorded: true`.
  deterministic  blueprint/massing/elevation output, which a code-built generator can
                 reproduce byte-identically. Flagged so it can be re-run for a TRUE
                 recipe at no cost. Still attested now, so nothing is left blank.

`unrecorded: true` is the point. You cannot recover what was never captured, and a
plausible reconstruction presented as a captured call is worse than an admitted gap.
This is the same instinct as `archive`, which retires an entity by recording the
retirement rather than deleting the history.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

RECIPE_SUFFIX = ".recipe.json"
DETERMINISTIC = re.compile(r"blueprint|massing|elevation", re.I)
# A shot section: `## <heading>` then its body up to the next heading. Two heading
# dialects exist in the wild and BOTH are load-bearing. Matching only the first found
# 27 of 232 recoverable prompts and silently downgraded the other 205 to "attested",
# which is exactly the kind of quiet under-recovery this module exists to avoid.
#   `## hero  -> reference/x/hero.png`   target names the file
#   `## face-3q`                          heading IS the file stem
SHOT = re.compile(r"^##\s+(.+?)\s*$(.*?)(?=^##\s|\Z)", re.M | re.S)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()


def images(universe: Path) -> list[Path]:
    ref = Path(universe) / "reference"
    return sorted(ref.rglob("*.png")) if ref.is_dir() else []


def has_recipe(png: Path) -> bool:
    return (png.parent / (png.name + RECIPE_SUFFIX)).exists()


def git_index(universe: Path) -> dict[str, dict]:
    """path -> {commit, date} for the commit that ADDED it.

    One `git log` walk rather than one call per file. At 835 files the per-file
    version takes minutes and this takes under a second.
    """
    try:
        r = subprocess.run(
            ["git", "log", "--diff-filter=A", "--name-only", "--date=short",
             "--format=%x00%H %ad"],
            cwd=universe, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return {}
    if r.returncode != 0:
        return {}
    out: dict[str, dict] = {}
    commit = date = None
    for line in r.stdout.splitlines():
        if line.startswith("\x00"):
            parts = line[1:].split()
            commit, date = (parts + [None, None])[:2]
        elif line.strip() and commit:
            out.setdefault(line.strip(), {"commit": commit, "date": date})
    return out


def prompts_for(png: Path) -> str | None:
    """The declared prompt for this shot, from the `prompts.md` beside it."""
    md = png.parent / "prompts.md"
    if not md.is_file():
        return None
    try:
        text = md.read_text()
    except OSError:
        return None
    for heading, body in SHOT.findall(text):
        shot, _, target = heading.partition("->")
        shot, target = shot.strip(), target.strip()
        hit = (target and Path(target).name == png.name) or shot == png.stem
        if hit:
            body = body.strip()
            if body:
                return body
    return None


def is_source(png: Path) -> bool:
    """A photo-stack input, not generated output.

    A real person's reference photographs sit in the same tree as rendered art. They
    were never generated, so "the generating call was not recorded" is simply false
    about them, and counting them as missing provenance both overstates the gap and
    would stamp 57 photographs in Nation of Fire with a note about a render that
    never happened.
    """
    return bool(re.match(r"photo[-_ ]?\d*$", png.stem, re.I)) or "photos" in png.parts


def classify(png: Path, prompt: str | None) -> str:
    if is_source(png):
        return "source"
    if prompt:
        return "reconstructed"
    if DETERMINISTIC.search(png.name):
        return "deterministic"
    return "attested"


def build_record(png: Path, universe: Path, git: dict, spec_version: str) -> dict:
    prompt = prompts_for(png)
    kind = classify(png, prompt)
    rel = str(png.relative_to(universe))
    g = git.get(rel, {})
    rec = {
        "asset": str(png),
        "provenance": kind,
        "unrecorded": kind not in ("reconstructed", "source"),
        "backfilled": True,
        "specVersion": spec_version,
        "sha256": sha256(png),
        "generator": "abu backfill-provenance",
        "note": {
            "reconstructed": "Prompt recovered from prompts.md beside the asset. The "
                             "references, size and quality of the original call were "
                             "not recorded and are NOT guessed here.",
            "attested": "This asset predates the provenance-writing adapter. Nothing "
                        "about the generating call survives. Recorded here are the "
                        "facts that do: its hash and when it entered canon.",
            "deterministic": "Code-built output (blueprint/massing/elevation). Re-run "
                             "the generator from its spec to replace this with a TRUE "
                             "recipe at no cost and with identical pixels.",
            "source": "Source input (a photo-stack reference), not generated output. "
                      "There is no generating call to record.",
        }[kind],
    }
    if prompt:
        rec["prompt"] = prompt
        # Deliberately null, not omitted: an absent key reads as an oversight, an
        # explicit null reads as "we looked and it is not knowable".
        rec["inputs"] = None
        rec["model"] = None
    if g:
        rec["git"] = g
        rec["enteredCanon"] = g.get("date")
    return rec


def plan(universe: Path, spec_version: str = "0") -> dict:
    """What a backfill would do. Writes nothing."""
    universe = Path(universe).expanduser().resolve()
    all_png = images(universe)
    missing = [p for p in all_png if not has_recipe(p)]
    git = git_index(universe) if missing else {}
    records = [(p, build_record(p, universe, git, spec_version)) for p in missing]
    counts: dict[str, int] = {}
    for _p, r in records:
        counts[r["provenance"]] = counts.get(r["provenance"], 0) + 1
    return {
        "universe": str(universe),
        "total_images": len(all_png),
        "already_have_recipe": len(all_png) - len(missing),
        "to_backfill": len(missing),
        "by_kind": counts,
        "records": records,
        "rerunnable_for_true_recipe": counts.get("deterministic", 0),
    }


def apply(universe: Path, spec_version: str = "0") -> dict:
    """Write the backfilled recipes. Never overwrites an existing recipe."""
    p = plan(universe, spec_version)
    written = 0
    for png, rec in p["records"]:
        dst = png.parent / (png.name + RECIPE_SUFFIX)
        if dst.exists():
            continue
        dst.write_text(json.dumps(rec, indent=2) + "\n")
        written += 1
    p["written"] = written
    p.pop("records", None)
    return p
