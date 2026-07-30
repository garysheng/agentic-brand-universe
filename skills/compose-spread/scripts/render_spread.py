#!/usr/bin/env python3
"""Render ONE spread: assemble the job from canon, then generate the image.

Thin wrapper over assemble_prompt.py (the deterministic, tested core) + the
chatgpt-images generate_image.py. The assemble step is pure software; only this
wrapper touches the model. Re-rolls are the caller's loop: render, run
render-readback, and on a DEFECT call again (the model is stochastic).

Usage:
  render_spread.py <universe> <render-spec.json> <spread-id> --out <path>
      [--skip-existing] [--quality high] [--print-prompt]
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assemble_prompt import build, load, Refuse  # noqa: E402

def _provider_script(provider="gpt-image-2"):
    """The generation script, resolved rather than assumed. This script lives at
    <repo>/skills/<name>/scripts/, so the repo root is 3 up; `.resolve()` first
    because skills are installed by symlinking into ~/.claude/skills."""
    from pathlib import Path as _P
    eng = str(_P(__file__).resolve().parents[3] / "engine")
    if eng not in sys.path:
        sys.path.insert(0, eng)
    from agenticstory.providers import resolve_str
    return resolve_str(provider)


def _sha16(path) -> str:
    """Short content hash, so a recipe pins the exact bytes it describes."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _git_head(repo) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True, text=True,
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except OSError:
        return ""


def write_recipe(out: Path, universe: Path, spec: dict, spread_id: str,
                 job: dict, quality: str) -> Path:
    """Write `<out>.recipe.json` beside the render.

    An asset without its recipe is not done: it cannot be reproduced, verified,
    or blessed. Records the model, the EXACT prompt, and every input reference
    by path + hash, plus the canon commit the prompt was assembled from.
    """
    descriptor = next(
        (s for s in spec.get("spreads", []) if s.get("id") == spread_id), None
    )
    recipe = {
        "asset": out.name,
        "assetSha256_16": _sha16(out),
        "provider": "openai",
        "model": "gpt-image-2",
        "quality": quality,
        "size": job["size"],
        "generatedBy": "abu:compose-spread render_spread.py",
        "universe": str(universe),
        "universeCommit": _git_head(universe),
        "book": spec.get("book"),
        "story": spec.get("story"),
        "spread": spread_id,
        "descriptor": descriptor,
        "prompt": job["prompt"],
        "refs": [{"path": r, "sha256_16": _sha16(r)} for r in job["refs"]],
        "qa": job["qa"],
    }
    path = out.with_suffix(out.suffix + ".recipe.json")
    path.write_text(json.dumps(recipe, indent=2) + "\n")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("universe")
    ap.add_argument("render_spec")
    ap.add_argument("spread")
    ap.add_argument("--out", required=True)
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--quality", default="high")
    ap.add_argument("--print-prompt", action="store_true",
                    help="print the assembled prompt and refs, THEN STILL RENDER. "
                         "Pair with --dry-run to inspect without spending.")
    # WHY THIS EXISTS (earned 2026-07-26, nation-of-fire book 18). Validating a
    # 32-spread render-spec before paying for it is the single most valuable thing
    # you can do with this script, and there was no way to ask for it: --print-prompt
    # reads like an inspection flag but prints and then generates anyway. A loop over
    # 32 spreads with --print-prompt, believed to be a free pre-flight, started
    # billing real renders. Refusals are pure text checks that cost nothing, so the
    # dry run catches every uncast character, bad plate key and missing ref for free.
    ap.add_argument("--dry-run", action="store_true",
                    help="assemble and validate only: never calls the image model. "
                         "Exits 0 if the spread would render, 2 on any refusal.")
    args = ap.parse_args()

    out = Path(args.out)
    if args.skip_existing and out.exists():
        print(f"{args.spread}: exists, skip")
        return 0

    try:
        spec = load(Path(args.render_spec))
        job = build(Path(args.universe), spec, args.spread)
    except Refuse as e:
        print(f"REFUSE: {e}", file=sys.stderr)
        return 2

    if args.print_prompt:
        print("PROMPT:\n" + job["prompt"] + "\n")
        print("REFS (" + str(len(job["refs"])) + "):")
        for r in job["refs"]:
            print("  " + r)

    if args.dry_run:
        print(f"{args.spread}: DRY RUN ok ({len(job['refs'])} refs, "
              f"{len(job['qa'])} qa invariants, size {job['size']}) — nothing generated")
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "uv", "run", _provider_script(),
        "--prompt", job["prompt"],
        "--filename", str(out),
        "--size", job["size"],
        "--quality", args.quality,
        "--no-open",
    ]
    for r in job["refs"]:
        cmd += ["--input-image", r]

    for attempt in (1, 2, 3):
        rc = subprocess.run(cmd).returncode
        if rc == 0 and out.exists():
            recipe = write_recipe(
                out, Path(args.universe), spec, args.spread, job, args.quality
            )
            print(f"{args.spread}: OK -> {out} (+ {recipe.name})")
            return 0
        print(f"{args.spread}: attempt {attempt} failed rc={rc}", file=sys.stderr)
        time.sleep(10 * attempt)
    return 1


if __name__ == "__main__":
    sys.exit(main())
