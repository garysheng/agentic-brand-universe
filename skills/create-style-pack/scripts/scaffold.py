#!/usr/bin/env python3
"""
scaffold.py — scaffold a Style Pack (SPEC §4.7): a portable <pack>/pack.json + refs/.

Copies the blessed reference images INTO the pack (self-contained, §3a), writes the
manifest, and validates that every ref resolves and the anchor is one of the refs.
A pack without a `gate` is rejected: a gateless pack is a mood board, not a Style Pack.

Usage:
  python3 scaffold.py --dir <pack-dir> --id <id> --name "<name>" \\
    --anchor <path-to-anchor.png> \\
    --ref <path.png> [--ref ...]            (3-8 total, anchor auto-included) \\
    --style-line "<one-line look>" \\
    --palette-ground '#0a1030,#141c46' [--palette-fill ... --palette-line ...] \\
    --reject <pole> [--reject ...] \\
    --gate "<assertion>" [--gate ...]       (>=1 required) \\
    --max-elements 5
"""
import argparse, json, os, shutil, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--id", required=True); ap.add_argument("--name", required=True)
    ap.add_argument("--anchor", required=True)
    ap.add_argument("--ref", action="append", default=[])
    ap.add_argument("--style-line", required=True)
    ap.add_argument("--palette-ground", default=""); ap.add_argument("--palette-fill", default=""); ap.add_argument("--palette-line", default="")
    ap.add_argument("--reject", action="append", default=[])
    ap.add_argument("--gate", action="append", default=[])
    ap.add_argument("--max-elements", type=int, default=5)
    a = ap.parse_args()

    if not a.gate:
        sys.exit("scaffold: a Style Pack MUST have >=1 --gate assertion (a gateless pack is a mood board)")

    pack = os.path.abspath(a.dir)
    refs_dir = os.path.join(pack, "refs")
    os.makedirs(refs_dir, exist_ok=True)

    # anchor is always a ref; de-dup by source path, preserve order (anchor first)
    src_list, seen = [], set()
    for p in [a.anchor] + a.ref:
        ap_ = os.path.abspath(os.path.expanduser(p))
        if not os.path.exists(ap_): sys.exit(f"scaffold: ref not found: {ap_}")
        if ap_ in seen: continue
        seen.add(ap_); src_list.append(ap_)
    if not (3 <= len(src_list) <= 8):
        sys.exit(f"scaffold: need 3-8 refs total (got {len(src_list)}); the look is the references")

    ref_rel = []
    anchor_rel = None
    for i, src in enumerate(src_list):
        base = os.path.basename(src)
        # keep basenames unique inside the pack
        dest = os.path.join(refs_dir, base)
        n = 1
        while os.path.exists(dest) and os.path.abspath(dest) != src:
            stem, ext = os.path.splitext(base); dest = os.path.join(refs_dir, f"{stem}-{n}{ext}"); n += 1
        if os.path.abspath(dest) != src:
            shutil.copy2(src, dest)
        rel = os.path.relpath(dest, pack)
        ref_rel.append(rel)
        if i == 0: anchor_rel = rel

    palette = {}
    if a.palette_ground: palette["ground"] = [c.strip() for c in a.palette_ground.split(",") if c.strip()]
    if a.palette_fill:   palette["fill"]   = [c.strip() for c in a.palette_fill.split(",") if c.strip()]
    if a.palette_line:   palette["line"]   = [c.strip() for c in a.palette_line.split(",") if c.strip()]

    manifest = {
        "id": a.id, "name": a.name,
        "anchor": anchor_rel,
        "refs": ref_rel,
        "palette": palette,
        "styleLine": a.style_line,
        "rejectedPoles": a.reject,
        "gate": a.gate,
        "maxElements": a.max_elements,
    }
    with open(os.path.join(pack, "pack.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    # validate: every ref resolves, anchor is in refs
    for r in ref_rel:
        if not os.path.exists(os.path.join(pack, r)): sys.exit(f"scaffold: ref did not land: {r}")
    if anchor_rel not in ref_rel: sys.exit("scaffold: anchor must be one of refs")
    print(f"[style-pack] OK  {a.id}  ({len(ref_rel)} refs, {len(a.gate)} gate assertions)  -> {pack}/pack.json")

if __name__ == "__main__":
    main()
