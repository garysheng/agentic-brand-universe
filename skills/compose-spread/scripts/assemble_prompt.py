#!/usr/bin/env python3
"""Assemble ONE spread's render job from canon (SPEC per-spread apply).

Deterministic: (universe, render-spec, spread-id) -> JSON with
  prompt   the full generation prompt (register-anchor register line first)
  refs     ordered reference image paths, ABSOLUTE, register anchor FIRST
  size     the model render size
  qa       the readback checklist, one line per in-frame invariant

The whole point: NOTHING load-bearing about a character or setting is retyped by
the author. Character identity — including which LOOK (default or a named
altLooks.<key>) — comes from canon/entities/<id>.json. The per-book render-spec
carries only per-spread COMPOSITION (cast + selected look + scene staging) plus
book-wide style/negatives. Because the character block, its refs, AND the
negatives are all computed from the SAME canon look, a per-book file can no
longer silently contradict a character's canon (the bug this skill exists to kill:
a global "everyone is clean-shaven" negative fighting a canon facial-hair alt-look).

Usage:
  assemble_prompt.py <universe> <render-spec.json> <spread-id>
"""
import argparse
import json
import re
import sys
from pathlib import Path


class Refuse(Exception):
    pass


# A guarded negative (e.g. "no facial hair") is satisfied only by an invariant
# that POSITIVELY declares the feature. Negatively-phrased invariants like
# "completely-clean-shaven-never-a-mustache" contain the feature word ("mustache")
# but must NOT count as declaring it — so an invariant carrying any of these
# negation markers can never satisfy a guard.
NEG_MARKER = re.compile(r"clean-shaven|beardless|\bno-|-no-|never|bare|without", re.I)

# Sheet keys that show the FACE. On an alt look these are dropped (the alt anchor
# photo IS the face+hair); BODY sheets (fullbody, pose) are kept for proportion.
FACE_SHEET_KEYS = {"face-3q", "face-neutral", "face", "expressions"}


def load(p: Path):
    with open(p) as f:
        return json.load(f)


def deslug(inv: str) -> str:
    # invariants are kebab slugs (they double as render-readback keys); render
    # them as plain words in the prompt while keeping the slug for QA.
    return inv.replace("-", " ")


# Real-person entities declare `photoStack` as a DIRECTORY of bare-face photos, by
# convention (see any realPerson entity). A directory is not a reference the image model
# can accept, so it must be expanded to the actual image files here. Left unexpanded, the
# generator crashed with IsADirectoryError on EVERY real-person spread, which is every
# Nation of Fire book about a real friend. Found 2026-07-23 rendering the Russ book
# through the real pipeline (the reason to use the pipeline and not a hand-rolled script).
_IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp")

def resolve_ref(uroot: Path, p: str) -> list[str]:
    """Resolve a ref path to a LIST of on-disk image files. A path may be absolute,
    universe-relative, or relative to the universe's PARENT (cross-repo anchors live
    beside the universe). A DIRECTORY expands to the image files directly inside it,
    sorted, so a realPerson photoStack directory becomes its photos."""
    cand = Path(p)
    tries = [cand] if cand.is_absolute() else [uroot / p, uroot.parent / p, cand]
    for t in tries:
        if t.exists():
            if t.is_dir():
                imgs = sorted(str(f.resolve()) for f in t.iterdir()
                              if f.suffix.lower() in _IMG_EXTS)
                if not imgs:
                    raise Refuse(f"ref directory has no images: {p}")
                return imgs
            return [str(t.resolve())]
    raise Refuse(f"ref does not resolve on disk: {p}")


def resolve_render_block(ent: dict, pose: str | None, look: str | None = None):
    """Return (extra_sheet_keys, prose) from an entity's `structured.render`.

    Canon may carry PRESCRIBED PROMPT-CRAFT that a deslugged invariant list cannot
    express: an invariant is a short kebab QA key ("north-star-cross-pendant-front"),
    while the render block holds the sentence that actually steers the model ("a
    faceted dimensional four-point STAR ... NOT a Latin cross, NOT a crucifix").
    Ignoring it meant a universe could write the fix into canon and never have it
    reach a single prompt — which is how signature wardrobe (jacket patches) and a
    star-vs-crucifix pendant silently regressed across a whole batch.

    `render.always` applies to every pose. `render.poses.<pose>` may add a `bake`
    sentence and its own `sheets` list. Pose defaults to "front" when the entity
    defines one, because front-facing is the common case and the case canon warns
    about; a descriptor sets `pose` explicitly for anything else (e.g. "back").
    """
    st = ent.get("structured") or {}
    r = st.get("render") or {}
    # An alt look may REPLACE the render block wholesale. dropSheets already stops
    # a contradicted base SHEET reaching the model; this stops the contradicted
    # base PROSE. Without it, jerry-man's `render.always` kept asserting "his gold
    # NORTH STAR pendant" and "do NOT change his age" on a college-era look whose
    # invariants say the neck is bare and he is twenty, and the prose won: the
    # render came back with a necklace on a man who does not own one yet.
    if look:
        al = (st.get("altLooks") or {}).get(look) or {}
        if "render" in al:
            r = al["render"] or {}
    if not r:
        return [], None
    parts = []
    if r.get("always"):
        parts.append(r["always"])
    sheets: list[str] = []
    poses = r.get("poses") or {}
    if poses:
        key = pose or ("front" if "front" in poses else None)
        if key is not None:
            if key not in poses:
                raise Refuse(f"{ent['id']} has no render pose '{key}'")
            p = poses[key]
            if p.get("bake"):
                parts.append(p["bake"])
            sheets = list(p.get("sheets") or [])
    return sheets, (" ".join(parts) if parts else None)


def resolve_character(ent: dict, look: str | None):
    """Return (ref_paths, invariants) for a character in the selected look.

    Default look: requiredForRender sheets + up to two real photos.
    Alt look: the alt anchor photo (+ any alt sheets), and invariants with the
    superseded base invariants removed and the alt invariants added. The default
    clean-shaven sheets are NOT passed for an alt look, so they cannot fight it.
    """
    st = ent.get("structured", {})
    sheets = st.get("sheets", {})
    base_inv = list(st.get("invariants", []))
    refs: list[str] = []

    if look:
        al = (st.get("altLooks") or {}).get(look)
        if al is None:
            raise Refuse(f"{ent['id']} has no altLook '{look}'")
        if al.get("anchorPhoto"):
            refs.append(al["anchorPhoto"])
        for v in (al.get("sheets") or {}).values():
            if v:
                refs.append(v)
        # keep the base BODY sheets (pose/proportion/wardrobe); drop the base FACE
        # sheets, which show the default look and would fight the alt anchor photo.
        # `dropSheets` additionally drops base sheets the alt look CONTRADICTS.
        # Guarded negatives already stop a blanket negative fighting a canon look;
        # nothing did the same for REFS, so a look whose invariant said "neck
        # completely bare" still had the adult PENDANT sheet passed to the model,
        # and a reference image outranks a word. Caught adding jerry-man's age eras.
        dropped = set(al.get("dropSheets") or [])
        for key in st.get("requiredForRender", []):
            if key in FACE_SHEET_KEYS or key in dropped:
                continue
            p = sheets.get(key)
            if p and p not in refs:
                refs.append(p)
        supers = set(al.get("supersedes", []))
        inv = [i for i in base_inv if i not in supers] + list(al.get("invariants", []))
    else:
        for key in st.get("requiredForRender", []):
            p = sheets.get(key)
            if not p:
                raise Refuse(f"{ent['id']}.{key} is required but unlocked")
            refs.append(p)
        rp = ent.get("realPerson") or {}
        refs += list(rp.get("photoStack") or [])[:2]
        inv = base_inv
    return refs, inv


def resolve_setting(ent: dict, plate: str | None):
    """Return (ref_paths, block). Plate files follow reference/<id>/<plate>.png;
    the description comes from the setting's contract.dressing."""
    refs: list[str] = []
    if plate:
        refs.append(f"reference/{ent['id']}/{plate}.png")
    con = ent.get("contract", {})
    block = None
    if con.get("dressing"):
        block = f"{ent['id']} exactly as its reference plate: {con['dressing']}"
    return refs, block


def build(uroot: Path, spec: dict, spread_id: str) -> dict:
    uni = load(uroot / "universe.json")
    ident = uni.get("identity", {})
    reg = ident.get("register", {})

    # Anchor: the book may override identity.register.anchor when that anchor is
    # unsuitable (e.g. it points at a photograph, a painterly universe's own
    # rejectedPole). The override is DATA in the render-spec, with a reason.
    anchor = spec.get("anchorRef") or reg.get("anchor")
    if not anchor:
        raise Refuse("no anchor: identity.register.anchor is null and render-spec has no anchorRef")

    sp = next((s for s in spec.get("spreads", []) if s["id"] == spread_id), None)
    if sp is None:
        raise Refuse(f"spread '{spread_id}' not in render-spec")

    refs: list[str] = [anchor]
    ent_blocks: list[str] = []
    qa: list[str] = []
    char_invsets: dict[str, list[str]] = {}

    def add_refs(paths):
        for p in paths:
            if p not in refs:
                refs.append(p)

    # A spread's location can be given as a top-level {setting, plate} or as a
    # cast member; handle both, characters and settings alike, from canon.
    entries = list(sp.get("cast", []))
    if sp.get("setting"):
        entries.append({"id": sp["setting"], "plate": sp.get("plate")})

    for c in entries:
        ent = load(uroot / "canon" / "entities" / f"{c['id']}.json")
        kind = ent.get("kind")
        if kind in ("setting", "visual-metaphor"):
            r, block = resolve_setting(ent, c.get("plate"))
            add_refs(r)
            if block:
                ent_blocks.append(block)
            continue
        r, inv = resolve_character(ent, c.get("look"))
        add_refs(r)
        # Canon's prescribed prompt-craft (structured.render) is emitted ALONGSIDE
        # the invariant list: the invariants remain the QA keys, the render block
        # is the wording that actually steers the model. Its pose may also require
        # sheets beyond requiredForRender (e.g. the jacket-back sheet on a back pose).
        pose_sheets, render_prose = resolve_render_block(ent, c.get("pose"), c.get("look"))
        sheets_map = (ent.get("structured") or {}).get("sheets") or {}
        # a pose's extra sheets obey the selected look's dropSheets too, or the
        # render block quietly reintroduces the very sheet the look contradicts.
        look_dropped = set(
            (((ent.get("structured") or {}).get("altLooks") or {}).get(c.get("look")) or {}).get("dropSheets")
            or []
        )
        add_refs([sheets_map[k] for k in pose_sheets
                  if sheets_map.get(k) and k not in look_dropped])
        ent_blocks.append(
            f"{c['id']} rendered exactly per the supplied reference images: "
            + "; ".join(deslug(i) for i in inv)
            + "."
            + (f" {render_prose}" if render_prose else "")
        )
        qa += [f"{c['id']}: {i}" for i in inv]
        char_invsets[c["id"]] = inv

    # Auto-disambiguation: when two or more characters share the frame, name what
    # makes each one distinct (the invariants NOT common to all of them), so the
    # model does not blur two faces/hairstyles together. Fully derived.
    disambig = None
    if len(char_invsets) >= 2:
        sets = [set(v) for v in char_invsets.values()]
        common = set.intersection(*sets)
        parts = []
        for cid, inv in char_invsets.items():
            uniq = [i for i in inv if i not in common]
            if uniq:
                parts.append(f"{cid} is the one with " + ", ".join(deslug(i) for i in uniq))
        if parts:
            disambig = (
                "TELL THEM APART, keep every face and hairstyle distinct: "
                + "; ".join(parts)
                + "."
            )

    # Negatives: universe rejectedPoles + book-wide unconditional negatives, then
    # GUARDED negatives — a blanket negative (e.g. "no facial hair") is emitted
    # ONLY when no in-frame character's selected look positively satisfies it.
    negs = list(reg.get("rejectedPoles", []))
    negs += list(spec.get("negatives", []))
    all_inv = set().union(*[set(v) for v in char_invsets.values()]) if char_invsets else set()
    for g in spec.get("guardedNegatives", []):
        pat = g.get("satisfiedByInvariantMatching")
        satisfied = bool(pat) and any(
            re.search(pat, i) and not NEG_MARKER.search(i) for i in all_inv
        )
        if not satisfied:
            negs.append(g["text"])

    # Resolve every ref to an absolute on-disk path (register anchor stays first).
    resolved: list[str] = []
    for p in refs:
        for r in resolve_ref(uroot, p):
            if r not in resolved:
                resolved.append(r)

    style = spec.get("style", "")
    scene = sp.get("scene", "")
    prompt = " ".join(
        x
        for x in [
            f"Picture-book spread painted in the {reg.get('name', 'locked')} register of the FIRST reference image.",
            style,
            ("SCENE: " + scene) if scene else "",
            *ent_blocks,
            disambig or "",
            sp.get("extra", ""),  # authored per-spread instruction (e.g. bake a title glyph); DATA, not improvisation
            ("NEGATIVES: " + ", ".join(negs) + ".") if negs else "",
        ]
        if x
    )

    return {"prompt": prompt, "refs": resolved, "size": spec.get("size", "1536x1024"), "qa": qa}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("universe")
    ap.add_argument("render_spec")
    ap.add_argument("spread")
    args = ap.parse_args()
    try:
        out = build(Path(args.universe), load(Path(args.render_spec)), args.spread)
    except Refuse as e:
        print(f"REFUSE: {e}", file=sys.stderr)
        return 2
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
