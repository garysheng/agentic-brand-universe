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
import json, pathlib, sys

E, W = [], []
def err(code, msg): E.append((code, msg))
def warn(code, msg): W.append((code, msg))

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
    for ej in (root/"canon"/"entities").glob("*.json"):
        e = jload(ej)
        if not e or e.get("kind") not in ("character","prop","motif","visual-metaphor"): continue
        sheets = (e.get("structured") or {}).get("sheets") or {}
        for name in (e.get("structured") or {}).get("requiredForRender", []):
            pth = sheets.get(name)
            if not pth: err("GOLDEN-UNDECLARED", f"{ej.name}: requires '{name}' but no sheet path")
            elif not (root/pth).exists(): err("GOLDEN-MISSING", f"{ej.name}: {name} -> {pth} missing")

    # ---- provider quirk registry
    regf = SKILLS.parent/"registry"/"providers.json"
    providers = jload(regf).get("providers", {}) if regf.exists() else {}
    if not providers: warn("NO-QUIRK-REGISTRY", "no provider registry; quirks cannot be inherited")

    # ---- projections
    pdir = root/"projections"
    if not pdir.exists():
        warn("NO-PROJECTIONS", "universe declares no projections; it can only make storybooks by hand")
        return
    for pj in sorted(pdir.glob("*.json")):
        p = jload(pj)
        if not p: continue
        pid = p.get("id", pj.stem)
        if p.get("extends"):
            base = pdir/(p["extends"].split("@")[0] + ".json")
            if not base.exists(): err("EXTENDS-UNRESOLVED", f"{pid}: extends {p['extends']} not found")
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

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    lint(root)
    for c,m in E: print(f"  ERROR  [{c}] {m}")
    for c,m in W: print(f"  warn   [{c}] {m}")
    print(f"\n{len(E)} error(s), {len(W)} warning(s)")
    return 2 if E else (1 if W else 0)

if __name__ == "__main__":
    sys.exit(main())
