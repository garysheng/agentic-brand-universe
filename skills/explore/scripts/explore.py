#!/usr/bin/env python3
"""Render a comparison set that isolates ONE variable, and stage every roll.

The whole point is that the ONLY thing differing between outputs is the axis under
study, so the operator's eye has nothing else to explain a difference by.

  python3 explore.py --subject-file subject.txt --variants variants.txt \
      --out-dir ~/scratch/explore-material --style-pack <path> \
      [--ref <path> ...] [--ref-first] [--size 1024x1024] [--quality high] [--concurrency 3]

variants.txt: one variant per line, "id: text". Blank lines and # comments ignored.
Each render = subject + variant text. Nothing else changes between rolls.
"""
import argparse, concurrent.futures as cf, os, pathlib, subprocess, sys

GEN = pathlib.Path(__file__).resolve().parents[2] / "on-brand-image" / "scripts" / "generate.py"

def parse_variants(path):
    out = []
    for raw in pathlib.Path(path).read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            sys.exit(f"variant line missing 'id: text' -> {raw!r}")
        vid, text = line.split(":", 1)
        vid = vid.strip()
        if not vid or not text.strip():
            sys.exit(f"variant line missing id or text -> {raw!r}")
        out.append((vid, text.strip()))
    if not out:
        sys.exit("no variants found")
    ids = [v for v, _ in out]
    if len(set(ids)) != len(ids):
        sys.exit("duplicate variant ids")
    return out

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--subject-file", required=True, help="the INVARIANT half of the prompt")
    p.add_argument("--variants", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--style-pack")
    p.add_argument("--ref", action="append", default=[])
    p.add_argument("--ref-first", action="store_true")
    # A comparison set of a CANON entity (what should she wear at the gym, which chair
    # suits him) needs the entity's locked identity plates on every roll, or the six
    # variants come back as six different people and the axis under study is lost in
    # the noise. Until 2026-09-06 the only way to do that here was to hand-pick plates
    # and pass them as --ref, which every caller did differently. Forward the entity to
    # the adapter, which already resolves sheets, alt-looks and invariants from canon.
    p.add_argument("--entity", action="append", default=[],
                   help="UNIVERSE:ID[@LOOK], repeatable. Passes the entity's locked identity "
                        "plates and canon on every roll, resolved by the provider adapter.")
    p.add_argument("--entity-required-only", action="store_true",
                   help="pass only each entity's requiredForRender sheets (fewer references)")
    p.add_argument("--no-wardrobe", action="store_true",
                   help="skip the adapter's automatic wardrobe resolution from --entity; use "
                        "when the axis under study IS the wardrobe")
    p.add_argument("--size", default="1024x1024")
    p.add_argument("--quality", default="high")
    p.add_argument("--concurrency", type=int, default=3)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    if not GEN.exists():
        sys.exit(f"provider adapter not found at {GEN}")
    subject = pathlib.Path(a.subject_file).read_text().strip()
    variants = parse_variants(a.variants)
    out = pathlib.Path(os.path.expanduser(a.out_dir)); out.mkdir(parents=True, exist_ok=True)

    jobs = []
    for vid, text in variants:
        ptxt = out / f"{vid}.prompt.txt"
        ptxt.write_text(f"{subject} {text}\n")
        cmd = ["python3", str(GEN), "--out", str(out / f"{vid}.png"),
               "--prompt-file", str(ptxt), "--size", a.size, "--quality", a.quality, "--no-open"]
        if a.style_pack: cmd += ["--style-pack", os.path.expanduser(a.style_pack)]
        for r in a.ref: cmd += ["--ref", os.path.expanduser(r)]
        if a.ref_first: cmd.append("--ref-first")
        for e in a.entity: cmd += ["--entity", os.path.expanduser(e)]
        if a.entity_required_only: cmd.append("--entity-required-only")
        if a.no_wardrobe: cmd.append("--no-wardrobe")
        jobs.append((vid, cmd))

    print(f"[explore] {len(jobs)} variants -> {out}")
    if a.dry_run:
        for vid, cmd in jobs: print(f"  {vid}: {' '.join(cmd)}")
        print("[explore] dry run, nothing generated")
        return

    def run(job):
        vid, cmd = job
        log = out / f"{vid}.log"
        with open(log, "w") as fh:
            rc = subprocess.call(cmd, stdout=fh, stderr=subprocess.STDOUT)
        return vid, rc

    failed = []
    with cf.ThreadPoolExecutor(max_workers=max(1, a.concurrency)) as ex:
        for vid, rc in ex.map(run, jobs):
            ok = rc == 0 and (out / f"{vid}.png").exists()
            print(f"  {'ok  ' if ok else 'FAIL'} {vid}")
            if not ok: failed.append(vid)

    print(f"\n[explore] staged in {out}")
    print("[explore] every roll is KEPT. A render is not reproducible; never delete a candidate.")
    if failed:
        print(f"[explore] {len(failed)} failed, see <id>.log: {', '.join(failed)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
