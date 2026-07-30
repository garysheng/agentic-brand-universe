"""Recovering `prompts.md` from the recipes beside it.

`backfill-provenance` runs one direction: a `prompts.md` declares a shot's prompt, so
art with no recipe can have one reconstructed. This module runs the OTHER direction,
and it exists because the reverse gap turned out to be the common one.

The shape of the failure: an agent shoots a matrix by calling a provider script
directly instead of through `shoot-references`. The art lands, the adapter writes a
`.recipe.json` beside it (provenance is a side effect of generating, so that part
survives), and `prompts.md` is left exactly as `add-character` scaffolded it, every
body still reading `TODO(author)`. The prompt now exists only inside the recipe, which
is an attestation of one past call and not a live instruction. Nothing regenerates from
it, nothing reads it before the next shot, and the file the framework keeps prompts in
is empty.

`chain_matrix.py` refuses to shoot a matrix in that state, which is correct and is what
surfaced this. But a refusal with no verb behind it just means somebody hand-transcribes
five files, so here is the verb.

Two rules keep it honest:

  * It only ever replaces a TODO placeholder. An authored body outranks a recipe, always,
    because the author may have deliberately revised the prompt after the shot. That also
    makes the whole thing idempotent: a second run writes nothing.
  * A shot with no recipe stays TODO. That is not a failure to fill in, it is a shot that
    was never taken, and the scaffold is already saying the true thing about it.

There is a third case, and skipping it was the first bug this module had. A `prompts.md`
is scaffolded ONCE, from the matrix slots the entity had at that moment, and it does not
follow the entity afterwards. Rename a setting's angles from the generic `empty-c1` to
the real `empty-path` and `empty-slope`, and the file still advertises slots that no
longer exist while the shots that DO exist have nowhere to be written down. So a recipe
whose shot has no heading gets a heading appended, marked as recovered. The alternative
is reporting a clean run over a file that is missing the only two prompts it needed.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

TODO = "TODO(author)"
SHOT = re.compile(r"^##[ \t]+(.+?)[ \t]*$(.*?)(?=^##[ \t]|\Z)", re.M | re.S)


def recipe_for(directory: Path, shot: str, target: str) -> Path | None:
    """The recipe beside a shot, under either naming convention.

    `shoot-references` documents `<shot>.recipe.json`; the provider adapter writes
    `<image>.recipe.json`, which for `face-neutral.png` is `face-neutral.png.recipe.json`.
    Both are in the corpus, so both are accepted.
    """
    names = [f"{shot}.recipe.json", f"{shot}.png.recipe.json"]
    if target:
        stem = Path(target).name
        names = [f"{stem}.recipe.json", f"{Path(stem).stem}.recipe.json"] + names
    for n in names:
        p = directory / n
        if p.is_file():
            return p
    return None


def prompt_in(recipe: Path) -> str | None:
    try:
        data = json.loads(recipe.read_text())
    except (OSError, ValueError):
        return None
    prompt = data.get("prompt")
    return prompt.strip() if isinstance(prompt, str) and prompt.strip() else None


def declared_sheets(universe: Path, entity: str) -> set[str]:
    """The slots this entity actually has, which is what makes an orphan an orphan.

    Without this the sweep appends a heading for every recipe in the folder, and a
    reference folder accumulates plenty of art that is NOT a matrix slot: alt-look era
    plates, rejected candidates, composited study sheets. On Nation of Fire the
    unconstrained version proposed 384 new headings against 21 real recoveries. A slot
    is what the ENTITY says it is.
    """
    f = universe / "canon" / "entities" / f"{entity}.json"
    if not f.is_file():
        return set()
    try:
        sheets = (json.loads(f.read_text()).get("structured") or {}).get("sheets") or {}
    except (OSError, ValueError):
        return set()
    return set(sheets) if isinstance(sheets, dict) else set()


def orphan_recipes(directory: Path, known: set[str], slots: set[str]) -> list[tuple[str, str]]:
    """Recipes for DECLARED slots the scaffold never listed, because the slots moved."""
    out, seen = [], set()
    for r in sorted(directory.glob("*.recipe.json")):
        shot = r.name[: -len(".recipe.json")]
        if shot.endswith(".png"):
            shot = shot[: -len(".png")]
        # Both naming conventions can exist for one shot; recover it once.
        if shot in known or shot in seen or shot not in slots:
            continue
        prompt = prompt_in(r)
        if prompt:
            seen.add(shot)
            out.append((shot, prompt))
    return out


def plan_file(md: Path, universe: Path) -> dict:
    """What this one `prompts.md` would gain, without writing anything."""
    blank = {"path": str(md), "filled": [], "still_todo": [], "authored": [], "appended": []}
    try:
        text = md.read_text()
    except OSError:
        return blank

    filled, still_todo, authored, seen = [], [], [], set()
    for heading, body in SHOT.findall(text):
        shot, _, target = heading.partition("->")
        shot, target = shot.strip(), target.strip()
        seen.add(shot)
        if TODO not in body:
            authored.append(shot)
            continue
        recipe = recipe_for(md.parent, shot, target)
        prompt = prompt_in(recipe) if recipe else None
        if prompt:
            filled.append((shot, prompt))
        else:
            still_todo.append(shot)
    return {"path": str(md), "filled": filled, "still_todo": still_todo,
            "authored": authored,
            "appended": orphan_recipes(md.parent, seen, declared_sheets(universe, md.parent.name))}


def rewrite(text: str, filled: dict[str, str]) -> str:
    """Replace each named shot's TODO body with its recovered prompt, in place."""
    def sub(m: re.Match) -> str:
        heading, body = m.group(1), m.group(2)
        shot = heading.partition("->")[0].strip()
        if shot not in filled or TODO not in body:
            return m.group(0)
        return f"## {heading}\n\n{filled[shot]}\n\n"

    return SHOT.sub(sub, text)


def prompt_files(universe: Path) -> list[Path]:
    ref = universe / "reference"
    return sorted(ref.rglob("prompts.md")) if ref.is_dir() else []


def append_block(shot: str, prompt: str, entity: str) -> str:
    return (f"\n## {shot}  -> reference/{entity}/{shot}.png\n"
            f"RECOVERED from this shot's recipe: the scaffold had no slot for it, so the\n"
            f"prompt below is what actually produced the art on disk.\n\n{prompt}\n")


def run(universe: Path, apply: bool = False, only: list[str] | None = None) -> dict:
    """`only` scopes the sweep to named entities.

    The universe-wide plan is the honest report and should stay easy to see, but the
    universe-wide APPLY touches every reference folder at once. A run that is really
    unblocking one book should be able to fix that book's entities and leave the rest
    reported rather than rewritten.
    """
    want = set(only or [])
    files, total_filled, total_todo, total_appended = [], 0, 0, 0
    for md in prompt_files(universe):
        if want and md.parent.name not in want:
            continue
        p = plan_file(md, universe)
        if not (p["filled"] or p["still_todo"] or p["appended"]):
            continue
        if apply and (p["filled"] or p["appended"]):
            text = rewrite(md.read_text(), dict(p["filled"]))
            for shot, prompt in p["appended"]:
                text = text.rstrip("\n") + "\n" + append_block(shot, prompt, md.parent.name)
            md.write_text(text)
        files.append(p)
        total_filled += len(p["filled"])
        total_todo += len(p["still_todo"])
        total_appended += len(p["appended"])
    return {"files": files, "filled": total_filled, "still_todo": total_todo,
            "appended": total_appended, "applied": apply}
