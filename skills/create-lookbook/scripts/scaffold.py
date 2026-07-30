#!/usr/bin/env python3
"""
scaffold.py — scaffold a Lookbook (SPEC §4.7.1): a portable <lookbook>/lookbook.json + refs/.

A Lookbook is the COMPLEMENT of a Style Pack. A Style Pack says "match this ONE look"
(anchor first, clone the style). A Lookbook says "draw from THIS RANGE; every instance
must differ; never clone one exemplar." It exists for curated-but-VARIED visual
vocabularies — a wardrobe/fashion, a set of building silhouettes, a range of faces —
where motif/prop are wrong (they force sameness) and a Style Pack is wrong (it is a
render medium, not subject variety).

Copies the exemplars INTO the lookbook (self-contained, §3a), writes the manifest, and
validates. Requires a `--variety-rule` (the instruction passed on every render) and a
`--gate` (a lookbook without a variety gate is just a mood board that will drift to
uniform). No anchor: there is no single look to match.

Usage:
  python3 scaffold.py --dir <lookbook-dir> --id <id> --name "<Name>" \\
    --ref <a.png> --ref <b.png> [...]          (4-12 VARIED exemplars) \\
    --aesthetic "<one line describing the vocabulary>" \\
    --variety-rule "<how to vary; passed on every render>" \\
    --gate "<variety assertion>" [--gate ...]  (>=1 required) \\
    --min-refs 3
"""
import argparse, hashlib, json, os, shutil, sys

def _sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def _same_bytes(a, b):
    try:
        return os.path.getsize(a) == os.path.getsize(b) and _sha256(a) == _sha256(b)
    except OSError:
        return False

def _carry_provenance(src, dest):
    """Copy <image>.recipe.json alongside the image it describes.

    generate.py writes provenance as a sidecar next to the render. A scaffolder that
    copies only the image strands that sidecar wherever the render was staged, so the
    landed exemplar is un-auditable: no divergence check can run against it and
    universe-doctor cannot score it. Every caller was hand-copying the sidecars after
    the fact (four times in one session before this was promoted), which is the
    definition of a framework gap. Returns True if a sidecar was carried.
    """
    sidecar = src + ".recipe.json"
    if not os.path.exists(sidecar):
        return False
    target = dest + ".recipe.json"
    if os.path.abspath(sidecar) != os.path.abspath(target):
        shutil.copy2(sidecar, target)
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--id", required=True); ap.add_argument("--name", required=True)
    ap.add_argument("--ref", action="append", default=[])
    ap.add_argument("--aesthetic", required=True)
    ap.add_argument("--variety-rule", required=True)
    ap.add_argument("--gate", action="append", default=[])
    ap.add_argument("--min-refs", type=int, default=3)
    a = ap.parse_args()

    if not a.gate:
        sys.exit("scaffold: a Lookbook MUST have >=1 --gate (a gateless lookbook drifts to uniform)")

    book = os.path.abspath(a.dir)
    refs_dir = os.path.join(book, "refs")
    os.makedirs(refs_dir, exist_ok=True)

    srcs, seen = [], set()
    for p in a.ref:
        ap_ = os.path.abspath(os.path.expanduser(p))
        if not os.path.exists(ap_): sys.exit(f"scaffold: ref not found: {ap_}")
        if ap_ in seen: continue
        seen.add(ap_); srcs.append(ap_)
    if not (4 <= len(srcs) <= 12):
        sys.exit(f"scaffold: need 4-12 VARIED exemplars (got {len(srcs)}); the point is range")

    ref_rel, carried = [], []
    for src in srcs:
        base = os.path.basename(src)
        dest = os.path.join(refs_dir, base); n = 1
        # RE-RUNNING A SCAFFOLD MUST NOT FORK THE MANIFEST OFF ITS PROVENANCE.
        #
        # The rename loop below exists so two DIFFERENT sources sharing a basename
        # do not clobber each other. But on a re-run (adding exemplars to an
        # existing lookbook, which is the normal way a lookbook grows) the file
        # already sitting in refs/ is a byte-identical copy of this same source.
        # Renaming it to `<stem>-1.png` then pointed the manifest at the copy while
        # `<stem>.png.recipe.json` stayed beside the original, so every re-scaffolded
        # exemplar silently lost its provenance and the folder doubled in size.
        # Earned 2026-07-30, christofuturism: 8 of 12 women's plates, caught only by
        # a manual provenance audit. Identical content therefore reuses the name.
        while (os.path.exists(dest) and os.path.abspath(dest) != src
               and not _same_bytes(dest, src)):
            stem, ext = os.path.splitext(base); dest = os.path.join(refs_dir, f"{stem}-{n}{ext}"); n += 1
        if os.path.abspath(dest) != src: shutil.copy2(src, dest)
        carried.append(_carry_provenance(src, dest))
        ref_rel.append(os.path.relpath(dest, book))

    manifest = {
        "id": a.id, "kind": "lookbook", "name": a.name,
        "refs": ref_rel,
        "aesthetic": a.aesthetic,
        "varietyRule": a.variety_rule,
        "gate": a.gate,
        "minRefs": a.min_refs,
    }
    with open(os.path.join(book, "lookbook.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    for r in ref_rel:
        if not os.path.exists(os.path.join(book, r)): sys.exit(f"scaffold: ref did not land: {r}")
    bare = [os.path.basename(r) for r, ok in zip(ref_rel, carried) if not ok]
    if bare:
        print(f"  WARNING: {len(bare)} exemplar(s) landed with NO recipe sidecar: "
              + ", ".join(bare) + ". These are un-auditable: no divergence check can\n"
              "  ever run against them. Prefer exemplars made by generate.py, which writes\n"
              "  <image>.recipe.json beside every render (this scaffolder carries it along).")
    print(f"[lookbook] OK  {a.id}  ({len(ref_rel)} exemplars, {len(a.gate)} variety gate(s), "
          f"provenance {len(ref_rel) - len(bare)}/{len(ref_rel)})  -> {book}/lookbook.json")

if __name__ == "__main__":
    main()
