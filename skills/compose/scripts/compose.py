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
import json, os, pathlib, re, subprocess, sys, hashlib

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
    errs += scene_contradictions(proj, comp)
    return errs

# Words a scene must not use, because the compiler is simultaneously appending
# "no <pole>" to the very same prompt. The model is then handed both instructions
# at once and picks one. Earned 2026-07-23: a beat described a grid "receding
# across the frame" for a projection whose pack rejects perspective outright; the
# compiled prompt said "receding" and "no perspective" in the same breath, and the
# render came back in one-point perspective. The judge caught it, having never seen
# the beat. The maker wrote the contradiction, which is exactly why the maker is
# not allowed to be the judge.
#
# This is a CHEAP LITERAL check and it says so: it catches a scene that NAMES a
# rejected pole, not one that merely implies it. "Receding" is not the word
# "perspective". Catching implication needs a model, and that check belongs to the
# gate, which already has it. The point of this one is that it costs nothing and
# runs before a single image is paid for.
# Words that do not NAME a rejected pole but reliably summon one. The literal check
# caught nothing on a six-plate run where three plates failed for exactly this reason:
# an "open" book and an "open" doorway are inherently volumetric, and a scene that said
# "glowing" and "dark" got a radial glow and a vignette on a pack that requires one flat
# ground colour. None of those words is "perspective" or "gradient", and all three
# produced one.
#
# Kept deliberately small and specific. A big fuzzy list would fire constantly and get
# switched off, which is worse than not having it.
IMPLIES = {
    "perspective": ["receding", "three-quarter", "angled", "tilted", "rotated",
                    "open book", "open door", "ajar", "swung", "depth", "vanishing"],
    "shading":     ["glowing", "glow", "lit", "shadow", "shadowed", "dim"],
    "gradients":   ["glowing", "glow", "fading", "faded", "dark", "darkness", "halo"],
}

# A scene that says "no glow" or "with no depth" is EXCLUDING the pole, not summoning
# it. Matching the bare word flagged every careful exclusion as a contradiction and
# refused the whole composition at plan time, which blocked a run entirely. A check
# that false-fires is worse than no check, and this one false-fired on the very
# repairs written to satisfy it.
NEGATORS = ("no", "not", "never", "without", "nothing", "none", "avoid", "zero")
ARTICLES = ("a", "an", "the")

def _negated(text, start):
    """Is the match at `start` governed by a negation?

    A fixed word window cannot decide this. "No object may be turned, angled, opened,
    or tilted" puts the negator EIGHT words back and plainly negates the whole list,
    while "no text anywhere, and a big glowing box" puts one four words back and does
    NOT negate the glow. Distance is the wrong signal.

    Scope is. Scan backwards and stop at an ARTICLE, because "a" or "the" starts a
    fresh noun phrase and ends the reach of any earlier negator. A negator found
    before an article governs the match; one found after it does not.
    """
    before = text[max(0, start - 200):start]
    words = re.findall(r"[a-z']+", before)
    for w in reversed(words[-12:]):
        if w in ARTICLES:
            return False                      # a new noun phrase began; negation ended
        if w in NEGATORS:
            return True
    return False

def scene_contradictions(proj, comp):
    errs = []
    b = comp.get("bind", {}) or {}
    ref = b.get("style-pack") if isinstance(b, dict) else None
    if not ref: return errs
    try:
        pack = load_pack(comp["universe"], ref)
    except Exception:
        return errs                                  # a missing pack is another check's job
    poles = [str(x).lower() for x in pack.get("rejectedPoles", [])]
    scenes = list(comp.get("beats", [])) + list(comp.get("plateScenes", []))
    for sl in (comp.get("slots", {}) or {}).values():
        if isinstance(sl, dict) and sl.get("scene"): scenes.append(sl["scene"])
    for i, sc in enumerate(scenes):
        low = str(sc).lower()
        for pole in poles:
            # single-word poles only; a phrase like "3D/CGI/Pixar" would false-fire
            if " " in pole or "/" in pole: continue
            m = re.search(r"\b" + re.escape(pole) + r"\b", low)
            if m and not _negated(low, m.start()):
                errs.append(f"scene {i} names '{pole}', which this style pack REJECTS. "
                            f"The compiled prompt would say '{pole}' and 'no {pole}' at once. "
                            f"Rewrite the scene; do not rely on the negative to win.")
            for word in IMPLIES.get(pole, []):
                mw = re.search(r"\b" + re.escape(word) + r"\b", low)
                if mw and not _negated(low, mw.start()):
                    errs.append(f"scene {i} says '{word}', which does not name '{pole}' but "
                                f"reliably produces it, and this pack REJECTS '{pole}'. "
                                f"Describe the shape flat instead.")
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

def root_of(comp):
    return comp["universe"]

def spec_state(work, sid, idx):
    f = state_path(work, sid, idx)
    if not f.exists(): return None
    try: return json.loads(f.read_text())
    except Exception: return None

def clear_verdict(work, sid, idx):
    f = pathlib.Path(work) / "verdicts" / f"{sid}-{idx}.json"
    if f.exists(): f.unlink()

def state_path(work, sid, idx):
    return pathlib.Path(work) / "state" / f"{sid}-{idx}.json"

def run_slot(unit, proj, comp, work):
    """Execute ONE slot. Returns (status, detail). NEVER raises.

    The contract is enforced here rather than relying on the caller to box it. A
    function that promises not to raise and relies on someone else's try/except is
    lying to every other caller, and this exact gap was found by a test asserting
    the promise directly.
    """
    try:
        r = _run_slot(unit, proj, comp, work)
        return r if len(r) == 3 else (r[0], r[1], 0)
    except Exception as ex:
        return "DEFECT", f"{type(ex).__name__}: {ex}", 0


def _run_slot(unit, proj, comp, work):
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
    # generated slot: compile -> generate -> judge -> repair, per SPEC 4.10
    if spec.get("art"):                                   # art supplied by the composition
        return "PASS", spec["art"]
    # A composition may bind ONE pack, or a pack PER SLOT. A book that weaves a
    # narrative register and a diagram register is one composition in two registers.
    b = comp.get("bind", {}).get("style-pack")
    pack_ref = b.get(sid, b.get("default")) if isinstance(b, dict) else b
    if not pack_ref:
        return "DEFECT", f"slot '{sid}' has no style-pack binding", 0
    pack = load_pack(comp["universe"], pack_ref)

    # Goldens are per-slot too. A register that REJECTS the cast must not be handed
    # the cast: passing Gary's master into a characterless plate is a contradiction
    # the compiler should refuse, not something the model has to resist.
    g = comp.get("goldens", {})
    goldens = (g.get(sid, g.get("default", [])) if isinstance(g, dict) else g)
    rejected = [r.lower() for r in pack.get("rejectedPoles", [])]
    if goldens and any(("character" in r) or ("storybook-register" in r) for r in rejected):
        return "DEFECT", (f"slot '{sid}' binds pack '{pack['id']}' which rejects characters, "
                          f"but was handed {len(goldens)} character golden(s). Registers disagree."), 0
    scene = spec.get("scene", "")
    if comp.get("beats") and sid in ("spread", "art") and idx < len(comp["beats"]):
        scene = comp["beats"][idx]                       # one beat per repeated slot
    if comp.get("plateScenes") and sid == "plate" and idx < len(comp["plateScenes"]):
        scene = comp["plateScenes"][idx]
    if not scene:
        return "DEFECT", "no scene for this slot", 0
    if comp.get("_lock") and goldens:                    # only where a character is actually bound
        scene = comp["_lock"] + " Scene: " + scene
    prompt, refs, qa = compile_slot(proj, comp, sid, scene, pack, goldens)
    size = spec.get("size", "1024x1024")
    max_rolls = proj.get("maxRolls", comp.get("maxRolls", 3))

    # The checklist a judge is held to comes from the CONTRACT: this projection's
    # judged invariants plus the resolved provider's quirk checks, which `qa` already
    # holds. It used to be read from a bound entity's invariant list instead, so a
    # projection with no cast had no checkable rules at all and `qa` was computed and
    # then discarded. Found by the first characterless BOOK; every earlier
    # characterless deliverable was a single plate with nothing to judge across.
    checklist = list(qa)
    if goldens and comp.get("invariantsFile"):
        try:
            raw = json.loads(pathlib.Path(root_of(comp)).joinpath(comp["invariantsFile"]).read_text()) \
                  if not os.path.isabs(comp["invariantsFile"]) else json.loads(open(comp["invariantsFile"]).read())
            checklist += (raw if isinstance(raw, list)
                          else raw.get("structured", {}).get("invariants", []))
        except Exception as ex:
            return "DEFECT", f"invariantsFile declared but unreadable: {type(ex).__name__}: {ex}", 0

    # Identity is judged against a character golden; style is judged against the pack
    # anchor. Asking "is this the same subject?" of a plate with no subject is nonsense,
    # and asking only "does the linework match?" of a character lets a stranger through.
    mode = "identity" if goldens else "style"
    reference = goldens[0] if goldens else refs[0]

    prev = spec_state(work, sid, idx) or {}
    roll = int(prev.get("roll", 0))
    prev_status = prev.get("status")

    # ORDER MATTERS, and getting it wrong throws away work you already paid for.
    #
    # A VERDICT IS READ BEFORE THE ROLL BUDGET IS CONSULTED. A slot that has spent its
    # last roll still has an artifact on disk and may well have a PASSING verdict
    # waiting; declaring it exhausted without reading that verdict discards a good
    # plate and reports a defect that does not exist. This is the same failure as
    # resume logic that restores defects: the bookkeeping outranking the result.
    if not checklist:
        if os.path.exists(out):
            return "PASS", out, roll                       # nothing judged is declared
    else:
        v = verdict_for(work, sid, idx, out)
        if v and os.path.exists(out):
            if v["verdict"] == "PASS":
                return "PASS", out, roll
            print(f"      roll {roll}/{max_rolls} DEFECT: {str(v.get('why',''))[:110]}")
            clear_verdict(work, sid, idx)                  # the next roll needs a fresh look
            if roll >= max_rolls:
                return ("DEFECT",
                        f"exhausted {max_rolls} rolls against its judged invariants", roll)
        elif os.path.exists(out) and roll > 0 and prev_status == "NEEDS-JUDGMENT":
            # An artifact on disk with no verdict is AMBIGUOUS, and the roll counter
            # cannot disambiguate it. It is either (a) awaiting its first look, or
            # (b) already judged, rejected, and its verdict consumed. The prior STATUS
            # is what tells them apart, and using the roll count alone silently
            # re-briefed a known-rejected plate instead of re-rolling it, so a repaired
            # beat and a raised roll budget both had no effect.
            #
            # Only case (a) must not regenerate: re-rolling something unjudged pays
            # twice and discards the artifact the judge was about to see.
            brief = judge_request(work, sid, idx, reference, out, checklist, mode, roll)
            return "NEEDS-JUDGMENT", (f"awaiting an independent judge; brief at {brief}. "
                                      f"Dispatch a fresh judge with the brief ALONE, write "
                                      f"the verdict to {work}/verdicts/{sid}-{idx}.json, re-run."), roll

    if roll >= max_rolls:
        return "DEFECT", f"exhausted {max_rolls} rolls against its judged invariants", roll

    roll += 1
    ok, detail = generate(prompt, refs, out, size)
    if not ok:
        return "DEFECT", f"generation failed: {detail}", roll
    if not checklist:
        return "PASS", out, roll
    brief = judge_request(work, sid, idx, reference, out, checklist, mode, roll)
    return "NEEDS-JUDGMENT", (f"generated roll {roll}; brief at {brief}. Dispatch a fresh "
                              f"judge with the brief ALONE and write the verdict to "
                              f"{work}/verdicts/{sid}-{idx}.json, then re-run."), roll

SKILLS = pathlib.Path(__file__).resolve().parents[2]
GEN_SCRIPT = os.path.expanduser("~/.agents/skills/chatgpt-images/scripts/generate_image.py")

def load_pack(root, pack_ref):
    """A style pack is the look, as data. Resolve it and its refs to real paths."""
    base = pathlib.Path(root) / pack_ref
    pack = json.loads((base / "pack.json").read_text())
    pack["_dir"] = base
    return pack

REGISTRY = SKILLS.parent / "registry" / "providers.json"

def quirks_for(proj, slot_id, resolved_provider):
    """Known failure modes of the model this slot ACTUALLY runs on.

    Quirks bind to the RESOLVED provider, not to the pin. An unpinned generator is
    provider-agnostic by design, but at run time it still executes on some specific
    model, and that model's quirks are just as real. Binding them to the pin meant
    the one projection that deliberately stayed portable was also the one left
    unguarded, which is backwards.
    """
    out = []
    for g in proj.get("generators", []):
        if g.get("for") == slot_id: out += g.get("quirks", [])
    if REGISTRY.exists() and resolved_provider:
        reg = json.loads(REGISTRY.read_text())["providers"].get(resolved_provider, {})
        for q in reg.get("quirks", []):
            if not any(o["id"] == q["id"] for o in out): out.append(q)
    return out

def compile_slot(proj, comp, slot_id, scene, pack, goldens):
    """Deterministic: nothing load-bearing is retyped, it is assembled from canon."""
    neg = ", ".join("no " + p for p in pack.get("rejectedPoles", []))
    provider = next((g.get("pin") for g in proj.get("generators", [])
                     if g.get("for") == slot_id), None) or comp.get("provider", "gpt-image-2")
    qk = quirks_for(proj, slot_id, provider)
    counters = " ".join(q["counter"] for q in qk)          # appended automatically, never recalled
    prompt = (f"Create a NEW illustration in EXACTLY the visual style of the reference images. "
              f"STRICT STYLE: {pack['styleLine']}. "
              f"Subject: {scene}. "
              f"{counters} "
              f"{neg}. ABSOLUTELY NO text, no letters, no numbers.")
    refs = [str(pack["_dir"] / pack["anchor"])]
    for r in pack.get("refs", [])[1:3]:
        refs.append(str(pack["_dir"] / r))
    refs += goldens                      # locked masters LAST, so identity rides on top
    qa = [i["id"] for i in proj["invariants"]["perSlot"] if i["check"] == "judged"]
    qa += [q["id"] for q in qk if q.get("check") == "judged"]   # countering is never assumed to have worked
    return prompt, refs, qa

def generate(prompt, refs, out, size):
    cmd = [GEN_SCRIPT, "--prompt", prompt, "--filename", out, "--size", size,
           "--quality", "high", "--no-open"]
    for r in refs: cmd += ["--input-image", r]
    r = subprocess.run(["uv", "run"] + cmd, capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip().splitlines()[-1][:160] if r.returncode else out

def judge_request(work, sid, idx, reference, slot_png, checklist, mode, roll):
    """Write the judging BRIEF for one slot, and nothing else.

    A judged check is a ROLE, not a service. The cheapest correct way to fill it is a
    fresh subagent inside whatever runtime is already composing: it costs no key, no
    separate process, and no second vendor, and it is independent for the only reason
    independence matters, which is that it never sees the plan.

    So the composer does not judge. It states, per slot, exactly what a judge must be
    shown (the artifact, the reference, the checklist) and exactly what it must NOT be
    shown (this file, the beats, the prompt, the intent). The runtime dispatches one
    judge per brief and writes a verdict back. That separation is enforced by the shape
    of the brief rather than by asking an agent to please forget what it knows.
    """
    d = pathlib.Path(work) / "judge"; d.mkdir(parents=True, exist_ok=True)
    # Bind the brief to the EXACT bytes being judged. A verdict is only ever valid for
    # the artifact it looked at, and without this there is nothing stopping a verdict
    # from being applied to a later re-roll. A poisoned state file already caused a
    # judge to be dispatched against a known-rejected image; a digest makes that
    # detectable rather than silent.
    brief = {"slot": sid, "index": idx, "roll": roll, "mode": mode,
             "artifactDigest": digest(slot_png),
             "artifact": slot_png, "reference": reference, "checklist": checklist,
             "instruction": ("Judge the pixels only. For EACH checklist item return PASS or "
                             "DEFECT with one sentence of evidence describing what you SEE. "
                             "If you cannot tell, return DEFECT and say what is ambiguous: "
                             "never pass an item you cannot verify."),
             "withheld": ("the plan, the beats, the compiled prompt, and the intent, "
                          "deliberately. A maker shown its own reasoning defends it.")}
    (d / f"{sid}-{idx}.json").write_text(json.dumps(brief, indent=2))
    return str(d / f"{sid}-{idx}.json")

def digest(path):
    """Short content hash of an artifact, for binding a verdict to what it judged."""
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except Exception:
        return None

def verdict_for(work, sid, idx, artifact=None):
    """A verdict the runtime wrote back, or None. Absent is NOT a pass.

    If the brief recorded which bytes were judged and those bytes have since changed,
    the verdict is STALE and is treated as absent. A verdict is only ever valid for the
    artifact it actually looked at."""
    f = pathlib.Path(work) / "verdicts" / f"{sid}-{idx}.json"
    if not f.exists(): return None
    try: v = json.loads(f.read_text())
    except Exception: return None
    if v.get("verdict") not in ("PASS", "DEFECT"): return None   # unparseable fails CLOSED
    if artifact:
        b = pathlib.Path(work) / "judge" / f"{sid}-{idx}.json"
        if b.exists():
            try: want = json.loads(b.read_text()).get("artifactDigest")
            except Exception: want = None
            if want and want != digest(artifact):
                return None                       # judged a different image; fails CLOSED
    return v



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
            elif prev["status"] == "NEEDS-JUDGMENT":
                print(f"  {u['slot']}-{u['index']}: checking for a verdict (no regeneration)")
            else:
                print(f"  {u['slot']}-{u['index']}: retrying previously DEFECT slot")
        try:
            status, detail, roll = run_slot(u, proj, comp, work)
        except Exception as ex:                          # a slot must NEVER take the run down
            status, detail, roll = "DEFECT", f"{type(ex).__name__}: {ex}", 0
        # The roll counter is owned by whoever GENERATES, never by the caller. Counting
        # a re-run as a roll meant a slot merely WAITING on a judge burned through its
        # budget and was eventually declared "exhausted its rolls" for waiting.
        rec = {"slot": u["slot"], "index": u["index"], "status": status, "detail": detail,
               "roll": roll}
        sp.write_text(json.dumps(rec, indent=2))
        print(f"  {u['slot']}-{u['index']}: {status}  {detail if status!='PASS' else ''}")
        results.append(rec)                               # park and CONTINUE, never halt

    pending = [r for r in results if r["status"] == "NEEDS-JUDGMENT"]
    defects = [r for r in results if r["status"] not in ("PASS", "SKIP", "NEEDS-JUDGMENT")]
    print(f"\n{len(results)-len(defects)-len(pending)}/{len(results)} slots passed")

    if pending:
        # Not a failure. The artifacts exist and are waiting on the one check the
        # composer is structurally forbidden to perform on itself.
        print(f"\n{len(pending)} slot(s) AWAITING AN INDEPENDENT JUDGE. Nothing is re-generated by")
        print("re-running; each judged slot resumes from the artifact already on disk.")
        print(f"  briefs:   {work}/judge/*.json")
        print(f"  verdicts: {work}/verdicts/<slot>-<index>.json   {{\"verdict\":\"PASS\"|\"DEFECT\",\"why\":\"...\"}}")
        print("  Give each judge the brief ALONE. It must not see this composition,")
        print("  the beats, or the compiled prompt. That is the entire point.")
        for r in pending: print(f"  - {r['slot']}-{r['index']}")

    if defects:
        print("\nartifact emitted INCOMPLETE. Repair these slots and re-run; passing slots resume free:")
        for d in defects: print(f"  - {d['slot']}-{d['index']}: {d['detail']}")
    if defects: return 1
    return 3 if pending else 0

if __name__ == "__main__":
    sys.exit(main())
