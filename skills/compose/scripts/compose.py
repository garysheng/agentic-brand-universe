#!/usr/bin/env python3
"""
The composer (SPEC 4.10): plan -> compile -> generate -> gate -> repair, per slot.

Implements the parts the spec asserted and nothing ran:
  * `extends` resolution, which previously nothing merged
  * feasibility of `surface` against `generators.producibleAspects`, checked at PLAN
    time, because discovering it an hour in is the failure it exists to prevent
  * DURABLE per-slot state, so a restart resumes rather than redoing
  * park-the-slot-and-continue, so one defect costs one slot and not the artifact
  * PROVENANCE: every slot writes its recipe (model, exact prompt, every input by
    path and by content hash) before anything is generated

    python3 compose.py <composition.json>                      compose
    python3 compose.py <composition.json> --recipes-only        freeze a baseline, no generation
    python3 compose.py <composition.json> --check-drift <dir>   compare to a baseline, exit 1 on drift
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

def surface_shrink(proj, comp):
    """Warn when a composition cuts the projection's DECLARED surface substantially.

    A projection's geometry is a statement about what this kind of deliverable IS. A
    storybook declaring 24 spreads is saying that a book of this kind runs about that
    long. A composition may override it, and sometimes should, but a large cut is
    almost never an editorial decision: it is the maker shrinking the job to what is
    cheap to generate.

    Earned 2026-07-23, three times in one evening. The maker chose the characterless
    register to avoid the hardest cross-slot invariant, then simplified plates until one
    was an empty rectangle, then cut a book from 24 spreads to 8. Every safeguard in
    this standard constrains EXECUTION. Nothing constrained SELECTION, and selection is
    where the drift was. This does not stop it, because a shorter book is legitimate. It
    makes the choice say its own name out loud.
    """
    out = []
    dec = proj.get("surface", {}).get("geometry", {})
    got = comp.get("surface", {})
    for k, want in dec.items():
        if not isinstance(want, int): continue
        have = got.get(k, comp.get("repeat", {}).get(k))
        if isinstance(have, int) and have < want * 0.6:
            out.append(f"composition sets {k}={have} where the projection declares {want}. "
                       f"That is {round(100 * have / want)}% of the declared surface. A shorter "
                       f"one is legitimate, but say why: this is where a maker shrinks a job "
                       f"to what is cheap to generate.")
    return out

def plan(proj, comp):
    out = []
    for slot in proj["slots"]:
        rep = slot.get("repeat")
        n = comp.get("repeat", {}).get(slot["id"], 1) if rep else 1
        for i in range(n):
            out.append({"slot": slot["id"], "index": i, "type": slot["type"],
                        "emitter": slot.get("emitter")})
    return out

def goldens_for(comp, sid, idx):
    """Which locked sheets this slot binds, AT THIS INDEX.

    Goldens could previously be bound per SLOT only, which cannot express a character
    whose state changes partway through a book. That is not an edge case: a wardrobe
    marker that ARRIVES at the turn is one of the cheapest ways to make a reader feel a
    change before they read it, and it is unrepresentable if every spread must share one
    sheet.

    So a slot's goldens may be a LIST (every index) or a MAPPING of index ranges to
    lists:

        "goldens": {
          "spread": { "0-20": ["reference/maya/master.png"],
                      "21-23": ["reference/maya/master-rust.png"] },
          "cover":  ["reference/maya/master.png"]
        }

    Ranges are inclusive. An index matching no range binds nothing, which fails loudly
    at the reference resolver rather than silently rendering a character with no anchor.
    """
    g = comp.get("goldens", {})
    if not isinstance(g, dict):
        return list(g or [])
    spec = g.get(sid, g.get("default", []))
    if isinstance(spec, list):
        return list(spec)
    if not isinstance(spec, dict):
        return []
    for key, val in spec.items():
        k = str(key)
        if "-" in k:
            lo, hi = k.split("-", 1)
            if lo.strip().isdigit() and hi.strip().isdigit():
                if int(lo) <= idx <= int(hi):
                    return list(val)
        elif k.isdigit() and int(k) == idx:
            return list(val)
    return []

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

EMITTERS = {"brand-card": "brand-card/scripts/card.py",
            "explanatory-plate": "explanatory-plate/scripts/plate.py"}


def spec_version(comp):
    """The spec version the UNIVERSE pins, never the engine's own constant.

    A recipe records what the universe claimed to conform to at the moment it was
    assembled. Reading the engine constant instead would make every recipe agree with
    whatever engine happened to run it, which is precisely the drift this is here to
    detect.
    """
    try:
        u = json.loads((pathlib.Path(comp["universe"]) / "universe.json").read_text())
        return (u.get("spec") or {}).get("version")
    except Exception:
        return None


def ref_stack(refs):
    """Every input by path AND by content hash.

    A golden whose BYTES change while its path stays the same is drift that a path
    alone cannot see, and it is the likeliest kind: goldens get re-locked in place.
    `digest` returns None for a path that does not resolve, so a missing reference is
    recorded rather than silently dropped from the provenance.
    """
    return [{"path": r, "digest": digest(r)} for r in refs]


def recipe_digest(rec):
    """Digest of everything that determines the artifact, and nothing else.

    No clock, no run id, no work directory. A provenance record that changes on every
    run is a log line; only one that changes when the INPUTS change can answer "did
    anything drift?".
    """
    body = {k: v for k, v in rec.items() if k != "recipeDigest"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]


def recipe_path(work, sid, idx):
    return pathlib.Path(work) / "recipes" / f"{sid}-{idx}.json"


def write_recipe(work, rec):
    p = recipe_path(work, rec["slot"], rec["index"])
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rec, indent=2, sort_keys=True))
    return str(p)


def assemble_one(proj, comp, sid, idx, stype, emitter=None):
    """Resolve ONE slot into its provenance recipe. Generates nothing, costs nothing.

    Returns (recipe, error). This is the SINGLE assembly path: `_run_slot` executes
    what this returns rather than resolving the same things a second time. Two
    assembly paths would drift apart, and the drift check would then be verifying the
    path nobody renders from.

    Two things depend on this existing at all:

    1. **Provenance.** Every generated asset must carry its recipe: the model, the
       exact prompt, and every input by path. The composer previously built all three
       in memory, passed them to the image model, and kept none of them, so the one
       pipeline that assembles prompts from canon was also the one that could not say
       what it had sent.
    2. **The drift check.** A generated artifact cannot be byte-reproduced, so
       re-running the composer proves nothing about drift. The RECIPE can be
       reproduced exactly. Unchanged canon plus an unchanged spec must assemble to an
       identical recipe, and anything else is either drift in the canon or
       non-determinism in this function.

    Nothing machine-specific may enter a recipe: no work directory, no output path, no
    absolute temp path. That is why the deterministic payload here carries no `out`.
    """
    spec = (comp.get("slots") or {}).get(sid)
    if spec is None:
        return None, "no composition data for this slot"
    rec = {"slot": sid, "index": idx, "type": stype,
           "specVersion": spec_version(comp),
           "projection": proj.get("id"),
           "extendsChain": proj.get("_extends_chain", [])}

    if stype != "generated":
        em = (emitter or "").split(":")[-1]
        script = EMITTERS.get(em)
        if not script:
            return None, f"unknown emitter '{em}'"
        rec.update({"emitter": em, "emitterScript": str(SKILLS / script),
                    "payload": spec})
        rec["recipeDigest"] = recipe_digest(rec)
        return rec, None

    if spec.get("art"):                                   # art supplied by the composition
        rec["art"] = spec["art"]
        rec["recipeDigest"] = recipe_digest(rec)
        return rec, None

    # A composition may bind ONE pack, or a pack PER SLOT. A book that weaves a
    # narrative register and a diagram register is one composition in two registers.
    b = comp.get("bind", {}).get("style-pack")
    pack_ref = b.get(sid, b.get("default")) if isinstance(b, dict) else b
    if not pack_ref:
        return None, f"slot '{sid}' has no style-pack binding"
    pack = load_pack(comp["universe"], pack_ref)

    # Goldens are per-slot too. A register that REJECTS the cast must not be handed
    # the cast: passing a character master into a characterless plate is a
    # contradiction the compiler should refuse, not one the model has to resist.
    goldens = goldens_for(comp, sid, idx)
    rejected = [r.lower() for r in pack.get("rejectedPoles", [])]
    if goldens and any(("character" in r) or ("storybook-register" in r) for r in rejected):
        return None, (f"slot '{sid}' binds pack '{pack['id']}' which rejects characters, "
                      f"but was handed {len(goldens)} character golden(s). Registers disagree.")
    scene = spec.get("scene", "")
    if comp.get("beats") and sid in ("spread", "art") and idx < len(comp["beats"]):
        scene = comp["beats"][idx]                       # one beat per repeated slot
    if comp.get("plateScenes") and sid == "plate" and idx < len(comp["plateScenes"]):
        scene = comp["plateScenes"][idx]
    if not scene:
        return None, "no scene for this slot"
    if comp.get("_lock") and goldens:                    # only where a character is actually bound
        scene = comp["_lock"] + " Scene: " + scene

    prompt, refs, qa = compile_slot(proj, comp, sid, scene, pack, goldens)
    rec.update({"provider": provider_for(proj, comp, sid),
                "size": spec.get("size", "1024x1024"),
                "pack": {"id": pack.get("id"), "ref": pack_ref},
                "prompt": prompt, "refs": ref_stack(refs),
                "goldens": goldens, "checklist": qa})
    rec["recipeDigest"] = recipe_digest(rec)
    return rec, None


def assemble_all(proj, comp):
    """Every slot's recipe, in plan order. No generation, no API, no cost."""
    out, errs = [], []
    for u in plan(proj, comp):
        rec, err = assemble_one(proj, comp, u["slot"], u["index"], u["type"], u.get("emitter"))
        if err:
            errs.append(f"{u['slot']}-{u['index']}: {err}")
        else:
            out.append(rec)
    return out, errs


def check_drift(recipes, baseline):
    """Compare freshly assembled recipes against a committed baseline.

    Reports THREE distinct conditions, because collapsing them hides the interesting
    one. A changed digest is drift. A recipe with no baseline is new work nobody
    froze. A baseline with no recipe is a slot that silently stopped being planned,
    which is the one a "did anything change?" check most easily misses.
    """
    base = pathlib.Path(baseline)
    changed, unfrozen, vanished = [], [], []
    seen = set()
    for r in recipes:
        key = f"{r['slot']}-{r['index']}"
        seen.add(key)
        f = base / f"{key}.json"
        if not f.exists():
            unfrozen.append(key); continue
        try:
            old = json.loads(f.read_text())
        except Exception as ex:
            changed.append((key, f"baseline unreadable: {type(ex).__name__}: {ex}")); continue
        if old.get("recipeDigest") != r["recipeDigest"]:
            fields = sorted({k for k in set(old) | set(r)
                             if k != "recipeDigest" and old.get(k) != r.get(k)})
            changed.append((key, "differs in: " + (", ".join(fields) or "recipeDigest only")))
    for f in sorted(base.glob("*.json")):
        if f.stem not in seen:
            vanished.append(f.stem)
    return changed, unfrozen, vanished


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
    rec, err = assemble_one(proj, comp, sid, idx, unit["type"], unit.get("emitter"))
    if err:
        return "DEFECT", err, 0
    write_recipe(work, rec)          # BEFORE generating: a slot that then fails still
                                     # has to say what it was about to make.
    out = str(pathlib.Path(work) / f"{sid}-{idx}.png")
    if unit["type"] == "deterministic":
        pf = pathlib.Path(work) / f"{sid}-{idx}.spec.json"
        pf.write_text(json.dumps({**rec["payload"], "out": out}, indent=2))
        r = subprocess.run([sys.executable, rec["emitterScript"], str(pf)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return "DEFECT", (r.stdout + r.stderr).strip().splitlines()[-1][:200]
        return "PASS", out
    # generated slot: compile -> generate -> judge -> repair, per SPEC 4.10
    if rec.get("art"):                                    # art supplied by the composition
        return "PASS", rec["art"]
    spec = comp["slots"][sid]
    goldens, prompt, refs = rec["goldens"], rec["prompt"], [r["path"] for r in rec["refs"]]
    qa, size = rec["checklist"], rec["size"]
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
        v = verdict_for(work, sid, idx, out, require_depicts=wants_readback(proj))
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

# What a slot may be exempted from. A rule that is right for interior art can be flatly
# wrong for a cover: every book cover ever printed carries its own title, so a blanket
# "no text or lettering" turns the one slot that MUST have type into a defect.
#
# Earned 2026-07-23. A style pack copied "text or lettering" into its rejected poles from
# a wordless-plate context, the cover came back bare, and the first instinct was to design
# around the rule with a deterministic overlay. Gary: "if the style pack rejects lettering
# outright, the style pack is wrong... we just got to update our code, not listen to rules
# that we need to update." A canon rule is not physics. When a rule and the work disagree,
# check which one is wrong before building scaffolding around it.
PERMIT_POLES = {"text": ("text or lettering", "text", "lettering", "words", "type")}

def provider_for(proj, comp, slot_id):
    """The model this slot ACTUALLY runs on: the generator's pin, else the
    composition's choice, else the default. One definition, because the compiled
    prompt and the recorded recipe must never disagree about what ran."""
    return next((g.get("pin") for g in proj.get("generators", [])
                 if g.get("for") == slot_id), None) or comp.get("provider", "gpt-image-2")


def applies_to(inv, slot_id):
    """A perSlot invariant applies to every slot UNLESS it names the ones it governs."""
    only = inv.get("slots")
    return True if not only else slot_id in only

def compile_slot(proj, comp, slot_id, scene, pack, goldens):
    """Deterministic: nothing load-bearing is retyped, it is assembled from canon."""
    slot = next((x for x in proj.get("slots", []) if x.get("id") == slot_id), {})
    permitted = set()
    for perm in slot.get("permits", []):
        permitted |= set(PERMIT_POLES.get(perm, (perm,)))
    poles = [x for x in pack.get("rejectedPoles", []) if str(x).lower() not in permitted]
    neg = ", ".join("no " + p for p in poles)
    provider = provider_for(proj, comp, slot_id)
    qk = quirks_for(proj, slot_id, provider)
    counters = " ".join(q["counter"] for q in qk)          # appended automatically, never recalled
    prompt = (f"Create a NEW illustration in EXACTLY the visual style of the reference images. "
              f"STRICT STYLE: {pack['styleLine']}. "
              f"Subject: {scene}. "
              f"{counters} "
              f"{neg}." + ("" if "text" in slot.get("permits", [])
                           else " ABSOLUTELY NO text, no letters, no numbers."))
    refs = [str(pack["_dir"] / pack["anchor"])]
    for r in pack.get("refs", [])[1:3]:
        refs.append(str(pack["_dir"] / r))
    # Goldens are declared relative to the UNIVERSE ROOT and must be joined to it. Left
    # verbatim they only resolved when the process happened to be run from that
    # directory, and from anywhere else the identity anchors silently failed to attach:
    # a book of strangers, with every style gate still green because the LOOK was never
    # the thing that broke. Silent identity loss is the exact failure goldens exist to
    # prevent, so it must not depend on a working directory.
    root = pathlib.Path(comp["universe"])
    refs += [g if os.path.isabs(g) else str(root / g) for g in goldens]
    qa = [i["id"] for i in proj["invariants"]["perSlot"]
          if i["check"] == "judged" and applies_to(i, slot_id)]
    qa += [q["id"] for q in qk if q.get("check") == "judged"]   # countering is never assumed to have worked
    return prompt, refs, qa

def generate(prompt, refs, out, size):
    # SPEC layer 2, the load-bearing reference resolver: every reference resolves to a
    # real asset or the render REFUSES. A missing golden that is merely skipped produces
    # a plausible image of the wrong person, which is worse than no image at all because
    # it passes every check that is not about identity.
    missing = [r for r in refs if not os.path.exists(r)]
    if missing:
        return False, ("reference(s) do not resolve, refusing to render rather than "
                       "generate without them: " + ", ".join(missing))
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
                             "never pass an item you cannot verify. ALSO return a field "
                             "`depicts`: one plain sentence naming what the image actually "
                             "shows, as you would describe it to someone who cannot see it."),
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

def readback(work, sid, idx, intended):
    """Pair what the blind judge SAW with what the scene INTENDED, for a separate check.

    Every invariant in a typical projection is NEGATIVE: no text, no perspective, at most
    N elements, one flat ground. Nothing asserts the artifact means anything. Repairing a
    slot against a purely negative gate therefore walks it toward the artifact that
    satisfies every rule most easily, which is the EMPTY FRAME. That is not a thought
    experiment: a plate for "a great-grandfather preaching under persecution" passed all
    eight of its invariants as a blank rectangle.

    The gate cannot catch this by design. The judge is blind to the plan, which is what
    makes it honest about style and simultaneously unable to notice that the subject is
    missing.

    So the check is split in two, and NEITHER half can rationalise:
      stage 1  a judge sees the IMAGE and no intent, and reports what it depicts.
      stage 2  a comparer sees the INTENT and that sentence, and never the image.
    A compliance gate proves nothing off-brand shipped. Only this proves something
    shipped at all.
    """
    d = pathlib.Path(work) / "readback"; d.mkdir(parents=True, exist_ok=True)
    v = verdict_for(work, sid, idx)
    pair = {"slot": sid, "index": idx,
            "intended": intended,
            "judgeSaw": (v or {}).get("depicts"),
            "question": ("Do these describe the same picture? Answer MATCH or MISMATCH. "
                         "You are deliberately not shown the image: judge only whether the "
                         "description could plausibly be a description of the intent."),
            "withheld": "the image itself, deliberately"}
    (d / f"{sid}-{idx}.json").write_text(json.dumps(pair, indent=2))
    return str(d / f"{sid}-{idx}.json")

def wants_readback(proj):
    """True when the contract declares that the artifact must DEPICT its subject."""
    inv = proj.get("invariants", {})
    for scope in ("perSlot", "crossSlot"):
        for i in inv.get(scope, []):
            if str(i.get("id", "")).startswith("depicts-its-subject"):
                return True
    return False

def verdict_for(work, sid, idx, artifact=None, require_depicts=False):
    """A verdict the runtime wrote back, or None. Absent is NOT a pass.

    If the brief recorded which bytes were judged and those bytes have since changed,
    the verdict is STALE and is treated as absent. A verdict is only ever valid for the
    artifact it actually looked at."""
    f = pathlib.Path(work) / "verdicts" / f"{sid}-{idx}.json"
    if not f.exists(): return None
    try: v = json.loads(f.read_text())
    except Exception: return None
    if v.get("verdict") not in ("PASS", "DEFECT"): return None   # unparseable fails CLOSED
    # A contract that demands the artifact depict its subject needs the judge's own
    # description to compare against. No description, no verdict: fails CLOSED.
    if require_depicts and not str(v.get("depicts", "")).strip(): return None
    if artifact:
        b = pathlib.Path(work) / "judge" / f"{sid}-{idx}.json"
        if b.exists():
            try: want = json.loads(b.read_text()).get("artifactDigest")
            except Exception: want = None
            if want and want != digest(artifact):
                return None                       # judged a different image; fails CLOSED
    return v



def main():
    argv = sys.argv[1:]
    recipes_only = "--recipes-only" in argv
    baseline = None
    if "--check-drift" in argv:
        i = argv.index("--check-drift")
        if i + 1 >= len(argv):
            print("--check-drift needs a baseline directory"); return 2
        baseline = argv[i + 1]
        del argv[i:i + 2]
    argv = [a for a in argv if a != "--recipes-only"]
    if not argv:
        print(__doc__.strip().splitlines()[-1] if __doc__ else "usage: compose.py <composition.json>")
        return 2
    comp = json.load(open(argv[0]))
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

    if recipes_only or baseline:
        # Assembly only. No image model is reached on either path, so both are free
        # and both are safe to run in CI on every push.
        recs, aerrs = assemble_all(proj, comp)
        if aerrs:
            print("ASSEMBLY FAILED, so there is nothing to compare:")
            for e in aerrs: print("  -", e)
            return 2
        if baseline:
            changed, unfrozen, vanished = check_drift(recs, baseline)
            for k, why in changed:   print(f"  DRIFT     {k}: {why}")
            for k in unfrozen:       print(f"  UNFROZEN  {k}: no baseline recipe")
            for k in vanished:       print(f"  VANISHED  {k}: baseline has it, the plan no longer does")
            if changed or unfrozen or vanished:
                print(f"\n{len(changed)} drifted, {len(unfrozen)} unfrozen, {len(vanished)} vanished")
                print("Unchanged canon and an unchanged spec must assemble to identical recipes.")
                print("If this change is intended, re-freeze the baseline with --recipes-only.")
                return 1
            print(f"\n{len(recs)} recipe(s) identical to the baseline. No drift.")
            return 0
        for r in recs:
            write_recipe(work, r)
            print(f"  {r['slot']}-{r['index']}  {r['recipeDigest']}  {r.get('provider', r.get('emitter', '-'))}")
        print(f"\n{len(recs)} recipe(s) written to {work}/recipes/. Nothing generated.")
        return 0

    for w in surface_shrink(proj, comp):
        print(f"  NOTE  {w}")
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
