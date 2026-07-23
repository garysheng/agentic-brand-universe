#!/usr/bin/env python3
"""
The composer (SPEC 4.10): plan -> compile -> generate -> gate -> repair, per slot.

Implements the parts the spec asserted and nothing ran:
  * `extends` resolution, which previously nothing merged
  * feasibility of `surface` against `generators.producibleAspects`, checked at PLAN
    time, because discovering it an hour in is the failure it exists to prevent
  * DURABLE per-slot state, so a restart resumes rather than redoing
  * park-the-slot-and-continue, so one defect costs one slot and not the artifact
"""
import json, os, pathlib, subprocess, sys, hashlib

def load_projection(root, ref):
    """Resolve a projection and its `extends` chain. Child overrides parent key-wise."""
    name = ref.split("@")[0]
    p = json.loads((pathlib.Path(root) / "projections" / f"{name}.json").read_text())
    if p.get("extends"):
        base = load_projection(root, p["extends"])
        merged = {**base, **{k: v for k, v in p.items() if v is not None}}
        merged["_extends_chain"] = base.get("_extends_chain", []) + [base["id"]]
        return merged
    p["_extends_chain"] = []
    return p

def feasibility(proj, comp):
    """A contract can be internally valid and physically undeliverable. Catch it here."""
    errs = []
    geo = {**proj["surface"].get("geometry", {}), **comp.get("surface", {})}
    gens = {g["for"]: g for g in proj.get("generators", [])}
    for slot in proj["slots"]:
        if slot["type"] != "generated":
            if not slot.get("emitter"):
                errs.append(f"slot '{slot['id']}': deterministic with no emitter, so nothing can produce it")
            continue
        g = gens.get(slot["id"])
        if not g: continue
        sg = slot.get("geometry")
        if not sg or not g.get("producibleAspects"): continue
        want = sg["w"] / sg["h"]
        tol = g.get("tolerance", 0.25)
        if not any(abs(want - a) / want <= tol for a in g["producibleAspects"]):
            errs.append(f"slot '{slot['id']}': needs aspect {want:.3f}; capability produces "
                        f"{g['producibleAspects']}. Surface is undeliverable, fix geometry not by cropping.")
    return errs

def plan(proj, comp):
    out = []
    for slot in proj["slots"]:
        rep = slot.get("repeat")
        n = comp.get("repeat", {}).get(slot["id"], 1) if rep else 1
        for i in range(n):
            out.append({"slot": slot["id"], "index": i, "type": slot["type"],
                        "emitter": slot.get("emitter")})
    return out

def state_path(work, sid, idx):
    return pathlib.Path(work) / "state" / f"{sid}-{idx}.json"

def run_slot(unit, proj, comp, work):
    """Execute ONE slot. Returns (status, detail). Never raises past the caller."""
    sid, idx = unit["slot"], unit["index"]
    spec = comp["slots"].get(sid)
    if spec is None:
        return "DEFECT", "no composition data for this slot"
    out = str(pathlib.Path(work) / f"{sid}-{idx}.png")
    if unit["type"] == "deterministic":
        emitter = (unit["emitter"] or "").split(":")[-1]
        payload = {**spec, "out": out}
        pf = pathlib.Path(work) / f"{sid}-{idx}.spec.json"
        pf.write_text(json.dumps(payload, indent=2))
        script = {"brand-card": "brand-card/scripts/card.py",
                  "explanatory-plate": "explanatory-plate/scripts/plate.py"}.get(emitter)
        if not script:
            return "DEFECT", f"unknown emitter '{emitter}'"
        r = subprocess.run([sys.executable, str(SKILLS / script), str(pf)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return "DEFECT", (r.stdout + r.stderr).strip().splitlines()[-1][:200]
        return "PASS", out
    return "SKIP", "generated slot: art supplied by the composition in this run"

SKILLS = pathlib.Path(__file__).resolve().parents[2]

def main():
    comp = json.load(open(sys.argv[1]))
    root = comp["universe"]
    work = comp.get("work", "/tmp/compose-" + comp["id"])
    (pathlib.Path(work) / "state").mkdir(parents=True, exist_ok=True)

    proj = load_projection(root, comp["projection"])
    print(f"projection {proj['id']}  extends chain: {proj['_extends_chain'] or 'none'}")

    errs = feasibility(proj, comp)
    if errs:
        print("PLAN-TIME REFUSAL, nothing generated:")
        for e in errs: print("  -", e)
        return 2

    units = plan(proj, comp)
    print(f"planned {len(units)} slot(s)")
    results = []
    for u in units:
        sp = state_path(work, u["slot"], u["index"])
        if sp.exists():
            prev = json.loads(sp.read_text())
            # Resume only what SUCCEEDED. Resuming a DEFECT would freeze the artifact
            # broken forever: the whole point of parking a slot is that you repair it
            # and re-run, paying only for that slot.
            if prev["status"] in ("PASS", "SKIP"):
                print(f"  {u['slot']}-{u['index']}: {prev['status']} (resumed, not recomputed)")
                results.append(prev); continue
            print(f"  {u['slot']}-{u['index']}: retrying previously DEFECT slot")
        status, detail = run_slot(u, proj, comp, work)
        rec = {"slot": u["slot"], "index": u["index"], "status": status, "detail": detail}
        sp.write_text(json.dumps(rec, indent=2))
        print(f"  {u['slot']}-{u['index']}: {status}  {detail if status!='PASS' else ''}")
        results.append(rec)                               # park and CONTINUE, never halt

    defects = [r for r in results if r["status"] == "DEFECT"]
    print(f"\n{len(results)-len(defects)}/{len(results)} slots passed")
    if defects:
        print("artifact emitted INCOMPLETE. Repair these slots and re-run; passing slots resume free:")
        for d in defects: print(f"  - {d['slot']}-{d['index']}: {d['detail']}")
    return 1 if defects else 0

if __name__ == "__main__":
    sys.exit(main())
