#!/usr/bin/env python3
"""reroll_from_recipe.py — re-run a rendered slot EXACTLY as its recipe records.

THE ONE-COMMAND EDIT PATH. Every rendered asset carries a `.recipe.json` beside it
"precisely for reproducibility", and until 2026-08-07 no framework verb ever read one
back. The cost was measured on a real run (hyperagentic-age,
runs/2026-08-07-1701-chat-a98f): a trivial closing-plate re-roll took 85 tool calls,
~70% of them re-reading the framework, SPEC and canon to reconstruct context that sat,
complete, in the slot's own recipe the whole time — model, full prompt, every ref path.
Orientation is only necessary when the answer is not already written down. Here it is.

What it does, in one command and one image call:
  1. Resolves the slot's generation from its recipe chain. Handles all three recipe
     dialects on disk: the provider-adapter shape (`refs: [{path}]`), the vendored
     provider shape (`inputs: [path]`), and `mode: "derive"` sidecars, whose
     `derivedFrom.recipe` chain it walks. When an in-place conform destroyed the
     pointer (the pre-v0.33 hole), it recovers the prompt from `sourceRender` and the
     refs from the closest-matching sibling generation recipe, and SAYS SO.
  2. Regenerates through the provider adapter (`on-brand-image/scripts/generate.py`),
     never a raw model call, with the optional `--note` delta appended to the recorded
     prompt — so provenance is written by construction.
  3. Replays every recorded derive step: `conform_cover.py` with the exact recorded
     args (aspect/mode/inset/blur/keyline) for endcaps, then the byte-identical
     platform-facing publish with its derivative recipe.
  4. Reminds you to read the result back (render-readback). A re-roll is still a
     render; the gate still applies.

It re-rolls a slot AS IT WAS. It reads NO canon, which is exactly why it must never be
used for an edit that changes text, cast, look, setting or register — those moved the
truth out from under the recipe, and the route is `update-book` / `compose-spread`,
which re-resolve canon. The `--note` is for deltas the recipe's own vocabulary can
absorb: light, weather, mood, a small compositional nudge.

Usage:
  reroll_from_recipe.py <asset.png | recipe.json> [--note "delta"] [--dry-run]
                        [--model M] [--size WxH] [--quality Q] [--timeout S]
                        [--out PATH] [--no-backup] [--allow-no-refs]
"""
from __future__ import annotations

import argparse
import datetime
import difflib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

RECIPE_SUFFIX = ".recipe.json"

# The prompt-similarity floor for adopting a sibling generation recipe's refs when the
# chain is broken. The incident's own book has two rolls of one plate whose prompts
# differ only in the NEGATIVES line (ratio ~0.97); an unrelated spread's prompt in the
# same folder scores far below this.
SIBLING_FLOOR = 0.80


def abu_root() -> Path:
    """The ABU root, found by walking UP for a marker instead of counting parents
    (same physics as on-brand-image/scripts/generate.py: this code runs from a git
    clone AND from a plugin cache, and only one of those has a fixed depth)."""
    for c in [HERE, *HERE.parents]:
        if (c / "engine" / "agenticstory").is_dir():
            return c
    sys.exit("reroll: cannot locate the ABU root from " + str(HERE)
             + " (looked upward for engine/agenticstory).")


def load(p: Path) -> dict:
    return json.loads(Path(p).read_text())


def is_derive(rec: dict) -> bool:
    """A derive sidecar records a deterministic transform, not a generation.
    Both markers are checked because both dialects exist on disk."""
    return rec.get("mode") == "derive" or str(rec.get("model") or "").lower().startswith("none")


def is_generation(rec: dict) -> bool:
    return bool(rec.get("prompt")) and not is_derive(rec)


def ref_paths(rec: dict) -> list[str]:
    """Reference paths from either generation dialect: the provider adapter writes
    `refs: [{path}]`; the vendored provider writes `inputs: [path]`. Only call this
    on a generation record — a derive's `inputs` are its transform source, not refs."""
    out: list[str] = []
    for r in rec.get("refs") or []:
        p = r.get("path") if isinstance(r, dict) else str(r)
        if p:
            out.append(p)
    if not out:
        for r in rec.get("inputs") or []:
            p = r.get("path") if isinstance(r, dict) else str(r)
            if p:
                out.append(p)
    return out


def sibling_generation(dirpath: Path, prompt: str, exclude: set[Path]):
    """The closest-matching generation recipe in the slot's own folder.

    Why this exists: before v0.33, conform_cover ran IN PLACE and overwrote the
    generation recipe, leaving `derivedFrom.recipe: null` and only a `sourceRender`
    block — which carries the prompt but, when the render bypassed the adapter, not
    the refs. The full ref list survives in the sibling `<slot>-gen.recipe.json` the
    run left behind. Exact prompt equality is the wrong test (two rolls of one plate
    legitimately differ in their NEGATIVES line), so this ranks by similarity and
    refuses below SIBLING_FLOOR rather than guessing."""
    best_path, best_rec, best_ratio = None, None, 0.0
    for rp in sorted(dirpath.glob("*" + RECIPE_SUFFIX)):
        if rp.resolve() in exclude:
            continue
        try:
            rec = load(rp)
        except (json.JSONDecodeError, OSError):
            continue
        if not is_generation(rec) or not ref_paths(rec):
            continue
        ratio = difflib.SequenceMatcher(None, prompt, str(rec.get("prompt"))).ratio()
        if ratio > best_ratio:
            best_path, best_rec, best_ratio = rp, rec, ratio
    if best_path is not None and best_ratio >= SIBLING_FLOOR:
        return best_path, best_rec, best_ratio
    return None, None, best_ratio


def classify_derive(rec: dict) -> str:
    """conform | publish | unknown. Unknown REFUSES upstream: replaying a transform
    this script cannot name would attest to a step it did not understand."""
    tool = str(rec.get("tool") or "")
    transform = str(rec.get("transform") or "")
    args = rec.get("args") or {}
    if "conform_cover" in tool:
        return "conform"
    if transform.startswith("copy") or "publish" in args:
        return "publish"
    return "unknown"


def resolve_chain(start: Path) -> dict:
    """Walk from an asset (or recipe) back to its generation, collecting the derive
    steps that must be replayed forward. Returns:
      { final: Path, derives: [ {kind, args, out} ... generation-forward order ],
        generation: {prompt, model, size, quality, refs}, source: str,
        refs_recovered: bool }
    """
    start = Path(start).expanduser()
    if start.name.endswith(RECIPE_SUFFIX):
        rpath = start
        asset = start.with_name(start.name[: -len(RECIPE_SUFFIX)])
    else:
        asset = start
        rpath = start.with_name(start.name + RECIPE_SUFFIX)
    if not rpath.exists():
        sys.exit(f"reroll: no recipe beside {asset}\n"
                 f"  expected {rpath}\n"
                 f"  Every generated asset carries one; if this one truly has none, it was made\n"
                 f"  outside the provider adapter and there is nothing faithful to replay.")

    derives_back: list[dict] = []   # final-first while walking
    visited: set[Path] = set()
    cur_rpath, cur_rec = rpath, load(rpath)
    generation = None
    source = None
    refs_recovered = False

    while True:
        key = cur_rpath.resolve()
        if key in visited:
            sys.exit(f"reroll: recipe chain loops at {cur_rpath}")
        visited.add(key)

        if is_generation(cur_rec):
            generation = {
                "prompt": cur_rec["prompt"],
                "model": cur_rec.get("model") or cur_rec.get("provider") or "gpt-image-2",
                "size": cur_rec.get("size") or "1536x1024",
                "quality": cur_rec.get("quality") or "high",
                "refs": ref_paths(cur_rec),
            }
            source = f"generation recipe {cur_rpath.name}"
            break

        if not is_derive(cur_rec):
            sys.exit(f"reroll: {cur_rpath.name} is neither a generation nor a derive recipe; "
                     f"refusing to guess what made it.")

        kind = classify_derive(cur_rec)
        if kind == "unknown":
            sys.exit(f"reroll: {cur_rpath.name} records a derive step this tool cannot replay "
                     f"(tool: {cur_rec.get('tool')!r}). Refusing rather than attesting to a "
                     f"transform it does not understand.")
        derives_back.append({
            "kind": kind,
            "args": cur_rec.get("args") or {},
            "out": Path(cur_rec.get("asset") or "") if cur_rec.get("asset") else None,
            "recipe": cur_rpath,
        })

        nxt = (cur_rec.get("derivedFrom") or {}).get("recipe")
        if nxt and Path(nxt).exists() and Path(nxt).resolve() not in visited:
            cur_rpath, cur_rec = Path(nxt), load(Path(nxt))
            continue

        # Chain broken (the pre-v0.33 in-place-conform hole). Recover.
        sr = cur_rec.get("sourceRender") or {}
        if not sr.get("prompt"):
            sys.exit(f"reroll: the derive chain dead-ends at {cur_rpath.name} with no "
                     f"generation recipe and no sourceRender prompt. Nothing faithful to "
                     f"replay; re-render through compose-spread/cover instead.")
        refs = ref_paths(sr)
        source = f"sourceRender carried in {cur_rpath.name}"
        if not refs:
            sib_path, sib_rec, ratio = sibling_generation(asset.parent, sr["prompt"], visited)
            if sib_rec is not None:
                refs = ref_paths(sib_rec)
                refs_recovered = True
                source += (f"; refs from sibling {sib_path.name} "
                           f"(prompt similarity {ratio:.2f})")
        generation = {
            "prompt": sr["prompt"],
            "model": sr.get("model") or "gpt-image-2",
            "size": sr.get("size") or "1536x1024",
            "quality": sr.get("quality") or "high",
            "refs": refs,
        }
        break

    derives = list(reversed(derives_back))  # generation-forward
    # A publish step's output is the final asset; a conform's is the -raw. When the
    # recorded `asset` paths were written on another machine, rebase them onto the
    # slot's actual folder by filename.
    for d in derives:
        if d["out"] is not None and not d["out"].exists():
            local = asset.parent / d["out"].name
            d["out"] = local
    return {"final": asset, "derives": derives, "generation": generation,
            "source": source, "refs_recovered": refs_recovered}


def with_note(prompt: str, note: str | None) -> str:
    if not note:
        return prompt
    return (prompt.rstrip()
            + "\n\nCHANGE FOR THIS RE-ROLL (the ONLY intended difference from the "
              "previous render): " + note.strip()
            + "\nEverything else stays exactly as described above: same subject, same "
              "composition, same style.")


def build_plan(chain: dict, note: str | None, overrides: dict, out_override: Path | None,
               allow_no_refs: bool = False) -> dict:
    gen = dict(chain["generation"])
    for k in ("model", "size", "quality"):
        if overrides.get(k):
            gen[k] = overrides[k]
    gen["prompt"] = with_note(gen["prompt"], note)

    if not gen["refs"] and chain["source"].startswith("sourceRender") and not allow_no_refs:
        sys.exit("reroll: the recovered generation has ZERO reference images and the original "
                 "chain is broken, so faithfulness cannot be proven. The refs are what carry "
                 "the register and the canon; pass --allow-no-refs only if the original render "
                 "truly used none.")
    missing = [r for r in gen["refs"] if not Path(r).expanduser().exists()]
    if missing:
        sys.exit("reroll: recorded reference images are MISSING on disk:\n  "
                 + "\n  ".join(missing)
                 + "\nRefusing: a re-roll without the original refs is a different render "
                   "wearing the same name.")

    if out_override is not None and chain["derives"]:
        sys.exit("reroll: --out only applies when the recipe is a direct generation; this "
                 "slot's chain dictates its own output paths (conform/publish).")

    final = out_override or chain["final"]
    gen_target = final if not chain["derives"] else None  # None -> temp file
    return {"generation": gen, "gen_target": gen_target, "final": final,
            "derives": chain["derives"], "source": chain["source"],
            "note": note or None}


def backup(paths: list[Path], dest_root: Path) -> Path | None:
    existing = [p for p in paths if p and p.exists()]
    if not existing:
        return None
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = dest_root / "candidates" / f"pre-reroll-{ts}"
    dest.mkdir(parents=True, exist_ok=True)
    for p in existing:
        shutil.copy2(p, dest / p.name)
        rp = p.with_name(p.name + RECIPE_SUFFIX)
        if rp.exists():
            shutil.copy2(rp, dest / rp.name)
    return dest


def readback_reminder(final: Path) -> str:
    root = abu_root()
    return ("\nNEXT — read it back before accepting (a re-roll is still a render; the gate "
            "still applies):\n"
            f"  python3 {root}/skills/render-readback/scripts/verify_render.py {final}\n"
            "  crop-zoom any invariant detail with render-readback/scripts/crop_zoom.py.\n"
            "  Any DEFECT re-rolls FROM SCRATCH (run this again); never stack an edit pass.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("target", help="the rendered asset (png) or its .recipe.json")
    ap.add_argument("--note", default=None,
                    help="the ONE intended delta, appended to the recorded prompt. "
                         "Omit for an identical re-roll.")
    ap.add_argument("--model", default=None, help="override the recorded model")
    ap.add_argument("--size", default=None, help="override the recorded size")
    ap.add_argument("--quality", default=None, help="override the recorded quality")
    ap.add_argument("--timeout", type=float, default=0.0)
    ap.add_argument("--out", default=None,
                    help="output path; only legal for a direct-generation recipe")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the resolved plan (prompt source, refs, steps) and stop; "
                         "no backup, no image call")
    ap.add_argument("--no-backup", action="store_true")
    ap.add_argument("--allow-no-refs", action="store_true",
                    help="permit a recovered generation with zero reference images")
    a = ap.parse_args(argv)

    chain = resolve_chain(Path(a.target))
    plan = build_plan(chain, a.note,
                      {"model": a.model, "size": a.size, "quality": a.quality},
                      Path(a.out).expanduser() if a.out else None,
                      allow_no_refs=a.allow_no_refs)

    gen = plan["generation"]
    print(f"[reroll] slot:    {plan['final']}")
    print(f"[reroll] source:  {plan['source']}")
    print(f"[reroll] model:   {gen['model']}  size: {gen['size']}  quality: {gen['quality']}")
    print(f"[reroll] prompt:  {len(gen['prompt'])} chars"
          + (f"  (+ note: {plan['note']!r})" if plan['note'] else "  (identical re-roll)"))
    for r in gen["refs"]:
        print(f"[reroll] ref:     {r}")
    for d in plan["derives"]:
        print(f"[reroll] then:    {d['kind']} -> {d['out']}")

    if a.dry_run:
        print("[reroll] DRY RUN: would generate exactly the above. No image call made.")
        print(readback_reminder(plan["final"]))
        return 0

    root = abu_root()
    # The durable generation record beside the slot (`<slot>-gen.recipe.json`). It is
    # overwritten below when the chain has derives, and the previous roll's copy is an
    # ATTESTATION, so it goes into the backup with everything else.
    durable = plan["final"].parent / (plan["final"].stem + "-gen" + RECIPE_SUFFIX)
    if not a.no_backup:
        overwritten = ([plan["final"]] + [d["out"] for d in plan["derives"] if d["out"]]
                       + [durable])
        dest = backup(list(dict.fromkeys(overwritten)), plan["final"].parent)
        if dest:
            print(f"[reroll] backed up the previous roll -> {dest}")

    scratch = Path(tempfile.mkdtemp(prefix="abu-reroll-"))
    pf = scratch / "prompt.txt"
    pf.write_text(gen["prompt"])
    gen_out = plan["gen_target"] or (scratch / "reroll-gen.png")

    cmd = [sys.executable, str(root / "skills/on-brand-image/scripts/generate.py"),
           "--out", str(gen_out), "--prompt-file", str(pf),
           "--model", gen["model"], "--size", gen["size"], "--quality", gen["quality"],
           "--no-open"]
    for r in gen["refs"]:
        cmd += ["--ref", r]
    if a.timeout:
        cmd += ["--timeout", str(a.timeout)]
    if subprocess.run(cmd).returncode != 0 or not gen_out.exists():
        sys.exit("reroll: generation FAILED; previous roll is untouched"
                 + ("" if a.no_backup else " (and backed up)"))

    # Record what this was: a re-roll of a recorded recipe, with the delta named.
    gen_recipe = gen_out.with_name(gen_out.name + RECIPE_SUFFIX)
    try:
        rec = load(gen_recipe)
        rec["rerolledFrom"] = {"target": str(plan["final"]),
                               "source": plan["source"], "note": plan["note"]}
        gen_recipe.write_text(json.dumps(rec, indent=2))
    except (json.JSONDecodeError, OSError):
        pass

    src = gen_out
    for d in plan["derives"]:
        if d["kind"] == "conform":
            args_ = d["args"]
            c = [sys.executable, str(root / "skills/cover/scripts/conform_cover.py"),
                 str(src), str(d["out"]),
                 "--aspect", str(args_.get("aspect") or "3:4"),
                 "--mode", str(args_.get("mode") or "pad"),
                 "--inset", str(args_.get("inset", 1.0)),
                 "--blur", str(args_.get("blur", 40))]
            if args_.get("keyline"):
                c += ["--keyline", str(args_["keyline"])]
            if subprocess.run(c).returncode != 0:
                sys.exit(f"reroll: conform step FAILED for {d['out']}")
        elif d["kind"] == "publish":
            sys.path.insert(0, str(root / "skills/cover/scripts"))
            from cover_provenance import write_derivative_recipe
            d["out"].write_bytes(Path(src).read_bytes())
            write_derivative_recipe(
                d["out"], src,
                tool="abu:reroll-slot/scripts/reroll_from_recipe.py",
                args={"publish": "platform-facing copy of the conformed re-roll"},
                transform="copy (byte-identical; no resample, no crop, no repaint)",
                role="conformed cover",
                note=("DERIVATIVE, not a generation. Platform-facing name for the "
                      "conformed re-roll: byte-identical to the file in derivedFrom, "
                      "whose own recipe records the render that made the art. "
                      "Published by reroll_from_recipe.py so the copy and its "
                      "provenance can never be done by hand, or half-done."))
        src = d["out"]

    if plan["gen_target"] is None and gen_recipe.exists():
        # Persist the generation record beside the slot (the `<slot>-gen.recipe.json`
        # convention), so the full ref list survives even a future in-place transform.
        # The previous roll's copy was backed up above; this one describes the roll
        # now on disk.
        shutil.copy2(gen_recipe, durable)

    print(f"[reroll] DONE -> {plan['final']}")
    print(readback_reminder(plan["final"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
