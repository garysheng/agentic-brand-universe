#!/usr/bin/env python3
"""ONE way to write the provenance sidecar for a cover asset that was DERIVED.

A cover reaches the platform through more than one deterministic step, and each of
them was independently re-learning how to write a `.recipe.json`. `conform_cover.py`
learned it on 2026-08-04 (SPEC v0.32 §3.2: a deterministic in-repo TRANSFORM writes
its own recipe, a third honest way to get one beside generating and importing), and
the very next step in the same chain — publishing `cover-raw.png` as the
platform-facing `cover.png` — was still being done by a hand `cp` with the sidecar
hand-copied after it.

So the shape lives here once. Stdlib only, and deliberately NO Pillow import: a step
that merely copies bytes must not require an imaging library to record that it did.

The invariant every caller inherits: **a derivative says so.** `model` is explicitly
none, `prompt` is null, and `derivedFrom` names the source, the source's own recipe
and its hash, so the chain back to the generation that made the art is unbroken and a
reader can never mistake a transform for a render.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

CARRY = ("spec", "universe", "story")


def sha16(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def write_derivative_recipe(out, src, *, tool: str, args: dict, transform: str,
                            note: str, role: str = "source render"):
    """Write `<out>.recipe.json` recording `out` as a derivative of `src`.

    Returns the sidecar path, or None if it could not be written (a warning goes to
    stderr rather than an exception: losing the art to a provenance failure would be
    the worse trade, and `book-doctor` fails on the missing sidecar anyway).
    """
    out, src = pathlib.Path(out), pathlib.Path(src)
    src_recipe = src.with_name(src.name + ".recipe.json")
    carried, generation = {}, {}
    if src_recipe.exists():
        try:
            s = json.loads(src_recipe.read_text())
            carried = {k: s[k] for k in CARRY if k in s}
            # THE GENERATION RECORD MUST SURVIVE THE DERIVE (merged from master,
            # 2026-08-05). `render_cover` conforms IN PLACE, so this function is often
            # about to overwrite the very recipe it derives from. Before this existed
            # that destroyed the prompt, the refs, the provider and the model for EVERY
            # cover: on nation-of-fire, 30 of 39 cover recipes had lost their generation
            # prompt and 25 pointed at themselves. The cost was concrete, because
            # rebuilding 28 covers to add a byline meant reconstructing each composition
            # by LOOKING at the art, the scene that made it being gone.
            #
            # Carry it forward under `sourceRender`. It is NOT this asset's own
            # generation and is never presented as one: top-level `prompt` and `model`
            # stay honest about being a derivative.
            gen = {k: s[k] for k in ("prompt", "refs", "provider", "model", "size",
                                     "quality", "textLines", "qa", "descriptor",
                                     "generatedBy", "universeCommit", "book", "spread")
                   if k in s and s[k] is not None}
            if gen.get("prompt"):
                generation = gen
        except (json.JSONDecodeError, OSError):
            carried = {}
    rec = {
        "asset": str(out),
        "model": "none (deterministic image transform, no model call)",
        "mode": "derive",
        "tool": tool,
        "args": args,
        "prompt": None,
        # The generation this was derived from, verbatim. Present only when the source
        # recipe actually recorded one.
        **({"sourceRender": generation} if generation else {}),
        "transform": transform,
        "inputs": [{"path": str(src), "sha256_16": sha16(src), "role": role}],
        "sha256_16": sha16(out),
        "derivedFrom": {
            "path": str(src),
            # A SELF-REFERENTIAL POINTER IS WORSE THAN NONE: it reads like a chain and
            # leads nowhere. When the derive is in place, the source recipe IS this
            # sidecar, so omit it and rely on `sourceRender`.
            "recipe": (str(src_recipe)
                       if src_recipe.exists()
                       and src_recipe.resolve()
                       != out.with_name(out.name + ".recipe.json").resolve()
                       else None),
            "sha256_16": sha16(src),
        },
        "note": note,
        **carried,
    }
    sidecar = out.with_name(out.name + ".recipe.json")
    try:
        sidecar.write_text(json.dumps(rec, indent=2) + "\n")
    except OSError as e:
        print(f"WARNING: could not write provenance beside {out}: {e}", file=sys.stderr)
        return None
    return sidecar
