#!/usr/bin/env python3
"""
Brand universe linter.

Static checks over a universe and everything it declares: packs, entities, goldens,
provenance, quirks. No generation, no API, no cost. Catches the classes of failure
that were previously only discovered by rendering, sometimes an hour into one.

    python3 lint.py <universe-dir>

Exit 0 clean, 1 warnings only, 2 errors.
"""
import hashlib, json, pathlib, re, sys

E, W = [], []
def err(code, msg): E.append((code, msg))
def warn(code, msg): W.append((code, msg))

# NOT every .json in stories/ is a story: voice-gate writes its waiver sidecar as
# `<manuscript-stem>.voice-waivers.json` beside the manuscript, inside stories/.
# Mirrors engine `agenticstory.store.STORY_SIDECAR_SUFFIXES` (this script stays
# stdlib-and-standalone, so the tuple is restated rather than imported).
STORY_SIDECAR_SUFFIXES = (".voice-waivers.json",)

def story_files(stories_dir):
    return [f for f in sorted(stories_dir.glob("*.json"))
            if not any(f.name.endswith(s) for s in STORY_SIDECAR_SUFFIXES)]

def _sha16(path):
    """First 16 hex of a file's sha256, or None if it does not resolve. Must match the
    engine's `_digest` so a golden's recorded input hashes compare equal here."""
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except Exception:
        return None

def _lint_windows(eid, kind_word, variants: dict):
    """Static checks on a variant set's `validFor` windows (SPEC v0.18).

    compose-spread refuses a WRONG-era selection at render time. Only lint can see
    the shape of the whole SET, and the hazard lives there: a set where SOME
    variants declare a window and others do not has a hole at exactly the point
    where the author believed the gate was closed, because an undeclared variant
    is legal at every date. A set with NO windows at all is the default and is
    silent.
    """
    windowed, bare = [], []
    for key, decl in variants.items():
        name = "the default look" if key is None else f"'{key}'"
        vf = (decl or {}).get("validFor")
        if vf is None:
            bare.append(name)
            continue
        if not isinstance(vf, dict):
            err("VALIDFOR-MALFORMED",
                f"{eid}: {kind_word} {name} has validFor {vf!r}; it must be an object "
                f"like {{\"from\": 1974, \"to\": 2003}} with either bound optional.")
            continue
        lo, hi = vf.get("from"), vf.get("to")
        if lo is None and hi is None:
            err("VALIDFOR-MALFORMED",
                f"{eid}: {kind_word} {name} declares an EMPTY validFor, which constrains "
                f"nothing. Give it a `from`, a `to`, or remove it.")
            continue
        bad = [b for b in (lo, hi) if b is not None and not isinstance(b, (int, float))]
        if bad:
            err("VALIDFOR-MALFORMED",
                f"{eid}: {kind_word} {name} has non-numeric validFor bound(s) {bad!r}. "
                f"A window is compared numerically, so a year is 1974 and never \"1974\".")
            continue
        if lo is not None and hi is not None and lo > hi:
            err("VALIDFOR-INVERTED",
                f"{eid}: {kind_word} {name} is valid from {lo} to {hi}, which is empty. "
                f"No spread can ever legally select it.")
            continue
        windowed.append(name)
    if windowed and bare:
        warn("VALIDFOR-PARTIAL",
             f"{eid}: {', '.join(windowed)} declare a validFor window but "
             f"{', '.join(bare)} do not, so the undeclared one(s) stay legal at EVERY "
             f"date and the era gate has a hole precisely where it looks closed. "
             f"Give every {kind_word} in the set a window, or none of them.")


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

    # ONE definition of a gate-complete setting, imported rather than restated. Guarded:
    # the linter must still run from a checkout whose engine is not importable, and a
    # silently-skipped check is better than a linter that cannot start. The engine ships
    # in this repo (which IS the plugin payload), so in practice this always resolves.
    #
    # Found by WALKING UP FOR A MARKER, never by counting parents: this runs from a git
    # clone and from a plugin cache, and a fixed depth encodes one of those layouts.
    _here = pathlib.Path(__file__).resolve()
    _root = next((c for c in [_here, *_here.parents]
                  if (c / "engine" / "agenticstory").is_dir()), None)
    _gaps = None
    if _root is not None:
        try:
            sys.path.insert(0, str(_root / "engine"))
            from agenticstory.model import setting_contract_gaps as _gaps
        except Exception:
            _gaps = None

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
        for sf in story_files(stories_dir):
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

    # A CHARACTER WHOSE WARDROBE IS ONLY AN ADJECTIVE WILL DRIFT.
    #
    # Consistency has to be pinned to something the compiler can PASS. jerry-man pins his
    # clothes with capsule sheets plus per-look `ql-*` poses, so his cardigan is identical
    # in every spread. selah carried the same intent as the words "refined modern-chic
    # wardrobe in CREAM AND GOLD", with no wardrobe sheet and no wardrobe pose anywhere, so
    # the model invented a different cream garment on every render of a 20-spread book and
    # every one of them satisfied canon. Earned 2026-07-30. A colour adjective is not a
    # wardrobe; a reference is.
    #
    # Flag a character that RECURS (has locked sheets and a render block) but has no pose
    # A LOCKED entity whose art is reachable ONLY through `contract`, with no
    # `structured.sheets` at all, cannot have a plate resolved for it.
    #
    # `contract.turnaround` / `blueprint` / `emptyPlates` describe the art; `sheets` is
    # what the RESOLVER reads. An entity that fills the first and not the second looks
    # completely finished: it is `status: locked`, its files are on disk, and every one
    # of them carries provenance. It fails much later and somewhere else, as
    # `compose-spec` reporting `available: NONE` for a setting the author has already
    # written into a beat, at which point the plate is simply never passed and the spread
    # renders off the style anchor alone.
    #
    # Earned 2026-08-03 (nation-of-fire, he-is-a-jealous-god): `the-great-stage` had been
    # locked since 2026-07-19 with four plates and full contract prose, and had never once
    # been cast through the framework compiler. Ten more entities in the same universe
    # were in the identical state, including two heavily-used settings.
    #
    # WARNING, never an error: the entity predates the resolver and its art is real. The
    # repair is deterministic, so the finding prints it rather than describing it.
    if ents_dir.exists():
        for ef in sorted(ents_dir.glob("*.json")):
            e = jload(ef) or {}
            if e.get("status") != "locked":
                continue
            eid = e.get("id", ef.stem)
            if (e.get("structured") or {}).get("sheets"):
                continue
            con = e.get("contract") or {}

            # KEY EVERY SHEET BY ITS FILENAME, never by the contract SLOT it came from.
            # The slot name is right only when the two happen to agree. A multi-state
            # visual-metaphor stores its neutral plate as `contract.turnaround`, so keying
            # by slot emits `"turnaround": ".../master.png"` and the entity ends up with no
            # `master` key at all, which is the one name the resolver's own hero fallback
            # looks for. Keying by filename produced `master` for three of the eleven
            # entities this check first found (the-conditioned-bell, the-old-feast,
            # the-one-lit-board) and matched the slot name everywhere else.
            def _key(p): return p.rsplit("/", 1)[-1].rsplit(".", 1)[0]

            repair, empties = {}, []
            for k in ("turnaround", "blueprint", "scalePlate", "blockingPlate"):
                v = con.get(k)
                if isinstance(v, str) and v:
                    repair.setdefault(_key(v), v)
            for p in con.get("emptyPlates") or []:
                if isinstance(p, str) and p:
                    repair.setdefault(_key(p), p)
                    empties.append(_key(p))
            if not repair:
                continue
            # The GATE is ONE SINGLE-VIEW plate. Never the turnaround: it is a multi-panel
            # study, and the compiler's single-image guard exists precisely because passing
            # one makes the model reproduce its LAYOUT instead of the scene.
            gate = "master" if "master" in repair else (empties[0] if empties else next(iter(repair)))
            pairs = ", ".join(f'"{k}": "{v}"' for k, v in repair.items())
            warn("LOCKED-BUT-NO-SHEETS",
                 f"{eid}: is locked and declares {len(repair)} contract plate(s), but has no "
                 f"`structured.sheets`, so the compiler can resolve NO plate for it and "
                 f"compose-spec will report 'available: NONE'. Repair (additive, invents "
                 f"nothing): set structured.sheets = {{{pairs}}} and "
                 f'requiredForRender = ["{gate}"].')

    # carrying a wardrobe-ish sheet. WARNING, never an error: a character who appears once
    # does not need a capsule.
    if ents_dir.exists():
        for ef in sorted(ents_dir.glob("*.json")):
            e = jload(ef) or {}
            if e.get("kind") != "character":
                continue
            eid = e.get("id", ef.stem)
            st = e.get("structured") or {}
            sheets = st.get("sheets") or {}
            poses = ((st.get("render") or {}).get("poses") or {})
            if not sheets or not poses:
                continue
            WARDROBE_HINT = ("capsule", "wardrobe", "outfit", "look", "items", "closet")
            has_wardrobe_sheet = any(any(h in k.lower() for h in WARDROBE_HINT) for k in sheets)
            pose_passes_wardrobe = any(
                any(any(h in str(sk).lower() for h in WARDROBE_HINT) for sk in (p.get("sheets") or []))
                for p in poses.values() if isinstance(p, dict))
            if not has_wardrobe_sheet and not pose_passes_wardrobe:
                warn("CHARACTER-WARDROBE-NOT-PINNED",
                     f"{eid}: has locked sheets and {len(poses)} render pose(s) but NO wardrobe "
                     "sheet and no pose that passes one, so their clothing is steered by prose "
                     "alone and will differ on every render. Pin it the way jerry-man does: a "
                     "capsule sheet plus per-look poses that pass it.")

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
            # ---- `status: locked` MUST MEAN THE GATE WOULD ACCEPT IT (v0.29)
            #
            # `lock_shot` and `refs.resolve_setting` disagreed about what locked meant, so
            # a setting could only reach `locked` by being hand-flipped in the JSON, and a
            # hand-flip cannot be checked by the tool that was bypassed. Both now call
            # `setting_contract_gaps`; this reports an entity whose recorded status and
            # actual gate-completeness disagree, which is a state the promoter can no
            # longer create and old canon still carries.
            if e.get("status") == "locked" and _gaps is not None:
                miss = _gaps(con)
                if miss:
                    warn("SETTING-LOCKED-BUT-GATE-REFUSES",
                         f"{eid}: status is 'locked' but the render gate would refuse it: "
                         f"{'; '.join(miss)}. `locked` is a claim about the art on disk, so a "
                         f"status the gate contradicts is a record that is simply not true. "
                         f"Shoot what is missing, or set status back to 'unlocked'.")
            # ---- NESTING (SPEC v0.29): find the multi-room entity before it costs a book
            #
            # A setting carries ONE flat contract, so an entity covering several rooms has
            # nowhere to put a per-room rule. Authors work around it by prefixing the room
            # name onto an invariant ("studyNook ONLY: exactly two armchairs"), and that
            # workaround is the tell. It is not cosmetic: every setting invariant becomes a
            # render-readback QA check, so on a nine-room entity each room is graded against
            # the other eight rooms' furniture.
            #
            # christofuturist-home is the worked case. It reached twelve plates over nine
            # rooms and cost the spec twice: v0.13 added contract.scalePlate because its
            # hearth room rendered small, and v0.29 added nesting because its sunken pit had
            # nowhere to declare fixed lettered seating.
            plate_keys = set((e.get("structured") or {}).get("sheets") or {})
            # The tell is an EXCLUSIVITY marker, not merely a plate-name prefix. First cut
            # matched any invariant starting with a plate key and produced four false
            # positives on real canon: `porch-house-wall-left-valley-and-rail-right`,
            # `kitchen-is-the-one-of-one-kitchen-grace` and `summit-is-a-modest-bald-rock`
            # are per-ANGLE handedness and identity statements, which are the correct way
            # to describe one entity's several cameras. What actually signals a flat
            # contract straining is "studyNook ONLY: EXACTLY TWO armchairs", which says a
            # rule holds for one plate and NOT its siblings.
            scoped = [i for i in (e.get("structured") or {}).get("invariants") or []
                      if isinstance(i, str)
                      and any(re.match(rf"^{re.escape(k)}\s+ONLY\b", i) for k in plate_keys)]
            if scoped:
                warn("SETTING-WANTS-NESTING",
                     f"{eid}: {len(scoped)} invariant(s) are scoped to a single plate by name "
                     f"(e.g. {scoped[0][:48]!r}). One entity is covering several rooms, so every "
                     f"room is read-back against the others' rules. Split the rooms into their "
                     f"own settings with `partOf: {eid}`, and move the genuinely house-wide "
                     f"rules into `structured.houseRules`.")
            # Count ROOMS, not contract slots. turnaround/blueprint/scalePlate/
            # blockingPlate/master are structural and were inflating the count: the
            # cold-cathedral read as 8 "rooms" when three were slots and it is cast by
            # zero spreads.
            _SLOTS = {"turnaround", "blueprint", "scalePlate", "blockingPlate", "master"}
            rooms = plate_keys - _SLOTS
            if len(rooms) >= 8 and not (e.get("structured") or {}).get("houseRules"):
                warn("SETTING-WANTS-NESTING",
                     f"{eid}: {len(rooms)} room plates on one setting and no `houseRules`. That "
                     f"is usually a building rather than a room. Consider child settings with "
                     f"`partOf: {eid}`.")
            # houseRules that nothing inherits is dead config
            # only a POPULATED houseRules is dead config; the scaffold writes an empty
            # one on every new setting so the field is discoverable, and warning on that
            # would make the linter noisy on correct, brand-new canon.
            _hr = (e.get("structured") or {}).get("houseRules") or {}
            if any(v for v in _hr.values()):
                kids = [f.stem for f in ents_dir.glob("*.json")
                        if ((jload(f) or {}).get("partOf") or "").strip() == eid]
                if not kids:
                    warn("HOUSE-RULES-WITH-NO-CHILDREN",
                         f"{eid}: declares structured.houseRules but no entity is `partOf` it, so "
                         f"nothing inherits them. Either nest the rooms or move the rules back "
                         f"into this entity's own invariants.")

            if not (con.get("scale") or "").strip():
                warn("SETTING-NO-SCALE-DESCRIPTOR",
                     f"{eid}: no contract.scale descriptor. State the size in human terms (\"a "
                     f"circular hall about 80 feet across, dome 45 feet at the crown\"); it is "
                     f"passed in every prompt like `dressing`, and prose survives a re-render.")

        # ---- a PROP must be able to prove its own size too (SPEC v0.21)
        #
        # A prop had no size record of ANY kind: no descriptor, no plate. So a pendant, a
        # chair and a door were each whatever size the model felt like, and a prop that
        # renders at the wrong size next to a person is the same defect as a room that
        # renders too small. This is the other half of Gary's 2026-08-01 ask: how tall
        # different people AND DIFFERENT THINGS are.
        for ef in sorted(ents_dir.glob("*.json")):
            e = jload(ef) or {}
            if e.get("kind") != "prop":
                continue
            eid = e.get("id", ef.stem)
            st = e.get("structured") or {}
            sc = st.get("scale") or {}
            if not (sc.get("size") or sc.get("height") or "").strip():
                warn("PROP-NO-SCALE",
                     f"{eid}: no structured.scale size descriptor, so nothing states how big "
                     f"this object is and it will render at whatever size the model assumes "
                     f"next to a figure. State it in human terms (\"about 40 mm across, worn "
                     f"at the collarbone\").")

    # ---- A SETTING'S DRESSING IS THE ROOM, NEVER WHAT A PERSON IS HOLDING (v0.29)
    #
    # A setting is REUSABLE by design: that is the whole reason canon holds it once. But
    # `contract.dressing` is injected into every prompt that casts the setting, in every
    # book, forever, and `contract.blockingPlate` is passed as a REFERENCE IMAGE on every
    # one of those renders regardless of which camera plate was selected. So a prop that
    # belongs to ONE book, written into either of them, leaks into every book after it.
    #
    # Earned 2026-08-02. `the-park-bench` was authored for will-there-be-ice-cream: its
    # `dressing` said "Each of them holds an ice cream cone" and its blocking plate showed
    # two mannequins holding cones. Three of the first seven spreads of an unrelated book
    # came back with both men holding ice cream, through scene text AND a per-spread
    # negative that banned ice cream BY NAME on every one of them. A reference image plus
    # an injected contract sentence together outrank a negative word, every time.
    #
    # The durable fix is to move the prop to the spread's scene text and reshoot the plate
    # propless. The escape hatch for the spread in front of you is `"blockingPlate": false`
    # on the cast entry, or `contract.plates.<plate>.includeBlockingPlate: false`.
    # THE DETECTOR IS THE PART THAT FAILS (SPEC 4.6 says this about the compiler's
    # conditional guards, and it is just as true here). Two rules keep it honest, both
    # measured against nation-of-fire's 144 settings:
    #
    #   1. Both halves must appear in the SAME SENTENCE. Scanning the whole field
    #      matched "continuity holds" in one sentence against "people" in another and
    #      flagged a quarter of every setting in the universe.
    #   2. The verb must take a CONCRETE OBJECT (an article or possessive then a noun).
    #      "the SAME framing hold" and "carries the warm sunset-gold" are the metaphors
    #      that survive rule 1, and an object test drops most of them.
    #
    # It still lets some noise through, which is the right trade for a warning: the
    # alternative version, tuned until it was silent on everything questionable, was
    # also silent on `the-park-bench`, the entity that earned the check.
    HELD = re.compile(
        r"\b(hold|holds|holding|carr(?:y|ies|ying)|clutch(?:es|ing)?|grip(?:s|ping)?|"
        r"sip(?:s|ping)?|eat(?:s|ing)?|drink(?:s|ing)?|wear(?:s|ing)?)\s+"
        r"(?:a|an|the|his|her|their|its|one|two|some)\s+\w", re.I)
    PERSON = re.compile(
        r"\b(each of them|they|them|he|she|his|her|their|someone|person|people|man|men|"
        r"woman|women|figure|figures|customer|customers|guest|guests|patron|patrons|"
        r"child|children)\b", re.I)
    if ents_dir.exists():
        for ef in sorted(ents_dir.glob("*.json")):
            e = jload(ef) or {}
            if e.get("kind") not in ("setting", "visual-metaphor"):
                continue
            eid = e.get("id", ef.stem)
            con = e.get("contract") or {}
            for field in ("dressing", "blocking"):
                txt = con.get(field)
                if not isinstance(txt, str) or not txt.strip():
                    continue
                hit = next((s for s in re.split(r"(?<=[.;!?])\s+", txt)
                            if HELD.search(s) and PERSON.search(s)), None)
                if hit:
                    warn("SETTING-DRESSING-NAMES-HELD-PROP",
                         f"{eid}: contract.{field} says {HELD.search(hit).group(0).strip()!r} "
                         f"of a person, in \"{hit.strip()[:90]}\". A setting's "
                         f"contract rides on EVERY render of it in EVERY book, so a prop belonging "
                         f"to one story leaks into every story that reuses the place, and a "
                         f"per-spread negative cannot win against it. Move the prop to the "
                         f"spread's scene text. If contract.blockingPlate also depicts it, reshoot "
                         f"the plate propless or scope it out per spread with "
                         f"`\"blockingPlate\": false` on the cast entry.")

    # ---- `structured.render.qa` MUST NOT BE THE ONLY GUARD ON AN ENTITY (v0.29)
    #
    # `render.qa` is now compiled into the read-back checklist (SPEC 4.6, implemented at
    # last in v0.29), so it is no longer inert. `structured.invariants` is still the field
    # every OTHER gate reads: the identity bake guard, auto-disambiguation between two
    # people in one frame, `supersedes` on a look or a pose, and `judge-slot`. An entity
    # with a populated `render.qa` and an EMPTY `invariants` therefore looks guarded and
    # is guarded in exactly one of five places.
    #
    # Earned on `theo-doorchaser` (The Tithe Is a Test, 2026-08-02): six well-written qa
    # items, zero invariants, and a dry assemble reported ZERO checks on the spread where
    # he stands alone. His half-on jacket was the spine of the book.
    if ents_dir.exists():
        for ef in sorted(ents_dir.glob("*.json")):
            e = jload(ef) or {}
            st = e.get("structured") or {}
            qa = (st.get("render") or {}).get("qa") or []
            if qa and not (st.get("invariants") or []):
                warn("ENTITY-QA-WITHOUT-INVARIANTS",
                     f"{e.get('id', ef.stem)}: declares {len(qa)} structured.render.qa item(s) "
                     f"and NO structured.invariants. `invariants` is what the identity bake "
                     f"guard, auto-disambiguation, `supersedes` and judge-slot all read, so this "
                     f"entity is guarded in one place out of five. State the checkable facts as "
                     f"invariants; keep render.qa for what only a reader can judge.")

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

            # ---- ABSOLUTE HEIGHT (SPEC v0.21)
            #
            # `relativeTo` above answers "is he taller than her". It cannot answer "how
            # tall is he", and neither can `scale.height`, which is prose that no plate
            # depicts. A solo forward-fullbody on a blank ground carries no unit of
            # comparison, so the model picks a stature and every render inherits it.
            # This is v0.9's setting lesson (a plate cannot be judged on a dimension it
            # does not depict) finally applied to people.
            sc = st.get("scale") or {}
            declared_h = (sc.get("height") or "").strip()
            plate = (st.get("sheets") or {}).get("scale-plate")
            if plate and not (root/plate).exists():
                warn("CHARACTER-SCALE-PLATE-MISSING",
                     f"{eid}: sheets['scale-plate'] -> {plate} (NOT ON DISK)")
            elif declared_h and not plate:
                warn("CHARACTER-HEIGHT-UNDEPICTED",
                     f"{eid}: declares scale.height '{declared_h}' but has no 'scale-plate' "
                     f"sheet, so nothing on disk depicts the dimension the record asserts. "
                     f"Shoot a solo head-to-toe plate against a measured reference.")
            elif not declared_h and not plate:
                warn("CHARACTER-NO-SCALE-PLATE",
                     f"{eid}: no scale.height and no 'scale-plate' sheet, so nothing states or "
                     f"proves how tall this character is and every render silently inherits the "
                     f"model's guess. Declare structured.scale.height and shoot a scale-plate.")

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

            # ---- VARIANT VALIDITY WINDOWS (SPEC v0.18)
            #
            # A `validFor` window lets compose-spread refuse a wrong-era selection
            # BEFORE it spends. What lint can see that the compiler cannot is the
            # shape of the whole variant SET, and the dangerous shape is a PARTIAL
            # one: if the default look and two of three alt looks declare a window
            # and one does not, the undeclared one is legal at every date, so the
            # gate silently has a hole exactly where someone thought they had closed
            # it. A set with no windows at all is fine and is the default.
            variants = {None: {"validFor": st.get("validFor")}}
            variants.update({k: (v or {}) for k, v in (st.get("altLooks") or {}).items()})
            _lint_windows(eid, "look", variants)

    # a setting's era axis is its PLATES, which carry the window in contract.plates
    if ents_dir.exists():
        for ef in sorted(ents_dir.glob("*.json")):
            e = jload(ef) or {}
            if e.get("kind") not in ("setting", "visual-metaphor"):
                continue
            con = e.get("contract") or (e.get("structured") or {}).get("contract") or {}
            plates = {k: (v or {}) for k, v in (con.get("plates") or {}).items()}
            for p in con.get("emptyPlates") or []:
                if isinstance(p, str):
                    plates.setdefault(pathlib.Path(p).stem, {})
            if plates:
                _lint_windows(e.get("id") or ef.stem, "plate", plates)

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
            for sf in story_files(stories_dir):
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
        for r in (p.get("refs") or []):
            if not (d/r).exists(): err("PACK-REF-MISSING", f"{pj}: ref {r} missing")
        if not p.get("gate"): err("PACK-NO-GATE", f"{pj}: no gate; a pack without one is a mood board")
        if not p.get("styleLine"): err("PACK-NO-STYLELINE", f"{pj}: no styleLine")
        n = len(p.get("refs") or [])
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
        # `structured.sheetAliases: {newKey: oldKey}` declares an INTENTIONAL alias
        # (the add-keys-never-remove rename pattern: retired-hearthRotunda precedent;
        # the-park-bench / apostle-lee-study camera aliases, 2026-08-02). A declared
        # alias is exempt from the dead-duplicate warning; an UNDECLARED duplicate
        # still warns, and requiredForRender naming two keys for one file is still an
        # error either way, because the same image passed twice carries no information
        # regardless of intent.
        aliases = st.get("sheetAliases") or {}
        if not isinstance(aliases, dict):
            aliases = {}
        seen = {}
        for k, v in sheets.items():
            if not v: continue
            seen.setdefault(v, []).append(k)
        for path, keys in seen.items():
            if len(keys) > 1:
                req = [k for k in (st.get("requiredForRender") or []) if k in keys]
                declared = {k for k in keys if aliases.get(k) in keys and aliases.get(k) != k}
                undeclared = [k for k in keys if k not in declared]
                if len(req) > 1:
                    err("SHEET-DUPLICATE-ALIAS",
                        f"{ej.name}: sheet keys {sorted(keys)} all point at '{path}'; "
                        f"requiredForRender names {sorted(req)}, so the same image is passed "
                        f"{len(req)} times and one of them carries no information.")
                elif len(undeclared) > 1:
                    warn("SHEET-DUPLICATE-ALIAS",
                         f"{ej.name}: sheet keys {sorted(undeclared)} all point at '{path}'; "
                         f"one is a dead alias. If the duplicate is INTENTIONAL (a renamed "
                         f"key kept for back-compat), declare it: "
                         f"structured.sheetAliases = {{\"<newKey>\": \"<oldKey>\"}}.")
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

        for inv in (st.get("invariants") or []):
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
            for key in (pose.get("sheets") or []):
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
        for name in (st.get("requiredForRender") or []):
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
            # `or []` and not just a default: an explicit `"inputs": null` in a recipe
            # returns None from .get, and iterating that kills the whole linter on a real
            # universe. This is the SECOND crash from this one line (see the note below on
            # bare-string inputs), which is why the guard is now belt and braces.
            for inp in (rec.get("inputs") or []):
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


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    lint(root)
    for c,m in E: print(f"  ERROR  [{c}] {m}")
    for c,m in W: print(f"  warn   [{c}] {m}")
    print(f"\n{len(E)} error(s), {len(W)} warning(s)")
    return 2 if E else (1 if W else 0)

if __name__ == "__main__":
    sys.exit(main())
