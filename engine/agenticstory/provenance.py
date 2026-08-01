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


# Every raster extension a universe actually stores art in. `.png` alone was the rule
# until v0.21 and it silently under-reported: `reference/gary/photos/gary-rome-colosseum.jpg`
# and a `.webp` style-pack ref were both invisible to the whole provenance sweep, so they
# could never be counted as missing, never be backfilled, and never enter a divergence
# check. A blind spot in the one module whose docstrings are about not under-reporting.
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")


def images(universe: Path, entity: str | None = None) -> list[Path]:
    """Every stored image under `reference/`, optionally scoped to ONE entity.

    `entity` scopes the sweep to `reference/<entity>/`, which is what makes
    `backfill-provenance --entity` possible. Without it a caller wanting to stamp one
    character's plates had to run the whole universe and then hand-prune the 35 unrelated
    images it wanted to touch, which is how a backfill turns into a diff nobody can review.
    """
    ref = Path(universe) / "reference"
    if entity:
        ref = ref / entity
    if not ref.is_dir():
        return []
    return sorted(p for p in ref.rglob("*") if p.suffix.lower() in IMAGE_EXTS)


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


def declared_sources(universe: Path) -> set[str]:
    """Resolved paths a universe has EXPLICITLY declared as source material.

    Reads every entity's `realPerson.photoStack`, which may name a file or a directory
    (a directory expands to the images directly inside it). Self-contained on purpose:
    this is a read of canon, and a provenance sweep must not fail because a refs-layer
    resolver changed shape.
    """
    out: set[str] = set()
    ents = Path(universe) / "canon" / "entities"
    if not ents.is_dir():
        return out
    for ef in sorted(ents.glob("*.json")):
        try:
            e = json.loads(ef.read_text())
        except Exception:
            continue
        stack = ((e.get("structured") or {}).get("realPerson") or {}).get("photoStack") or []
        for p in stack:
            cand = Path(p)
            for t in ([cand] if cand.is_absolute() else [universe / p, universe.parent / p]):
                if not t.exists():
                    continue
                if t.is_dir():
                    out.update(str(f.resolve()) for f in t.iterdir()
                               if f.suffix.lower() in IMAGE_EXTS)
                else:
                    out.add(str(t.resolve()))
                break
    return out


def is_source(png: Path, declared: set[str] | None = None) -> bool:
    """A photo-stack input, not generated output.

    A real person's reference photographs sit in the same tree as rendered art. They
    were never generated, so "the generating call was not recorded" is simply false
    about them, and counting them as missing provenance both overstates the gap and
    would stamp 57 photographs in Nation of Fire with a note about a render that
    never happened.

    `declared` (v0.21) is the set of resolved paths a universe has EXPLICITLY named as
    source material, chiefly `realPerson.photoStack` members. It is checked first,
    because the path heuristic below is only a guess and guesses the wrong way on a real
    case: a matrix slot legitimately filled by a PHOTOGRAPH — `reference/<id>/face-neutral.png`
    for a real person — matches neither `photo-N` nor a `photos/` parent, so it fell
    through to `attested`, which asserts a render that never happened. An assertion about
    history is the one thing this module may not get wrong, so an explicit declaration
    outranks the filename every time.
    """
    if declared and str(png.resolve()) in declared:
        return True
    return bool(re.match(r"photo[-_ ]?\d*$", png.stem, re.I)) or "photos" in png.parts


def classify(png: Path, prompt: str | None, declared: set[str] | None = None) -> str:
    if is_source(png, declared):
        return "source"
    if prompt:
        return "reconstructed"
    if DETERMINISTIC.search(png.name):
        return "deterministic"
    return "attested"


def build_record(png: Path, universe: Path, git: dict, spec_version: str,
                 declared: set[str] | None = None) -> dict:
    prompt = prompts_for(png)
    kind = classify(png, prompt, declared)
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


def plan(universe: Path, spec_version: str = "0", entity: str | None = None) -> dict:
    """What a backfill would do. Writes nothing.

    `entity` scopes the sweep to one entity's `reference/<id>/` subtree. Unscoped is
    still the default and still correct; the scope exists because a run that wants to
    stamp one character's plates otherwise proposes touching every unprovenanced image
    in the universe, and a diff nobody can review is a diff nobody checks.
    """
    universe = Path(universe).expanduser().resolve()
    all_png = images(universe, entity)
    missing = [p for p in all_png if not has_recipe(p)]
    git = git_index(universe) if missing else {}
    declared = declared_sources(universe) if missing else set()
    records = [(p, build_record(p, universe, git, spec_version, declared)) for p in missing]
    counts: dict[str, int] = {}
    for _p, r in records:
        counts[r["provenance"]] = counts.get(r["provenance"], 0) + 1
    return {
        "universe": str(universe),
        "entity": entity,
        "total_images": len(all_png),
        "already_have_recipe": len(all_png) - len(missing),
        "to_backfill": len(missing),
        "by_kind": counts,
        "records": records,
        "rerunnable_for_true_recipe": counts.get("deterministic", 0),
    }


def apply(universe: Path, spec_version: str = "0", entity: str | None = None) -> dict:
    """Write the backfilled recipes. Never overwrites an existing recipe."""
    p = plan(universe, spec_version, entity)
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
