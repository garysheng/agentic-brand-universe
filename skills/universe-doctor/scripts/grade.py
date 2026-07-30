#!/usr/bin/env python3
"""
grade.py — the Universe Doctor's scorecard engine.

Grades a brand universe on how COMPLETE and how HIGH-QUALITY it is, then emits a
prioritized punch-list of what to fix to raise the grade. Self-contained: reads the
universe's files directly (like lint.py), no engine import, no generation, no cost.

The rubric below IS the framework's definition of a "done, good" universe. Weights sum
to 100. Each dimension scores 0..max; overall maps to a letter grade.

    python3 grade.py <universe-dir> [--json]

Exit 0 always (a low grade is a report, not a failure).
"""
import json, os, pathlib, sys

# ---- rubric: (key, label, max_points) ---------------------------------------
RUBRIC = [
    ("validity",        "Validity (schema-valid canon)",          15),
    ("identity",        "Identity (register, anchor, mark, voice)", 15),
    ("entities",        "Entity reference matrices filled/locked",  25),
    ("setting_size",    "Settings prove their size (v0.9 scalePlate)", 10),
    ("provenance",      "Provenance on every generated image",      10),
    ("craft_canon",     "Craft-canon (encoded invariants/rules)",   10),
    ("stories",         "Stories composed over the canon",          10),
    ("self_contained",  "Self-contained (refs resolve in-repo)",     5),
]

def jload(p):
    try: return json.loads(pathlib.Path(p).read_text())
    except Exception: return None

def resolves(root, rel):
    if not rel: return False
    return (root / rel).exists()

def grade_universe(udir):
    root = pathlib.Path(udir)
    uni = jload(root / "universe.json") or {}
    ident = uni.get("identity", uni)  # some universes flatten identity at top level
    scores, issues = {}, []   # issues: (impact, dimension, what, fix_skill)

    # 1) VALIDITY -------------------------------------------------------------
    # lightweight: universe.json parses + every entity json parses + required id/kind.
    ents_dir = root / "canon" / "entities"
    ent_files = sorted(ents_dir.glob("*.json")) if ents_dir.exists() else []
    bad = []
    if not uni: bad.append("universe.json missing or unparseable")
    for f in ent_files:
        e = jload(f)
        if not e or "id" not in e or "kind" not in e:
            bad.append(f"entity {f.name} missing id/kind")
    scores["validity"] = 15 if not bad else max(0, 15 - 5 * len(bad))
    if bad:
        issues.append((15, "validity", "; ".join(bad[:3]), "abu validate"))

    # 2) IDENTITY -------------------------------------------------------------
    reg = ident.get("register", {}) if isinstance(ident, dict) else {}
    checks = {
        "register.name": bool(reg.get("name")),
        "register.anchor resolves": resolves(root, reg.get("anchor")),
        "mark": bool(ident.get("mark") or (uni.get("brand") or {}).get("mark") or ident.get("register")),
        "voice rules": bool(ident.get("voice")),
        "stylePack resolves": resolves(root, reg.get("stylePack")) or resolves(root, (reg.get("stylePack") or "") + "/pack.json"),
    }
    got = sum(1 for v in checks.values() if v)
    scores["identity"] = round(15 * got / len(checks))
    for name, ok in checks.items():
        if not ok:
            issues.append((3, "identity", f"identity is missing {name}", "start-new-story-universe / edit universe.json"))

    # 3) ENTITIES (reference matrices) ---------------------------------------
    renderable = [e for e in (jload(f) for f in ent_files) if e and e.get("kind") in
                  ("character", "setting", "visual-metaphor", "motif", "prop")]
    if not renderable:
        scores["entities"] = 0
        issues.append((25, "entities", "no renderable entities in canon", "add-character / add-setting / add-visual-metaphor"))
    else:
        fracs = []
        for e in renderable:
            frac, gaps = entity_completeness(root, e)
            fracs.append(frac)
            if frac < 1.0:
                skill = {"character": "add-character", "setting": "add-setting",
                         "visual-metaphor": "add-visual-metaphor", "motif": "add-motif",
                         "prop": "add-prop"}.get(e["kind"], "shoot-references")
                issues.append((round(25 / len(renderable) * (1 - frac)) + 1, "entities",
                               f"{e['id']} ({e['kind']}) matrix {int(frac*100)}% filled: {gaps}",
                               "shoot-references" if frac > 0 else skill))
        scores["entities"] = round(25 * sum(fracs) / len(fracs))

    # 4) SETTING SIZE (v0.9) --------------------------------------------------
    settings = [e for e in renderable if e.get("kind") in ("setting", "visual-metaphor")]
    if not settings:
        scores["setting_size"] = 10  # nothing to prove
    else:
        ok = 0
        for e in settings:
            c = e.get("contract", {})
            has_plate = resolves(root, c.get("scalePlate"))
            has_desc = bool((c.get("scale") or "").strip())
            if has_plate and has_desc: ok += 1
            else:
                miss = []
                if not has_plate: miss.append("scalePlate")
                if not has_desc: miss.append("scale descriptor")
                issues.append((round(10 / len(settings)) + 1, "setting_size",
                               f"{e['id']} cannot prove its size (missing {', '.join(miss)})", "add-setting"))
        scores["setting_size"] = round(10 * ok / len(settings))

    # 5) PROVENANCE -----------------------------------------------------------
    # A style-pack / lookbook ref is a COPY into a pack whose provenance lives in the
    # pack manifest (pack.json / lookbook.json), not a per-image .recipe.json. Counting
    # those as "un-provenanced" is a false positive, so they are excluded here (they are
    # provenanced at the pack level). Every other reference image is a primary render and
    # must carry its own recipe.
    ref = root / "reference"
    def _pack_managed(p):
        parts = p.parts
        return ("style" in parts or "lookbook" in parts) and "refs" in parts
    pngs = [p for p in ref.rglob("*.png") if not _pack_managed(p)] if ref.exists() else []
    if not pngs:
        scores["provenance"] = 10
    else:
        with_recipe = sum(1 for p in pngs if (p.parent / (p.name + ".recipe.json")).exists())
        scores["provenance"] = round(10 * with_recipe / len(pngs))
        if with_recipe < len(pngs):
            issues.append((round(10 * (len(pngs) - with_recipe) / len(pngs)) + 1, "provenance",
                           f"{len(pngs)-with_recipe}/{len(pngs)} images have no .recipe.json",
                           "on-brand-image (regenerate via the adapter)"))

    # 6) CRAFT-CANON ----------------------------------------------------------
    craft = root / "canon" / "craft"
    n_craft = len(list(craft.glob("*.json"))) if craft.exists() else 0
    scores["craft_canon"] = 10 if n_craft >= 2 else (6 if n_craft == 1 else 0)
    if n_craft == 0:
        issues.append((10, "craft_canon", "no craft-canon: the universe's invariants/rules aren't encoded",
                       "create-lookbook (+ a register-rule) / add a spine/genre record"))

    # 7) STORIES --------------------------------------------------------------
    sdir = root / "stories"
    stories = [jload(f) for f in sdir.glob("*.json")] if sdir.exists() else []
    stories = [s for s in stories if s]
    full = sum(1 for s in stories if s.get("status") == "full")
    if not stories:
        scores["stories"] = 0
        issues.append((10, "stories", "no stories composed over the canon", "add-story"))
    else:
        scores["stories"] = 10 if full else 6
        if not full:
            issues.append((4, "stories", f"{len(stories)} story stub(s), none promoted to full", "add-story"))

        # A FULL story with no canon/properties record is INVISIBLE to every future
        # casting sweep, because the property registry is what a sweep reads to learn
        # what already exists. Found on a universe whose own reference book, the one
        # every later book was built from, had no record and therefore no CANON.md row.
        pdir = root / "canon" / "properties"
        have = {p.stem for p in pdir.glob("*.json")} if pdir.exists() else set()
        unregistered = sorted(s["id"] for s in stories
                              if s.get("status") == "full" and s.get("id") and s["id"] not in have)
        if unregistered:
            scores["stories"] = max(0, scores["stories"] - min(4, len(unregistered)))
            issues.append((min(8, 2 * len(unregistered)), "stories",
                           f"{len(unregistered)} full story/stories with NO canon/properties record, so they are "
                           f"invisible to casting sweeps: {', '.join(unregistered[:5])}",
                           "write canon/properties/<id>.json, then `abu build-canon`"))

    # 8) SELF-CONTAINED -------------------------------------------------------
    asset_root = uni.get("assetRoot", ".")
    scores["self_contained"] = 5 if asset_root == "." else 0
    if asset_root != ".":
        issues.append((5, "self_contained", f"assetRoot is '{asset_root}' (should be '.'): refs may point outside the repo",
                       "consolidate assets in-repo"))

    total = sum(scores.values())
    return uni, scores, total, sorted(issues, key=lambda x: -x[0])

def entity_completeness(root, e):
    """Return (fraction 0..1 of the entity's matrix that is filled+resolving, gaps-summary)."""
    kind = e["kind"]
    slots = []  # (name, ok)
    if kind in ("character", "motif", "prop"):
        sheets = (e.get("structured") or {}).get("sheets") or {}
        for name, val in sheets.items():
            path = val if isinstance(val, str) else (val or {}).get("path") if isinstance(val, dict) else None
            slots.append((name, resolves(root, path)))
        if not sheets:
            slots.append(("sheets", False))
    else:  # setting / visual-metaphor
        c = e.get("contract") or {}
        for k in ("turnaround", "blueprint", "scalePlate"):
            slots.append((k, resolves(root, c.get(k))))
        plates = c.get("emptyPlates") or []
        slots.append(("emptyPlates", bool(plates) and all(resolves(root, p) for p in plates)))
        for k in ("map", "blocking", "dressing", "scale"):
            slots.append((k, bool((c.get(k) or "").strip())))
    got = sum(1 for _, ok in slots if ok)
    frac = got / len(slots) if slots else 0.0
    gaps = ", ".join(n for n, ok in slots if not ok)[:80] or "complete"
    return frac, gaps

def letter(total):
    return ("A" if total >= 90 else "B" if total >= 80 else "C" if total >= 70
            else "D" if total >= 60 else "F")

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    as_json = "--json" in sys.argv
    if not args:
        sys.exit("usage: grade.py <universe-dir> [--json]")
    udir = args[0]
    uni, scores, total, issues = grade_universe(udir)

    if as_json:
        print(json.dumps({
            "universe": uni.get("name") or os.path.basename(os.path.abspath(udir)),
            "grade": letter(total), "score": total,
            "dimensions": {k: {"score": scores[k], "max": m, "label": lbl} for k, lbl, m in RUBRIC},
            "issues": [{"impact": i, "dimension": d, "what": w, "fix": s} for i, d, w, s in issues],
        }, indent=2))
        return

    name = uni.get("name") or os.path.basename(os.path.abspath(udir))
    print(f"\n  UNIVERSE DOCTOR — {name}")
    print(f"  {'='*54}")
    print(f"  OVERALL: {letter(total)}   ({total}/100)\n")
    for k, lbl, m in RUBRIC:
        s = scores[k]; bar = "#" * round(10 * s / m) + "." * (10 - round(10 * s / m))
        print(f"    [{bar}] {s:>2}/{m:<2}  {lbl}")
    if issues:
        print(f"\n  PUNCH-LIST (highest impact first):")
        for i, (impact, dim, what, fix) in enumerate(issues, 1):
            print(f"    {i}. (+{impact}) {what}")
            print(f"          -> reach for: {fix}")
    else:
        print("\n  No issues. This universe is complete and locked.")
    print()

if __name__ == "__main__":
    main()
