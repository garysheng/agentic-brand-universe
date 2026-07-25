#!/usr/bin/env python3
"""
Brand universe linter.

Static checks over a universe and everything it declares: packs, projections,
goldens, emitters, quirks. No generation, no API, no cost. Catches the classes of
failure that were previously only discovered by running a composition, sometimes an
hour into one.

    python3 lint.py <universe-dir>

Exit 0 clean, 1 warnings only, 2 errors.
"""
import hashlib, json, pathlib, re, sys

E, W = [], []
def err(code, msg): E.append((code, msg))
def warn(code, msg): W.append((code, msg))

def _sha16(path):
    """First 16 hex of a file's sha256, or None if it does not resolve. Must match the
    engine's `_digest` so a golden's recorded input hashes compare equal here."""
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except Exception:
        return None

def jload(p):
    try: return json.loads(pathlib.Path(p).read_text())
    except Exception as ex: err("PARSE", f"{p}: {ex}"); return None

def lint(root):
    root = pathlib.Path(root).resolve()
    SKILLS = pathlib.Path(__file__).resolve().parents[2]
    EMITTERS = {"brand-card": SKILLS/"brand-card/scripts/card.py",
                "explanatory-plate": SKILLS/"explanatory-plate/scripts/plate.py"}

    u = jload(root/"universe.json")
    if not u: return

    # ---- story types are DATA, not prose (craft-canon membership)
    #
    # A story declares its `spine` (arc invariant) and optional `genre` (book type). The SPEC
    # (§13) says these are craft-canon records (`canon/craft/*.json`, kinds spine|genre), so
    # "where are this universe's story types?" is answerable by listing them. But nothing tied
    # a story's declared value back to that registry, so a typo ("expectant-biograhpy"), a
    # near-duplicate ("teaching-testimony" vs "testimony-teaching"), or free-text prose in the
    # genre field ("testimony (Jerry-voiced ...)") passed silently. This check makes an
    # unregistered spine/genre a loud finding: register it as a craft record (one JSON file, so
    # the mode becomes discoverable data) or fix the typo. A WARNING, not an error: a universe
    # mid-normalization still validates and composes, it just gets told what to canonize.
    craft_dir = root/"canon"/"craft"
    reg_spine, reg_genre = set(), set()
    if craft_dir.exists():
        for cf in craft_dir.glob("*.json"):
            c = jload(cf) or {}
            if c.get("kind") == "spine": reg_spine.add(c.get("id"))
            elif c.get("kind") == "genre": reg_genre.add(c.get("id"))
    stories_dir = root/"stories"
    if stories_dir.exists() and (reg_spine or reg_genre):
        for sf in sorted(stories_dir.glob("*.json")):
            s = jload(sf)
            if not s: continue
            sid = s.get("id", sf.stem)
            spine = s.get("spine")
            if spine and spine not in reg_spine:
                warn("STORY-SPINE-UNREGISTERED", f"{sid}: spine '{spine}' is not a registered "
                     f"craft record. Register it (canon/craft/<id>.json kind 'spine') or fix the "
                     f"value; known: {sorted(x for x in reg_spine if x)}")
            genre = s.get("genre")
            if genre and genre not in reg_genre:
                warn("STORY-GENRE-UNREGISTERED", f"{sid}: genre '{genre}' is not a registered "
                     f"craft record. Register it (canon/craft/<id>.json kind 'genre') or fix the "
                     f"value; known: {sorted(x for x in reg_genre if x)}")

    # ---- the spec pin
    #
    # A universe declares the spec version it conforms to. Nothing checked that the
    # declaration was true, and on 2026-07-24 three surfaces gave three answers:
    # SPEC.md said v0.6, the engine constant said 0.4.1, and a universe pinned 0.5.
    # Every one of them was internally consistent, which is exactly why nobody caught
    # it: consistency is not truth. A pin that nothing verifies is a comment.
    pin = (u.get("spec") or {}).get("version")
    engine = None
    initf = SKILLS.parent/"engine"/"agenticstory"/"__init__.py"
    if initf.exists():
        m = re.search(r'SPEC_VERSION\s*=\s*"([^"]+)"', initf.read_text())
        engine = m.group(1) if m else None
    if not pin:
        err("NO-SPEC-PIN", "universe.json declares no spec.version; it conforms to nothing in "
                           "particular, and an unpinned universe cannot detect drift")
    elif engine and pin != engine:
        warn("SPEC-PIN-BEHIND", f"universe pins spec v{pin}; this engine implements v{engine}. "
                                f"Bump deliberately and re-lint, or pin the engine back. Do not "
                                f"leave them disagreeing: the recipes this engine writes will "
                                f"record a version the universe never conformed to.")

    reg = u.get("identity", {}).get("register", {})
    if not reg.get("anchor"):
        err("REGISTER-UNLOCKED", "identity.register.anchor is null; generation should refuse")
    elif not (root/reg["anchor"]).exists():
        err("REGISTER-MISSING", f"register anchor does not resolve: {reg['anchor']}")

    # ---- style packs
    packs = {}
    for pj in (root/"reference"/"style").rglob("pack.json"):
        p = jload(pj)
        if not p: continue
        d = pj.parent; packs[str(d.relative_to(root))] = p
        if not p.get("anchor"): err("PACK-NO-ANCHOR", f"{pj}: no anchor")
        elif not (d/p["anchor"]).exists(): err("PACK-ANCHOR-MISSING", f"{pj}: anchor {p['anchor']} missing")
        for r in p.get("refs", []):
            if not (d/r).exists(): err("PACK-REF-MISSING", f"{pj}: ref {r} missing")
        if not p.get("gate"): err("PACK-NO-GATE", f"{pj}: no gate; a pack without one is a mood board")
        if not p.get("styleLine"): err("PACK-NO-STYLELINE", f"{pj}: no styleLine")
        n = len(p.get("refs", []))
        if n < 3: warn("PACK-THIN", f"{pj}: {n} ref(s); the spec expects 3 to 8")

    # ---- goldens declared by entities
    #
    # A golden is Gary's approved answer of record: the human-blessed output the whole
    # divergence loop measures the generator against. But an approval that recorded only
    # a path cannot answer what it was approved AGAINST, so the golden library was a
    # taste corpus nothing could audit. `lock-shot --recipe` now freezes provenance as
    # a `<golden>.recipe.json` sidecar; these two checks make that provenance load-bearing.
    for ej in (root/"canon"/"entities").glob("*.json"):
        e = jload(ej)
        if not e or e.get("kind") not in ("character","prop","motif","visual-metaphor"): continue
        st = e.get("structured") or {}
        sheets = st.get("sheets") or {}

        # Render-correctness: every REQUIRED sheet resolves. Scoped to requiredForRender
        # because that is what the render gate depends on.
        for name in st.get("requiredForRender", []):
            pth = sheets.get(name)
            if not pth: err("GOLDEN-UNDECLARED", f"{ej.name}: requires '{name}' but no sheet path")
            elif not (root/pth).exists(): err("GOLDEN-MISSING", f"{ej.name}: {name} -> {pth} missing")

        # Auditability: every LOCKED sheet carries provenance, required or not. A golden
        # is Gary's approved answer of record regardless of whether the render gate needs
        # it, so every approved asset must be able to enter a divergence check.
        for name, pth in sheets.items():
            if not pth or not (root/pth).exists(): continue    # unlocked/missing: other checks own it
            sidecar = (root/pth).with_name((root/pth).name + ".recipe.json")
            if not sidecar.exists():
                warn("GOLDEN-NO-RECIPE", f"{ej.name}: golden '{name}' ({pth}) has no provenance "
                     f"sidecar; it is un-auditable and cannot be part of a divergence check. "
                     f"Re-lock it with `lock-shot --recipe`.")
                continue
            rec = jload(sidecar)
            if not rec: continue
            # An input that has changed bytes since approval means this golden was
            # blessed against something that no longer exists. The approval may not hold,
            # and no human is looking. This is the free half of the divergence loop:
            # detected statically, at zero cost, over the whole approved corpus.
            for inp in rec.get("inputs", []):
                # A recipe's inputs may be bare path strings (older lock-shot) or
                # {path,digest} dicts (with provenance). Only the dict form carries a
                # digest to compare; a bare string has nothing to check, and calling
                # .get on it used to crash the whole linter mid-run.
                if not isinstance(inp, dict): continue
                ip, want = inp.get("path"), inp.get("digest")
                if want is None: continue
                ap = ip if pathlib.Path(ip).is_absolute() else str(root/ip)
                now = _sha16(ap)
                if now is None:
                    warn("GOLDEN-INPUT-GONE", f"{ej.name}: golden '{name}' was approved against "
                         f"input '{ip}', which no longer resolves.")
                elif now != want:
                    warn("GOLDEN-STALE", f"{ej.name}: golden '{name}' was approved when input '{ip}' "
                         f"had bytes {want}; it is now {now}. The approval was of a different input; "
                         f"re-judge and re-lock, or confirm the golden still holds.")

    # ---- provider quirk registry
    regf = SKILLS.parent/"registry"/"providers.json"
    providers = jload(regf).get("providers", {}) if regf.exists() else {}
    if not providers: warn("NO-QUIRK-REGISTRY", "no provider registry; quirks cannot be inherited")

    # ---- projections
    pdir = root/"projections"
    if not pdir.exists():
        warn("NO-PROJECTIONS", "universe declares no projections; it can only make storybooks by hand")
        return
    def resolve(pj, seen=()):
        """Merge the `extends` chain before checking anything, exactly as the composer
        does. Checking the child's RAW fields makes every fork that INHERITS a
        generator, an emitter, or a surface false-fail: the field is absent from the
        file and present at run time. The one prior fork happened to override every
        field it used, which is why this went unseen until a fork that inherits.
        Returns (merged, error_or_None)."""
        p = jload(pj)
        if not p: return None, None
        ref = p.get("extends")
        if not ref: return p, None
        name = ref.split("@")[0]
        if name in seen:
            return p, f"{p.get('id', pj.stem)}: extends cycle through '{name}'"
        base_f = pdir/(name + ".json")
        if not base_f.exists():
            return p, f"{p.get('id', pj.stem)}: extends {ref} not found"
        base, e = resolve(base_f, seen + (name,))
        if base is None: return p, e
        merged = {**base, **{k: v for k, v in p.items() if v is not None}}
        return merged, e

    for pj in sorted(pdir.glob("*.json")):
        raw = jload(pj)
        if not raw: continue
        p, chain_err = resolve(pj)
        pid = raw.get("id", pj.stem)
        if chain_err:
            err("EXTENDS-UNRESOLVED", chain_err)
            continue          # every downstream check would be noise against a broken chain
        gens = {g.get("for"): g for g in p.get("generators", [])}
        for s in p.get("slots", []):
            sid = s.get("id")
            if s.get("type") == "deterministic":
                em = (s.get("emitter") or "").split(":")[-1]
                if not em:
                    err("SLOT-NO-EMITTER", f"{pid}.{sid}: deterministic with no emitter; nothing can produce it")
                elif em not in EMITTERS:
                    err("EMITTER-UNKNOWN", f"{pid}.{sid}: unknown emitter '{em}'")
                elif not EMITTERS[em].exists():
                    err("EMITTER-MISSING", f"{pid}.{sid}: emitter script missing at {EMITTERS[em]}")
            elif s.get("type") == "generated":
                g = gens.get(sid)
                if not g:
                    err("SLOT-NO-GENERATOR", f"{pid}.{sid}: generated but no generator declares for='{sid}'")
                    continue
                # Aspect ratio is a VISUAL property. Demanding one from a text or
                # audio slot is a false positive, and false positives are how a
                # linter teaches people to ignore it. Found by the first
                # text-dominant projection; every prior one was image-dominant.
                if g.get("capability") not in ("image", "video"):
                    continue
                geo, asp = s.get("geometry"), g.get("producibleAspects")
                if geo and asp:
                    want = geo["w"]/geo["h"]; tol = g.get("tolerance", 0.25)
                    if not any(abs(want-a)/want <= tol for a in asp):
                        err("SURFACE-INFEASIBLE",
                            f"{pid}.{sid}: needs aspect {want:.3f}, provider makes {asp}. Undeliverable.")
                elif not asp:
                    warn("NO-PRODUCIBLE-ASPECTS", f"{pid}.{sid}: no producibleAspects; feasibility uncheckable")
                pin = g.get("pin")
                if pin and pin not in providers:
                    warn("PIN-UNKNOWN-PROVIDER", f"{pid}.{sid}: pinned to '{pin}', absent from the quirk registry")
        inv = p.get("invariants", {})
        for scope in ("perSlot","crossSlot"):
            for i in inv.get(scope, []):
                if i.get("check") not in ("computed","judged"):
                    err("INVARIANT-UNTYPED", f"{pid}: invariant '{i.get('id')}' is not computed or judged")
        if not inv.get("perSlot") and not inv.get("crossSlot"):
            warn("NO-INVARIANTS", f"{pid}: declares no invariants; nothing can fail, so nothing is checked")

        # A contract can be internally coherent and, in practice, undeliverable. Feasibility
        # already catches that for GEOMETRY: an aspect no generator can produce. It could not
        # catch it for BEHAVIOUR: an invariant the pinned provider is known to break.
        #
        # Earned 2026-07-23. A projection declared "hands: four fingers plus a thumb" and
        # pinned a provider whose registry entry says it loses a digit on stylized hands.
        # Six artifacts went to independent judges and six failed on that one item, twice
        # each, prompt counter included. Nothing was wrong with the projection in isolation
        # and nothing was wrong with the registry in isolation; the contradiction lived
        # BETWEEN them, which is the same shape as the infeasible-surface class.
        #
        # This is a WARNING, not an error. A brand is allowed to demand something hard, and a
        # known quirk is a re-roll cost rather than an impossibility. What it must not be is a
        # surprise discovered after paying for generation.
        quirk_terms = {}
        for g in p.get("generators", []):
            prov = g.get("pin")
            if not prov: continue
            for q in providers.get(prov, {}).get("quirks", []):
                for w in re.findall(r"[a-z]{4,}", q["id"].lower()):
                    quirk_terms.setdefault(w, []).append((prov, q["id"]))
        for scope in ("perSlot", "crossSlot"):
            for i in inv.get(scope, []):
                words = set(re.findall(r"[a-z]{4,}", str(i.get("id", "")).lower()))
                hits = {(prov, qid) for w in words for prov, qid in quirk_terms.get(w, [])}
                for prov, qid in sorted(hits):
                    if qid == i.get("id"): continue          # the quirk itself, already handled
                    warn("INVARIANT-VS-QUIRK",
                         f"{pid}: invariant '{i.get('id')}' overlaps a known quirk of its pinned "
                         f"provider {prov} ('{qid}'). Expect re-rolls; budget for them or relax "
                         f"the rule, but do not discover this after paying for generation.")

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    lint(root)
    for c,m in E: print(f"  ERROR  [{c}] {m}")
    for c,m in W: print(f"  warn   [{c}] {m}")
    print(f"\n{len(E)} error(s), {len(W)} warning(s)")
    return 2 if E else (1 if W else 0)

if __name__ == "__main__":
    sys.exit(main())
