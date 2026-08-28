#!/usr/bin/env python3
"""Render one spread, or a whole book: assemble each job from canon, then generate.

Thin wrapper over assemble_prompt.py (the deterministic, tested core) + the
chatgpt-images generate_image.py. The assemble step is pure software; only this
wrapper touches the model. Re-rolls are the caller's loop: render, run
render-readback, and on a DEFECT call again (the model is stochastic).

Usage:
  render_spread.py <universe> <render-spec.json> <spread-id> --out <path>
      [--skip-existing] [--quality high] [--print-prompt] [--dry-run]

  render_spread.py <universe> <render-spec.json> --all --out-dir spreads/ --jobs 4
  render_spread.py <universe> <render-spec.json> spread-01 spread-02 --out-dir spreads/

BATCH MODE (added 2026-07-31). This script took exactly one spread id, so EVERY
book grew its own parallel driver: a dozen lines of ThreadPoolExecutor over this
same subprocess, plus a skip-if-exists the script already implements. `pave-the-path`
flagged "the renderer's own batch mode" after she-had-everything-but-peace and it
was not built; the-power-of-obeying wrote the identical driver again. Two runs is
the bar, so it lives here now.

`--jobs` defaults to 1, so single-spread behaviour is unchanged: same stdout, same
exit codes. A per-spread failure never aborts the batch (the expensive spreads that
DID land must survive one that did not), and the batch exits nonzero if any spread
failed or refused.
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assemble_prompt import build, load, Refuse  # noqa: E402

# The image provider hard-rejects a prompt over this many characters with a 400. It is the
# provider's limit, not ours; keep it here so the refusal and the warning share one number.
PROMPT_CAP = 32000


def _abu_root(start=None):
    """The ABU root, found by walking UP for a marker instead of counting parents.

    A fixed `parents[N]` encodes one directory layout. This code runs from at least
    two: a git clone, and a plugin cache under ~/.claude/plugins. Counting worked in
    the clone and would fail silently or wrongly in the other, which is the class of
    bug that made the framework uninstallable in the first place."""
    from pathlib import Path as _PP
    p = _PP(start or __file__).resolve()
    for c in [p, *p.parents]:
        if (c / "engine" / "agenticstory").is_dir():
            return c
    raise SystemExit(
        "abu: cannot locate the ABU root from " + str(p) + ".\n"
        "  Looked upward for engine/agenticstory. If ABU was installed as a plugin,\n"
        "  reinstall it: /plugin marketplace add garysheng/agentic-brand-universe")


def _provider_script(provider="gpt-image-2"):
    """The generation script, resolved rather than assumed. This script lives at
    <repo>/skills/<name>/scripts/, so the repo root is 3 up; `.resolve()` first
    because skills are installed by symlinking into ~/.claude/skills."""
    from pathlib import Path as _P
    eng = str(_abu_root() / "engine")
    if eng not in sys.path:
        sys.path.insert(0, eng)
    from agenticstory.providers import resolve_str
    return resolve_str(provider)


def _guarded_length(prompt: str) -> int:
    """The length the PROVIDER will actually send, not the length we hand it.

    `apply_prompt_guards` appends up to seven standing guard blocks after the compiler is
    done, several thousand characters in a busy spread. Measuring the pre-guard string
    under-reports the real prompt, which is worse than not measuring at all: it reports a
    comfortable number for a render that then 400s. Earned 2026-08-21, on the first day the
    budget check existed: a spread whose dry run said 26,325/32,000 assembled 32,308 and
    failed three times.
    """
    try:
        from pathlib import Path as _P
        prov = _P(_provider_script()).parent
        if str(prov) not in sys.path:
            sys.path.insert(0, str(prov))
        from prompt_guards import apply_prompt_guards
        guarded, _ = apply_prompt_guards(prompt)
        return len(guarded)
    except Exception:
        # Never let the measurement break a render it was only meant to describe.
        return len(prompt)


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


def render_one(args, spec: dict, sid: str, out: Path, echo) -> int:
    """Render ONE spread. Returns 0 ok/skip, 1 generation failure, 2 refusal.

    `echo` collects output so a parallel batch prints each spread's lines
    together instead of interleaving them into noise.
    """
    # `--out` IS A FILE PATH, NEVER A DIRECTORY. Handed a directory, `out.exists()`
    # is true for every spread, so `--skip-existing` reported "exists, skip" 72 times
    # and the batch rendered NOTHING while exiting 0. Earned 2026-08-01 on
    # will-there-be-ice-cream. Silent, total, and indistinguishable from success.
    if out.is_dir():
        echo(f"REFUSE {sid}: --out is a FILE path, not a directory ({out}). "
             f"Pass --out {out}/{sid}.png. Handed a directory, --skip-existing sees it "
             f"already exists and skips every spread while still exiting 0.", err=True)
        return 2

    if args.skip_existing and out.exists():
        echo(f"{sid}: exists, skip")
        return 0

    try:
        job = build(Path(args.universe), spec, sid)
    except Refuse as e:
        echo(f"REFUSE {sid}: {e}", err=True)
        return 2
    except Exception as e:
        # NOTHING one spread does may kill the batch. An unexpected error here
        # used to escape as a traceback, and in a 69-spread run that discarded
        # every spread queued behind it. Name the spread, keep going.
        echo(f"REFUSE {sid}: {type(e).__name__}: {e}", err=True)
        return 2

    if args.print_prompt:
        echo("PROMPT:\n" + job["prompt"] + "\n")
        echo("REFS (" + str(len(job["refs"])) + "):")
        for r in job["refs"]:
            echo("  " + r)

    # Advisory findings surface on EVERY run, dry or paid. A warning the operator only
    # sees on --dry-run is a warning nobody sees, because the paid run is the one they do.
    for w in job.get("warnings") or []:
        echo(f"  warn {sid}: {w}")

    # THE PROMPT BUDGET IS THE ONE NUMBER THAT DECIDES WHETHER A PAID RUN CAN SUCCEED,
    # and it was the one number never reported. The provider hard-400s above PROMPT_CAP,
    # so a spread whose accumulated entity prose and negatives crossed it burned three
    # attempts and a retry backoff before saying so, and its --dry-run said "ok" first.
    # Earned 2026-08-21 (nation-of-fire, the-deal-composer): three spreads failed this way
    # in one session, each time after the dry run passed.
    n = _guarded_length(job["prompt"])
    pct = round(100 * n / PROMPT_CAP)
    if n > PROMPT_CAP:
        echo(f"REFUSE {sid}: assembled prompt is {n} characters WITH THE PROVIDER GUARDS APPLIED, "
             f"over the provider cap of "
             f"{PROMPT_CAP}. Nothing was generated and nothing was spent. The prompt is the "
             f"register line plus EVERY cast entity's render prose, invariants and negatives, "
             f"plus the scene and this spread's negatives. Trim the SPREAD first if it "
             f"restates a rule an entity already carries; a rule belongs on the entity once, "
             f"not in each spread that casts it. `abu lint-universe` reports bloated entities.",
             err=True)
        return 2
    if pct >= 90:
        echo(f"  warn {sid}: prompt is {n}/{PROMPT_CAP} characters ({pct}% of the cap)")

    if args.dry_run:
        echo(f"{sid}: DRY RUN ok ({len(job['refs'])} refs, "
             f"{len(job['qa'])} qa invariants, size {job['size']}, "
             f"prompt {n}/{PROMPT_CAP}) — nothing generated")
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    # A FAILED RENDER MUST NOT LEAVE A PLAUSIBLE ARTIFACT. The attempt loop below checks
    # `out.exists()`, which is correct for THIS process, but a stale file already sitting at
    # this path survives a total failure, so any caller that checks "does the file exist" or
    # "is it a reasonable size" reads a 400 as a success. Earned 2026-08-21: a batch of three
    # spreads 400'd on prompt length, left three unrelated older images at those paths, and
    # the size check passed; the wrong pictures were reviewed as if they were the new render.
    # ...but a re-roll of GOOD art must not lose it to a flaky provider either. So the
    # previous render is MOVED ASIDE rather than deleted, and on total failure it is left at
    # `<out>.prev`, never restored to `out`. `out` stays absent, so the stale-reads-as-new
    # hazard above is unchanged, and the operator still has the picture. Earned 2026-08-28:
    # a 48-spread book re-rolled two good spreads, the provider dropped every attempt, and
    # both images were gone with nothing to fall back on.
    recipe_path = out.with_suffix(out.suffix + ".recipe.json")
    prev = out.with_suffix(out.suffix + ".prev")
    prev_recipe = recipe_path.with_suffix(recipe_path.suffix + ".prev")
    # CLEAR THE OLD BACKUP ONLY WHEN THERE IS A LIVE FILE TO PUT IN ITS PLACE. Unlinking it
    # first looks equivalent and is not: on the SECOND attempt of a retry loop `out` is already
    # gone (the first attempt banked it), so an unconditional unlink deletes the banked art and
    # replaces it with nothing. That destroys exactly what this block exists to protect, and it
    # did, one commit after the block was written.
    for live, kept in ((out, prev), (recipe_path, prev_recipe)):
        if live.exists():
            if kept.exists():
                kept.unlink()
            live.replace(kept)
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

    # Serial keeps the provider's own output inline (the operator is watching one
    # render). Parallel captures it, or N models write over each other.
    capture = args.jobs > 1
    for attempt in (1, 2, 3):
        p = subprocess.run(cmd, capture_output=capture, text=True)
        if p.returncode == 0 and out.exists():
            recipe = write_recipe(out, Path(args.universe), spec, sid, job, args.quality)
            for kept in (prev, prev_recipe):
                if kept.exists():
                    kept.unlink()
            echo(f"{sid}: OK -> {out} (+ {recipe.name})")
            return 0
        tail = ""
        if capture:
            lines = ((p.stdout or "") + (p.stderr or "")).strip().splitlines()
            tail = ": " + lines[-1][:300] if lines else ""
        echo(f"{sid}: attempt {attempt} failed rc={p.returncode}{tail}", err=True)
        if attempt < 3:
            time.sleep(10 * attempt)
    if prev.exists():
        echo(f"{sid}: the PREVIOUS render was kept at {prev.name}; {out.name} is absent "
             f"because this run produced nothing. Rename it back only if you decide to "
             f"accept the old picture.", err=True)
    return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("universe")
    ap.add_argument("render_spec")
    ap.add_argument("spread", nargs="*",
                    help="one or more spread ids. Omit and pass --all for every "
                         "spread in the render-spec.")
    ap.add_argument("--all", action="store_true",
                    help="render every spread the render-spec declares")
    ap.add_argument("--out", help="output path. Single spread only.")
    ap.add_argument("--out-dir",
                    help="output directory; each spread is written as <id>.png. "
                         "Required for more than one spread, because --out cannot "
                         "name N files.")
    ap.add_argument("--jobs", type=int, default=1, metavar="N",
                    help="render N spreads concurrently (default 1). Provider output "
                         "is captured when N > 1.")
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

    try:
        spec = load(Path(args.render_spec))
    except Refuse as e:
        print(f"REFUSE: {e}", file=sys.stderr)
        return 2

    ids = list(args.spread)
    if args.all:
        declared = [s["id"] for s in spec.get("spreads", []) if s.get("id")]
        ids = ids + [d for d in declared if d not in ids]
    if not ids:
        ap.error("name at least one spread id, or pass --all")

    if len(ids) > 1 or args.out_dir:
        if not args.out_dir:
            ap.error("--out cannot name %d files; use --out-dir" % len(ids))
        if args.out:
            ap.error("--out and --out-dir are mutually exclusive")
        outs = {sid: Path(args.out_dir) / f"{sid}.png" for sid in ids}
    else:
        if not args.out:
            ap.error("--out is required for a single spread (or use --out-dir)")
        outs = {ids[0]: Path(args.out)}

    # ONE spread, serial: print straight through, so behaviour is byte-identical
    # to before batch mode existed.
    if len(ids) == 1 and args.jobs <= 1:
        def echo(msg, err=False):
            print(msg, file=sys.stderr if err else sys.stdout)
        return render_one(args, spec, ids[0], outs[ids[0]], echo)

    def work(sid):
        buf: list[tuple[str, bool]] = []
        code = render_one(args, spec, sid, outs[sid], lambda m, err=False: buf.append((m, err)))
        return sid, code, buf

    results: dict[str, int] = {}
    jobs = max(1, args.jobs)
    with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
        for sid, code, buf in ex.map(work, ids):
            for msg, err in buf:
                print(msg, file=sys.stderr if err else sys.stdout, flush=True)
            results[sid] = code

    failed = [s for s, c in results.items() if c == 1]
    refused = [s for s, c in results.items() if c == 2]
    print(f"\nbatch: {len(results) - len(failed) - len(refused)}/{len(results)} ok"
          + (f", {len(failed)} failed ({', '.join(failed)})" if failed else "")
          + (f", {len(refused)} REFUSED ({', '.join(refused)})" if refused else ""))
    if refused:
        return 2
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
