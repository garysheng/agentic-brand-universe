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

    # Provenance policy: the pre-policy golden library is accepted as historical
    # (Gary, 2026-07-25) via an explicit FILE rather than a date, so the debt is a
    # reviewable artifact that can only shrink. See the goldens loop below.
    gf_path = root/"canon"/"provenance-grandfathered.json"
    gf = jload(gf_path) if gf_path.exists() else None
    grandfathered = set((gf or {}).get("goldens") or [])
    grandfathered_hit = set()

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

    # ---- a setting must be able to prove its own SIZE (SPEC v0.9, §12)
    #
    # `emptyPlates` are people-free on purpose so a setting reference never bakes a character's
    # face into a room. That rule is right and it stays. Its unpriced cost: a figure-free interior
    # carries no unit of comparison, so the model picks a size, every render inherits that guess,
    # and nobody can catch it because the plate does not depict the dimension being judged. A
    # hearth room rendered small and cramped through an entire book before its owner said "that
    # room is supposed to be much bigger than that." Same blind spot hid a free-standing firepit
    # under a suspended conical flue that could not have stood up: no plate ever had to show how
    # the thing was built.
    #
    # The fix is a SEPARATE `scalePlate` (same room, anonymous scale figures: small, distant,
    # turned away, faces unreadable, never a canon character) plus a `scale` descriptor stating
    # the size in human terms. Prose survives a re-render; a plate does not.
    #
    # WARNING, never an error: a setting with no scale plate still locks and still renders.
    # PROSE THAT NAMES A FILE THE COMPILER CANNOT PASS.
    #
    # A rule that lives only in prose is a memory test, not a gate. Two forms of this
    # were found in ONE session (nation-of-fire, 2026-07-30), each silently degrading
    # every render that touched it, each caught only by a human eyeballing the canon:
    #
    #   1. jerry-man's EIGHT ql-* poses each said "matching FIGURE N FROM THE LEFT on the
    #      supplied capsule reference sheet" while listing only `face` in the pose's
    #      `sheets`. The capsule was never passed, so the wardrobe was steered by words
    #      alone and drifted across whole batches.
    #   2. christofuturist-village's prose named village-sanctuary.png,
    #      village-construction.png and village-fenceline-night.png by FILE PATH while
    #      `structured.sheets` carried only master/turnaround/blueprint. Those three
    #      could never be passed, so every render fell back to the daytime master
    #      regardless of era or angle.
    #
    # So: flag prose or bake text that names a `reference/...` path not present in the
    # entity's `sheets`, and pose bakes that talk about a "sheet" while passing none.
    # WARNING, never an error: the render still happens, it is just quietly worse.
    ents_dir = root/"canon"/"entities"
    if ents_dir.exists():
        for ef in sorted(ents_dir.glob("*.json")):
            e = jload(ef) or {}
            eid = e.get("id", ef.stem)
            st = e.get("structured") or {}
            sheets = st.get("sheets") or {}
            wired = {str(v) for v in sheets.values()}
            # Match on BASENAME too: prose legitimately writes a shorthand path.
            wired |= {str(v).rsplit("/", 1)[-1] for v in sheets.values()}
            # These contract keys ARE path fields, consumed directly rather than via
            # `sheets`. Scanning them would flag every correctly-wired setting in every
            # universe, and a rule that cries wolf is a rule everyone learns to skip.
            PATH_FIELDS = {"turnaround", "blueprint", "scalePlate", "emptyPlates", "plates"}
            blobs = []
            for k, v in (e.get("prose") or {}).items():
                if isinstance(v, str): blobs.append((f"prose.{k}", v))
            for k, v in (e.get("contract") or {}).items():
                if k in PATH_FIELDS: continue
                if isinstance(v, str): blobs.append((f"contract.{k}", v))
            render = st.get("render") or {}
            for pname, pose in (render.get("poses") or {}).items():
                if isinstance(pose, dict) and isinstance(pose.get("bake"), str):
                    blobs.append((f"pose.{pname}.bake", pose["bake"]))
            for where, text in blobs:
                for path in set(re.findall(r"reference/[\w./-]+\.(?:png|webp|jpg|jpeg)", text)):
                    if path not in wired and path.rsplit("/", 1)[-1] not in wired:
                        warn("PROSE-NAMES-UNWIRED-FILE",
                             f"{eid}: {where} names {path}, which is not in structured.sheets. "
                             "The compiler passes files from `sheets`, so this reference is never "
                             "actually sent and the rule survives only as words.")
            for pname, pose in (render.get("poses") or {}).items():
                if not isinstance(pose, dict): continue
                bake = pose.get("bake") or ""
                if not isinstance(bake, str): continue
                if re.search(r"supplied .{0,40}sheet|reference sheet|FIGURE\s+\d+\s+FROM THE LEFT", bake, re.I):
                    named = [k for k in (pose.get("sheets") or [])]
                    studyish = [k for k in named if any(t in k.lower() for t in
                                ("capsule", "items", "lineup", "turnaround", "study", "sheet"))]
                    if not studyish:
                        warn("POSE-CITES-SHEET-IT-DOES-NOT-PASS",
                             f"{eid}: pose `{pname}` tells the model to match a supplied reference "
                             f"sheet, but its `sheets` list is {named or '[]'} and carries no such "
                             "sheet. Prose cannot make the compiler pass a file.")

    # A SETTING NEEDS A SHOT LIST, NOT ONE MASTER PLATE.
    #
    # A character gets a reference matrix at creation (SPEC 12): eight shots, made
    # BEFORE anything renders, so no later beat has to invent a view of them. Settings
    # got a master, a turnaround and a blueprint, and every camera after that was
    # improvised from the wide shot. That asymmetry is a real gap, and it fails the
    # same way every time: a close-up cannot inherit what the wide plate does not show,
    # so the model re-invents the parts that are out of frame, differently each spread.
    #
    # Earned 2026-07-30 (nation-of-fire, the-teaching-room). One wide master was locked
    # and twelve teaching beats were then asked for at conversational distance. The
    # audience seating drifted spread to spread until a dedicated chairsCloseUp plate
    # was shot; after that, every two-shot inherited the same chairs. Gary: "when you're
    # creating a setting, you should basically create all the shots that you want inside
    # that setting."
    #
    # WARNING, never an error: a one-plate setting used for one beat is perfectly fine.
    if ents_dir.exists():
        for ef in sorted(ents_dir.glob("*.json")):
            e = jload(ef) or {}
            if e.get("kind") != "setting":
                continue
            eid = e.get("id", ef.stem)
            st = e.get("structured") or {}
            sheets = st.get("sheets") or {}
            camera_ish = [k for k in sheets
                          if k not in ("blueprint", "scalePlate", "turnaround")]
            if e.get("status") == "locked" and len(camera_ish) < 2:
                warn("SETTING-HAS-NO-SHOT-LIST",
                     f"{eid}: locked with only {len(camera_ish)} camera plate(s) "
                     f"({camera_ish or '[]'}). A setting used for more than one beat needs a "
                     "SHOT LIST shot at creation, the way a character gets a reference matrix: "
                     "typically a wide establishing, at least one conversational-distance plate, "
                     "and a plate per recurring camera the story actually needs. Every framing "
                     "not shot up front gets re-invented at render time.")

    if ents_dir.exists():
        for ef in sorted(ents_dir.glob("*.json")):
            e = jload(ef) or {}
            if e.get("kind") != "setting":
                continue
            con = e.get("contract") or {}
            eid = e.get("id", ef.stem)
            sp = con.get("scalePlate")
            if not sp:
                warn("SETTING-NO-SCALE-PLATE",
                     f"{eid}: no contract.scalePlate. Its emptyPlates are people-free, so nothing "
                     f"in this setting proves how big it is and every render silently inherits the "
                     f"model's guess. Add a scalePlate (same room, anonymous scale figures).")
            elif not (root/sp).exists():
                warn("SETTING-NO-SCALE-PLATE",
                     f"{eid}: contract.scalePlate -> {sp} (NOT ON DISK)")
            if not (con.get("scale") or "").strip():
                warn("SETTING-NO-SCALE-DESCRIPTOR",
                     f"{eid}: no contract.scale descriptor. State the size in human terms (\"a "
                     f"circular hall about 80 feet across, dome 45 feet at the crown\"); it is "
                     f"passed in every prompt like `dressing`, and prose survives a re-render.")

    # ---- a character must be able to prove its own SCALE and its FUTURE (SPEC v0.10, §12)
    #
    # Two blind spots with one shape: a dimension nothing depicts cannot be judged.
    #
    # 1. RELATIVE HEIGHT. Every entity is described alone, so two men in one frame come
    #    out the same height (or reversed) and it stays invisible until someone who knows
    #    them says "he is much shorter than that." `structured.scale.relativeTo` states it.
    #    A ONE-SIDED relation is the failure mode worth flagging: the compiler emits a line
    #    only when both parties are in frame, so a relation declared on one entity and not
    #    its counterpart still works, but the two records can silently drift apart and then
    #    contradict each other. Cheap to keep symmetric, expensive to discover later.
    #
    # 2. DECLARED-FUTURE LOOKS. An alt look normally changes the FACE and supplies its own
    #    anchorPhoto, so base face sheets are auto-dropped. A prophetic era look inverts it:
    #    the face is continuous, the body changes, and the future has no photograph. Such a
    #    look reaches the model with body sheets only, which are the silhouette it supersedes.
    #    compose-spread refuses this at compile time; lint catches it a step earlier, before
    #    anyone schedules a render.
    if ents_dir.exists():
        chars = {}
        for ef in sorted(ents_dir.glob("*.json")):
            e = jload(ef) or {}
            if e.get("kind") == "character":
                chars[e.get("id", ef.stem)] = e
        known = {p.stem for p in ents_dir.glob("*.json")}
        FACE_KEYS = {"face-3q", "face-neutral", "face", "expressions"}
        for eid, e in chars.items():
            st = e.get("structured") or {}
            rel = ((st.get("scale") or {}).get("relativeTo") or {})
            for other in rel:
                if other not in known:
                    warn("CHARACTER-SCALE-UNKNOWN-TARGET",
                         f"{eid}: structured.scale.relativeTo names '{other}', which is not an "
                         f"entity in this canon.")
                    continue
                back = (((chars.get(other) or {}).get("structured") or {})
                        .get("scale") or {}).get("relativeTo") or {}
                if eid not in back:
                    warn("CHARACTER-SCALE-ONE-SIDED",
                         f"{eid}: declares a height relation to '{other}', but '{other}' declares "
                         f"none back. Record the inverse on '{other}' so the two cannot drift "
                         f"apart and contradict each other.")
            for lid, al in (st.get("altLooks") or {}).items():
                al = al or {}
                kept = set(al.get("keepSheets") or [])
                dropped = set(al.get("dropSheets") or [])
                has_face = bool(al.get("anchorPhoto") or (al.get("sheets") or {})
                                or al.get("keepPhotos") or (kept & FACE_KEYS) - dropped)
                if not has_face:
                    warn("LOOK-NO-IDENTITY-ANCHOR",
                         f"{eid}: altLook '{lid}' supplies no anchorPhoto and no sheets of its "
                         f"own, and an alt look auto-drops the base FACE sheets, so only body "
                         f"sheets would reach the model. Set keepSheets (a base face sheet) "
                         f"and/or keepPhotos if this is a declared-future or prophetic look "
                         f"whose face is continuous; otherwise give it an anchorPhoto.")

    # ---- an entity that is NOT the default avatar must not be cast casually
    #
    # A universe can hold two entities for the SAME person: an allegorical avatar used
    # everywhere, and a literal one that exists for a single book where the real people
    # appear as themselves. Nothing stopped a story casting the literal one because its
    # beat text said the person's name, which is exactly when the avatar is wanted. Cost
    # seven rendered spreads on He Was Always Speaking (2026-07-26) before the operator
    # caught it by eye. An entity opts in by setting `renderDefault: false` and naming
    # its `preferredAlias`.
    if ents_dir.exists():
        nondefault = {}
        for ef in sorted(ents_dir.glob("*.json")):
            e = jload(ef) or {}
            if e.get("renderDefault") is False:
                nondefault[e.get("id", ef.stem)] = e.get("preferredAlias")
        stories_dir = root/"stories"
        if nondefault and stories_dir.exists():
            for sf in sorted(stories_dir.glob("*.json")):
                st = jload(sf) or {}
                cast = set(st.get("features") or [])
                for b in st.get("beats") or []:
                    # a beat's `characters` is a list of ids in most stories and a list of
                    # {id: ...} objects in others; accept both rather than crash the linter.
                    for c in b.get("characters") or []:
                        cast.add(c.get("id") if isinstance(c, dict) else c)
                for eid, alias in nondefault.items():
                    if eid in cast and st.get("id") != (jload(ents_dir/f"{eid}.json") or {}).get("originStory"):
                        warn("ENTITY-NOT-DEFAULT-AVATAR",
                             f"{sf.stem}: casts '{eid}', which is marked renderDefault:false. "
                             f"Use '{alias}' instead unless this story is the specific one that "
                             f"entity exists for.")

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

    # ---- sheet hygiene: aliases, and workflow state stored as visual invariants
    #
    # Two duplicate keys pointing at ONE file is not free: `requiredForRender: [master, face]`
    # then passes the SAME image twice, so a "face macro" contributes nothing and the entity
    # looks better-referenced than it is. Found on 7+ nation-of-fire entities, 2026-07-25.
    #
    # And `invariants` is the array read-back checks are generated FROM, so a workflow flag
    # parked there ("design-pending-tier1", "cast-approval-pending-gary") becomes a check
    # nobody can run against an image. Status belongs in `status` or `authority`, not here.
    STATUS_ISH = ("pending", "approval", "locked-20", "review", "tier1", "todo", "wip", "draft")
    for ej in (root/"canon"/"entities").glob("*.json"):
        e = jload(ej)
        if not e: continue
        st = e.get("structured") or {}
        sheets = st.get("sheets") or {}
        seen = {}
        for k, v in sheets.items():
            if not v: continue
            seen.setdefault(v, []).append(k)
        for path, keys in seen.items():
            if len(keys) > 1:
                req = [k for k in st.get("requiredForRender", []) if k in keys]
                sev = err if len(req) > 1 else warn
                sev("SHEET-DUPLICATE-ALIAS",
                    f"{ej.name}: sheet keys {sorted(keys)} all point at '{path}'"
                    + (f"; requiredForRender names {sorted(req)}, so the same image is passed "
                       f"{len(req)} times and one of them carries no information."
                       if len(req) > 1 else "; one is a dead alias."))
        # The scaffolder writes `lockedBy: "TODO-you"` and nothing ever forces it to be filled,
        # so an entity can carry locked art, frozen provenance and a full pose set while its
        # record of WHO approved it is still a placeholder. Found on 5 nation-of-fire entities
        # 2026-07-25, one of them created and locked that same session.
        au = e.get("authority") or {}
        if sheets and any(sheets.values()):
            if not au.get("lockedBy") or str(au.get("lockedBy")).startswith("TODO"):
                err("AUTHORITY-UNFILLED",
                    f"{ej.name}: has locked art but `authority.lockedBy` is "
                    f"{au.get('lockedBy')!r}. A golden with no recorded approver cannot be "
                    f"attributed, and approval is the whole point of locking.")

        for inv in st.get("invariants", []) or []:
            low = str(inv).lower()
            # A PROHIBITION is a real visual rule even when it contains a trigger word:
            # "no-barcode-no-publisher-mark-no-subtitle-no-review-quote" is a checkable fact
            # about an image and must not be flagged as workflow state (both false positives
            # found on the first real run, 2026-07-25).
            is_prohibition = low.startswith(("no-", "never-")) or "never" in low
            if any(t in low for t in STATUS_ISH) and len(str(inv)) < 60 and not is_prohibition:
                warn("INVARIANT-IS-STATUS",
                     f"{ej.name}: invariant '{inv}' reads as workflow state, not a checkable "
                     f"fact about an image. Read-back checks are generated from invariants, so "
                     f"this becomes an uncheckable check. Move it to `status` or `authority`.")

    # ---- castability: a character the renderer cannot cast
    #
    # An entity can be fully locked, fully art-approved, pass `validate` AND pass
    # `assert-story`, and still be impossible to put in a picture, because the render
    # compiler reads `structured.render.always` and `structured.render.poses[<pose>]`
    # while every gate above reads sheets and files. Nothing reported the gap: it
    # surfaced as a hard KeyError at cast time, after the story was written and the
    # spec was built. Hit at least three times in nation-of-fire (the-arena, then
    # russ-vibes-apostle and nas, then the-chairman + chief-of-toil + the-battle-axe-girls
    # on It Was Not Broken, 2026-07-25). Static, free, and catches the whole class.
    for ej in (root/"canon"/"entities").glob("*.json"):
        e = jload(ej)
        if not e or e.get("kind") not in ("character", "group"): continue
        # An entity with NO sheets has not been scaffolded for art yet, so demanding poses
        # from it is noise. `{}` and a missing key both mean that; checking only for None
        # flagged a doctrine-only group that has no art and wants none (found 2026-07-25).
        if not ((e.get("structured") or {}).get("sheets") or {}): continue
        render = ((e.get("structured") or {}).get("render") or {})
        poses = render.get("poses") or {}
        if not render.get("always") and not poses:
            err("CAST-UNRENDERABLE",
                f"{ej.name}: kind '{e.get('kind')}' has no structured.render block, so the render "
                f"compiler cannot cast it at all. Add render.always plus at least one pose, "
                f"restating rules the entity already carries; invent no new design.")
            continue
        if not poses:
            err("CAST-NO-POSES",
                f"{ej.name}: has structured.render.always but no poses, so no spread can select "
                f"a look for it. Add at least one pose.")
        # A pose names sheet KEYS; a key with no path is a hard exit at render time.
        sheets = (e.get("structured") or {}).get("sheets") or {}
        for pname, pose in poses.items():
            if not isinstance(pose, dict):
                err("CAST-POSE-SHAPE",
                    f"{ej.name}: pose '{pname}' is a {type(pose).__name__}, not an object. A pose is "
                    f"{{'sheets': [...], 'bake': '...'}}; a bare string is silently unusable.")
                continue
            for key in pose.get("sheets", []):
                if key not in sheets:
                    err("CAST-POSE-SHEET-MISSING",
                        f"{ej.name}: pose '{pname}' names sheet key '{key}' which is not in "
                        f"structured.sheets. The compiler hard-exits on this.")
                elif not sheets.get(key):
                    warn("CAST-POSE-SHEET-NULL",
                         f"{ej.name}: pose '{pname}' names sheet key '{key}' whose path is null; "
                         f"the pose is unusable until that shot locks.")

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
                # POLICY: provenance is enforced GOING FORWARD, and the pre-policy library is
                # accepted as historical (Gary, 2026-07-25). Freezing a recipe only became part
                # of `lock-shot` recently, so every older golden is un-auditable and always will
                # be; warning on each one buried real findings under hundreds of lines.
                #
                # The grandfather list is an explicit FILE, not a date, so the debt is a
                # reviewable artifact that can only shrink: a golden not on the list and missing
                # a recipe is an ERROR, because it was locked after the policy and skipped the
                # tool. Re-locking a grandfathered golden with `--recipe` earns it a real one,
                # and the entry should then be deleted from the list.
                if pth in grandfathered:
                    grandfathered_hit.add(pth)
                else:
                    err("GOLDEN-NO-RECIPE", f"{ej.name}: golden '{name}' ({pth}) has no provenance "
                        f"sidecar and is NOT grandfathered, so it was locked without `--recipe`. "
                        f"It is un-auditable and cannot enter a divergence check. Re-lock it with "
                        f"`lock-shot --recipe`.")
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
                    # An input that no longer RESOLVES is usually a rename or an archive move,
                    # not drift, and the fix is NOT to rewrite the recipe: a provenance record
                    # states what was actually passed at generation time, so editing it to match
                    # a later move falsifies the approval. (Nation of Fire's own canon says
                    # exactly this after the apostle-lee folder rename.) Say so, or this warning
                    # quietly advises people to launder their own history.
                    warn("GOLDEN-INPUT-GONE", f"{ej.name}: golden '{name}' was approved against "
                         f"input '{ip}', which no longer resolves, so no divergence check can run "
                         f"for it. Usually a rename or an archive move. Do NOT edit the recipe to "
                         f"match the new path: provenance records what was passed at approval "
                         f"time, and rewriting it falsifies the approval. Either leave it as "
                         f"history, or re-lock the golden with `--recipe` against today's inputs.")
                elif now != want:
                    warn("GOLDEN-STALE", f"{ej.name}: golden '{name}' was approved when input '{ip}' "
                         f"had bytes {want}; it is now {now}. The approval was of a different input; "
                         f"re-judge and re-lock, or confirm the golden still holds.")

    # ---- provider quirk registry
    regf = SKILLS.parent/"registry"/"providers.json"
    providers = jload(regf).get("providers", {}) if regf.exists() else {}
    if not providers: warn("NO-QUIRK-REGISTRY", "no provider registry; quirks cannot be inherited")

    if grandfathered:
        stale = grandfathered - grandfathered_hit
        warn("PROVENANCE-DEBT",
             f"{len(grandfathered_hit)} golden(s) are grandfathered as historical and carry no "
             f"provenance, so they can never enter a divergence check. Re-lock any of them with "
             f"`lock-shot --recipe` and delete the entry to shrink this list."
             + (f" {len(stale)} entry(ies) no longer match a declared golden and can be deleted."
                if stale else ""))

    # ---- projections
    pdir = root/"projections"
    if not pdir.exists():
        warn("NO-PROJECTIONS", "universe declares no projections; it can only make storybooks by hand")
        # CAUTION: this RETURNS, so every check written below runs only for universes that
        # declare projections. nation-of-fire declares none, so a new rule added past this
        # point silently never runs for the universe doing the most rendering. A summary
        # added here in 2026-07 was swallowed exactly this way. Put new entity/asset checks
        # ABOVE this line; only projection-specific checks belong below it.
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
