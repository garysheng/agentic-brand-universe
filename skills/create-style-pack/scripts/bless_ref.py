#!/usr/bin/env python3
"""
bless_ref.py — record that a HUMAN individually approved one ref of a Style Pack (SPEC §4.7).

A pack is built from "blessed reference images", and until now nothing on disk could say
WHICH ones a person actually looked at. `create-style-pack` copies every ref in the same
way, so a ref the operator blessed by name and a candidate the scaffolder swept in beside
it are byte-indistinguishable. The distinction is load-bearing and it is not bookkeeping:

  * The ANCHOR is passed FIRST on every render the pack will ever make, so an unblessed
    anchor propagates one unreviewed decision into every future image.
  * A reference outranks a word. A ref nobody vetted teaches whatever it happens to show,
    including the defect the gate is trying to catch.

The framework already had the primitive twice and could not point it at a pack:
`chain_matrix.py --bless-seed` blesses an ENTITY's seed shot, and `abu import-asset
--blessed-by` blesses an asset at the moment it is IMPORTED. Neither takes a pack.

THE MARKER IS BOUND TO THE BYTES. It records the ref's sha256, so a blessing is
falsifiable: re-roll the ref and the marker goes STALE rather than silently continuing to
claim approval of an image nobody saw. This mirrors `--bless-seed`'s `sha256_16` and the
engine's `goldenDigest`.

`--by` IS REQUIRED AND IS NOT DEFAULTED. `--bless-seed` hardcodes `blessedBy: "human"`
(docs/GAPS.md G12), which cannot distinguish the operator from a delegated agent read-back,
so the marker cannot be audited later. Say who, and when.

Usage:
  bless_ref.py <pack-dir> --status
  bless_ref.py <pack-dir> --ref <name> --by "<who, when>" [--note "<why>"] [--rebless]
"""
import argparse, datetime, hashlib, json, os, sys


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_pack(pack_dir):
    manifest = os.path.join(pack_dir, "pack.json")
    if not os.path.exists(manifest):
        sys.exit(f"bless: no pack.json in {pack_dir} (a Style Pack is pack.json + refs/)")
    try:
        with open(manifest) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        sys.exit(f"bless: {manifest} is not valid JSON: {e}")


def marker_path(pack_dir, ref_rel):
    return os.path.join(pack_dir, ref_rel + ".blessed.json")


def resolve_ref(pack, ref_arg):
    """Accept 'refs/x.png', 'x.png' or 'x'. A blessing on a file the pack does not
    LIST is a blessing of nothing, so an unlisted ref is refused rather than written."""
    refs = pack.get("refs") or []
    cands = [r for r in refs
             if r == ref_arg
             or os.path.basename(r) == ref_arg
             or os.path.splitext(os.path.basename(r))[0] == ref_arg]
    if len(cands) == 1:
        return cands[0]
    if not cands:
        sys.exit(f"bless: '{ref_arg}' is not a ref of this pack. Its refs are:\n  "
                 + "\n  ".join(refs)
                 + "\nA blessing on a file the pack does not list is a blessing of nothing.")
    sys.exit(f"bless: '{ref_arg}' is ambiguous, it matches {len(cands)}: {', '.join(cands)}")


def read_marker(pack_dir, ref_rel):
    p = marker_path(pack_dir, ref_rel)
    if not os.path.exists(p):
        return None
    try:
        with open(p) as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"_unreadable": True}


def state_of(pack_dir, ref_rel):
    """-> (state, marker). One of: unblessed | blessed | STALE | MISSING | UNREADABLE."""
    img = os.path.join(pack_dir, ref_rel)
    if not os.path.exists(img):
        return "MISSING", None
    m = read_marker(pack_dir, ref_rel)
    if m is None:
        return "unblessed", None
    if m.get("_unreadable"):
        return "UNREADABLE", None
    return ("blessed" if m.get("sha256") == sha256(img) else "STALE"), m


def cmd_status(pack_dir, pack):
    refs = pack.get("refs") or []
    anchor = pack.get("anchor")
    rows, blessed = [], 0
    for r in refs:
        st, m = state_of(pack_dir, r)
        if st == "blessed":
            blessed += 1
        rows.append((r, st, m))

    print(f"pack: {pack.get('id', '(no id)')}  ({pack_dir})")
    for r, st, m in rows:
        tag = " [ANCHOR]" if r == anchor else ""
        who = f"  <- {m['blessedBy']}, {m.get('blessedOn', '?')}" if m and st in ("blessed", "STALE") else ""
        print(f"  {st.ljust(9)} {r}{tag}{who}")
        if st == "STALE":
            print("            the bytes changed since the blessing; it approves an image "
                  "nobody saw. Re-bless with --rebless, or restore the blessed file.")
    print(f"\n{blessed} of {len(refs)} refs individually blessed.")

    unblessed = [r for r, st, _ in rows if st != "blessed"]
    if unblessed:
        print("The rest are CANDIDATES: present in the pack, not individually approved. "
              "Say so when reporting the pack rather than calling the whole set blessed.")
    # The anchor is passed FIRST on every render, so it carries the most reach of any ref.
    if anchor:
        a_state = dict((r, st) for r, st, _ in rows).get(anchor)
        if a_state != "blessed":
            print(f"\nWARNING: the ANCHOR ({anchor}) is {a_state}. It is passed FIRST on "
                  "every render this pack will ever make, so it is the one ref whose "
                  "approval propagates into everything downstream.")
    return 0


def cmd_bless(pack_dir, pack, ref_arg, by, note, rebless):
    ref_rel = resolve_ref(pack, ref_arg)
    img = os.path.join(pack_dir, ref_rel)
    if not os.path.exists(img):
        sys.exit(f"bless: {ref_rel} is listed in pack.json but not on disk at {img}")

    existing = read_marker(pack_dir, ref_rel)
    if existing and not existing.get("_unreadable") and not rebless:
        st, _ = state_of(pack_dir, ref_rel)
        sys.exit(f"bless: {ref_rel} already carries a blessing ({st}) by "
                 f"{existing.get('blessedBy')!r} on {existing.get('blessedOn')}. "
                 "Pass --rebless to replace it; a blessing is a record of a human act "
                 "and overwriting one silently would erase who approved what.")

    digest = sha256(img)
    rec = {
        "ref": ref_rel,
        "sha256": digest,
        "blessedBy": by,
        "blessedOn": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "note": note or "",
        "why": "A Style Pack ref is a load-bearing input, not decoration: the anchor is "
               "passed FIRST on every render and a reference outranks a word. This marker "
               "records that a named person looked at THESE BYTES and approved them. If the "
               "file changes, the sha256 no longer matches and the blessing reads STALE "
               "rather than silently transferring to an image nobody saw.",
    }
    if existing and not existing.get("_unreadable"):
        rec["replaced"] = {k: existing.get(k) for k in ("blessedBy", "blessedOn", "sha256")}

    out = marker_path(pack_dir, ref_rel)
    with open(out, "w") as f:
        json.dump(rec, f, indent=1)
        f.write("\n")
    print(f"blessed: {ref_rel}")
    print(f"  by     {by}")
    print(f"  sha256 {digest[:16]}...")
    print(f"  marker {out}")
    if ref_rel == pack.get("anchor"):
        print("  (this is the ANCHOR, passed first on every render this pack makes)")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("pack", help="the Style Pack directory (holding pack.json + refs/)")
    ap.add_argument("--ref", default=None,
                    help="the ref to bless: 'refs/x.png', 'x.png' or 'x'")
    ap.add_argument("--by", default=None,
                    help="WHO approved it and when, verbatim, e.g. 'Gary Sheng, 2026-08-20'. "
                         "Required, and deliberately not defaulted to \"human\": a marker "
                         "that cannot tell the operator from a delegated agent read-back "
                         "cannot be audited (docs/GAPS.md G12)")
    ap.add_argument("--note", default=None, help="what they said, or what the blessing covers")
    ap.add_argument("--rebless", action="store_true",
                    help="replace an existing blessing (the previous one is kept under `replaced`)")
    ap.add_argument("--status", action="store_true",
                    help="report which refs are blessed, stale or candidates, and warn on an "
                         "unblessed anchor")
    a = ap.parse_args()

    pack_dir = os.path.abspath(os.path.expanduser(a.pack))
    pack = load_pack(pack_dir)

    if a.status or not a.ref:
        if a.ref or a.by:
            sys.exit("bless: --status takes no --ref/--by")
        return cmd_status(pack_dir, pack)

    if not a.by:
        sys.exit("bless: --by is REQUIRED. Record who approved this ref and when "
                 "(e.g. --by 'Gary Sheng, 2026-08-20'). An unattributed blessing is "
                 "an assertion nobody can check later.")
    return cmd_bless(pack_dir, pack, a.ref, a.by, a.note, a.rebless)


if __name__ == "__main__":
    sys.exit(main())
