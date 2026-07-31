"""
Agentic Brand Universe — core model.

Typed canon entities, relations, and story specs, with hand-rolled validation
(stdlib only, no deps — same discipline as the resolver). Validation returns a
list of human-readable problems; an empty list means valid. Nothing here touches
the filesystem — that is refs.py's job (load-bearing asset resolution).

See ../../SPEC.md for the field contracts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ENTITY_KINDS = {
    "character", "setting", "visual-metaphor", "doctrine", "motif", "beat", "prop", "group",
}

# EDITORIAL STANDING, orthogonal to `status` (reference-completeness).
# 'archived' means: do not cast this in anything NEW. It never invalidates art
# that already shipped.
ENTITY_LIFECYCLES = {"active", "archived"}
SETTING_CONTRACT_FIELDS = ("turnaround", "emptyPlates", "blueprint", "scalePlate", "map", "blocking", "dressing", "scale")


# Sheets that assert WHO the entity is rather than what it is made of. An alt look
# changes substance or era, so these are dropped by default and re-added only when the
# look explicitly names them in `keepSheets`. Without the default drop, a look inherits
# a base plate that contradicts it; without `keepSheets`, a look that changes only
# substance loses the face and the renderer invents a new person.
_IDENTITY_SHEETS = {"face-neutral", "face-neutral-color", "face-3q", "expressions"}


@dataclass
class Entity:
    id: str
    kind: str
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def structured(self) -> dict[str, Any]:
        return self.raw.get("structured", {}) or {}

    @property
    def real_person(self) -> dict[str, Any] | None:
        return self.raw.get("realPerson")

    def required_sheet_keys(self) -> list[str]:
        s = self.structured
        # SPEC v0.11: an entity may demand a stricter gate than its kind's minimum.
        # Honour it here too, so lock-level and the render gate agree with lock-shot.
        override = s.get("requiredForRenderOnLock")
        if override:
            return list(dict.fromkeys(list(override) + list(s.get("requiredForRender") or [])))
        return list(s.get("requiredForRender", list((s.get("sheets") or {}).keys())))

    def sheet_path(self, key: str) -> str | None:
        return (self.structured.get("sheets") or {}).get(key)

    def alt_look(self, look: str) -> dict[str, Any] | None:
        return ((self.structured.get("altLooks") or {}) or {}).get(look)

    def look_sheets(self, look: str | None) -> dict[str, str]:
        """The sheets a render should actually pass for this entity in this look.

        SPEC v0.10 declared `altLooks` and nothing in the engine ever read it, so
        selecting a look meant a human typing the right filename into `--ref` by
        hand. That is not a gate, it is a memory test, and it was failed live: a
        `spirit` look was rendered with only its own full-body plate and none of the
        kept face sheets, and the face drifted every time (gary-sheng-art `jesus`,
        2026-07-27). Resolution belongs here, where it cannot be forgotten.

        Composition, in order:
          1. Start from the DEFAULT look's required sheets.
          2. Drop the base face/identity sheets, because an alt look that changes
             the body should not also drag in a contradicting base plate.
          3. Add back anything named in `keepSheets` — the look declaring "this
             part of me is still the base", which is how a look that changes
             SUBSTANCE keeps the same face.
          4. Remove anything in `dropSheets`.
          5. Overlay the look's own `sheets`, which win.
        """
        s = self.structured
        base = {k: v for k in self.required_sheet_keys() if (v := self.sheet_path(k))}
        if not look:
            return base
        al = self.alt_look(look)
        if al is None:
            known = sorted((s.get("altLooks") or {}).keys())
            raise ValueError(
                f"{self.id} has no altLook {look!r}. Known looks: {known or 'none'}")

        keep = set(al.get("keepSheets") or [])
        out = {k: v for k, v in base.items()
               if k in keep or not _IDENTITY_SHEETS.intersection({k})}
        for k in keep:
            p = self.sheet_path(k)
            if p:
                out[k] = p
        for k in (al.get("dropSheets") or []):
            out.pop(k, None)
        for k, v in (al.get("sheets") or {}).items():
            if v:
                out[k] = v
        return out

    def look_invariants(self, look: str | None) -> list[str]:
        """Base invariants minus anything the look `supersedes`, plus the look's own.

        `supersedes` exists so a look can retire a base rule it contradicts (a
        being of light supersedes a skin-tone invariant) WITHOUT deleting the rule
        for every other render of the entity.
        """
        s = self.structured
        base = list(s.get("invariants") or [])
        if not look:
            return base
        al = self.alt_look(look) or {}
        dead = set(al.get("supersedes") or [])
        return [i for i in base if i not in dead] + list(al.get("invariants") or [])

    # ---- LIFECYCLE (SPEC v0.16) -------------------------------------------------
    # `status` is REFERENCE-COMPLETENESS (locked | unlocked): is the art on disk.
    # `lifecycle` is EDITORIAL STANDING (active | archived): may a NEW story cast it.
    # They are deliberately ORTHOGONAL. An archived entity is usually still fully
    # locked, and its art stays valid forever, because every book that already
    # shipped with it must keep rendering and its provenance must stay honest.
    # Conflating the two would retroactively break history, which is the one thing
    # an archive must never do.

    @property
    def lifecycle(self) -> str:
        v = self.raw.get("lifecycle")
        return v if v in ENTITY_LIFECYCLES else "active"

    @property
    def is_archived(self) -> bool:
        return self.lifecycle == "archived"

    @property
    def superseded_by(self) -> str | None:
        return ((self.raw.get("archived") or {}).get("supersededBy")) or None

    def archive_note(self) -> str:
        """One line an author can act on: why it was retired and what to cast instead."""
        a = self.raw.get("archived") or {}
        bits = [f"'{self.id}' is ARCHIVED"]
        if a.get("on"):
            bits.append(f"on {a['on']}")
        if a.get("reason"):
            bits.append(f"({a['reason']})")
        if a.get("supersededBy"):
            bits.append(f"-> cast '{a['supersededBy']}' instead")
        return " ".join(bits)

    def is_locked_setting(self) -> bool:
        """A setting/visual-metaphor is locked only when every contract field is present."""
        if self.kind not in ("setting", "visual-metaphor"):
            return True
        if self.raw.get("status") != "locked":
            return False
        contract = self.raw.get("contract", {}) or {}
        for f in SETTING_CONTRACT_FIELDS:
            v = contract.get(f)
            if v in (None, "") or (f == "emptyPlates" and not v):
                return False
        return True

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Entity":
        return Entity(id=d.get("id", ""), kind=d.get("kind", ""), raw=d)

    def validate(self, subject_approval: str | None = None) -> list[str]:
        """Validate the entity.

        `subject_approval` is the universe's identity.subjectApproval.realLivingPerson policy.
        When a universe sets it to 'none-required' the per-subject blessing gate is abolished
        outright, so a real-person entity is NOT required to declare an approval state at all.
        """
        p: list[str] = []
        if not self.id:
            p.append("entity missing 'id'")
        if self.kind not in ENTITY_KINDS:
            p.append(f"{self.id}: unknown kind '{self.kind}' (allowed: {sorted(ENTITY_KINDS)})")
        lc = self.raw.get("lifecycle")
        if lc is not None and lc not in ENTITY_LIFECYCLES:
            p.append(f"{self.id}: unknown lifecycle '{lc}' (allowed: {sorted(ENTITY_LIFECYCLES)})")
        if self.is_archived:
            a = self.raw.get("archived")
            if not isinstance(a, dict) or not (a.get("on") and a.get("reason")):
                p.append(
                    f"{self.id}: an archived entity needs an 'archived' block with 'on' and "
                    f"'reason' (an archive with no recorded reason is unauditable)"
                )
        # Consumption decides structure: an entity a renderer draws needs sheets + requiredForRender.
        if self.kind == "character":
            if not (self.structured.get("sheets")):
                p.append(f"{self.id}: character has no structured.sheets (renderer-consumed → must be structured)")
            for k in self.required_sheet_keys():
                if not self.sheet_path(k):
                    p.append(f"{self.id}: requiredForRender '{k}' has no path in sheets")
        # structured.render is PROMPT-CRAFT and it is what actually steers the model, so a
        # malformed one is worse than a missing one: nothing here refused it before, and the
        # first thing that read it was the spread assembler, at render time, with an
        # AttributeError. Earned on knowledge-shall-increase 2026-07-30, where four characters
        # were authored with `poses: {name: "a sentence"}` and every spread casting them
        # refused mid-batch. The shape is poses.<key> = {"bake": str, "sheets": [str]}.
        render = self.structured.get("render")
        if render is not None:
            if not isinstance(render, dict):
                p.append(f"{self.id}: structured.render must be an object")
            else:
                if "always" in render and not isinstance(render["always"], str):
                    p.append(f"{self.id}: structured.render.always must be a string")
                poses = render.get("poses")
                if poses is not None:
                    if not isinstance(poses, dict):
                        p.append(f"{self.id}: structured.render.poses must be an object")
                    else:
                        for key, pose in poses.items():
                            if not isinstance(pose, dict):
                                p.append(
                                    f"{self.id}: structured.render.poses['{key}'] must be an "
                                    f"object with optional 'bake' and 'sheets', not "
                                    f"{type(pose).__name__} (a bare string passes validate and "
                                    f"then crashes the spread assembler)"
                                )
                                continue
                            if "bake" in pose and not isinstance(pose["bake"], str):
                                p.append(f"{self.id}: render.poses['{key}'].bake must be a string")
                            sheets = pose.get("sheets")
                            if sheets is not None:
                                if not isinstance(sheets, list):
                                    p.append(f"{self.id}: render.poses['{key}'].sheets must be a list")
                                else:
                                    for sk in sheets:
                                        if sk not in (self.structured.get("sheets") or {}):
                                            p.append(
                                                f"{self.id}: render.poses['{key}'] names sheet "
                                                f"'{sk}' which is not in structured.sheets"
                                            )
        if self.kind in ("setting", "visual-metaphor"):
            if "status" not in self.raw:
                p.append(f"{self.id}: {self.kind} needs a 'status' (locked|unlocked)")
            if "contract" not in self.raw:
                p.append(f"{self.id}: {self.kind} needs a 'contract' block")
        rp = self.real_person
        if rp is not None:
            if not rp.get("photoStack"):
                p.append(f"{self.id}: realPerson needs a non-empty photoStack (multi-ref rule)")
            # APPROVAL IS POLICY-DRIVEN (2026-07-25). A universe that declares
            # identity.subjectApproval.realLivingPerson = 'none-required' has abolished the
            # per-subject blessing gate (nation-of-fire did so on 2026-07-24), so there is
            # nothing to enforce here: no approval block is needed, and 'none-required' is a
            # legal explicit value. Demanding 'gated' or 'approved' under that policy forced a
            # dishonest choice, since 'approved' asserts a blessing nobody ever asked for and
            # 'gated' reinstates the very gate the universe retired.
            if subject_approval != "none-required":
                if (rp.get("approval") or {}).get("state") not in ("gated", "approved", "none-required"):
                    p.append(
                        f"{self.id}: realPerson.approval.state must be "
                        f"'gated', 'approved', or 'none-required'"
                    )
        return p


CRAFT_KINDS = {"spine", "genre", "register-rule"}


@dataclass
class CraftCanon:
    """A typed craft-canon record: a spine, a genre, or a register-rule the
    renderer honors. Craft is data, not skill prose (SPEC §11, §13)."""
    id: str
    kind: str
    raw: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "CraftCanon":
        return CraftCanon(id=d.get("id", ""), kind=d.get("kind", ""), raw=d)

    def validate(self) -> list[str]:
        p: list[str] = []
        if not self.id:
            p.append("craft record missing 'id'")
        if self.kind not in CRAFT_KINDS:
            p.append(f"{self.id}: unknown craft kind '{self.kind}' (allowed: {sorted(CRAFT_KINDS)})")
        if not (self.raw.get("rules") or self.raw.get("summary")):
            p.append(f"{self.id}: craft record needs a 'rules' or 'summary'")
        return p


@dataclass
class Relation:
    from_: str
    rel: str
    to: str
    raw: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Relation":
        return Relation(from_=d.get("from", ""), rel=d.get("rel", ""), to=d.get("to", ""), raw=d)

    def validate(self) -> list[str]:
        p: list[str] = []
        for f in ("from", "rel", "to"):
            if not self.raw.get(f):
                p.append(f"relation missing '{f}': {self.raw}")
        return p


@dataclass
class StorySpec:
    id: str
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def features(self) -> list[str]:
        return list(self.raw.get("features", []))

    @property
    def beats(self) -> list[dict[str, Any]]:
        return list(self.raw.get("beats", []))

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "StorySpec":
        return StorySpec(id=d.get("id", ""), raw=d)

    @property
    def status(self) -> str:
        return self.raw.get("status", "full")  # "stub" = registered but not yet fully migrated

    def validate(self) -> list[str]:
        """Structural validation only (no filesystem). Load-bearing asset + setting
        checks live in refs.assert_story, which needs the canon store + disk.
        A 'stub' story is a registered placeholder (title + spine) and is exempt
        from the features/beats/provenance requirements until it is filled in."""
        p: list[str] = []
        if not self.id:
            p.append("story missing 'id'")
        if not self.raw.get("spine"):
            p.append(f"{self.id}: no declared spine (every story declares its arc invariant)")
        if self.status == "stub":
            return p
        if not self.features:
            p.append(f"{self.id}: no features (a story selects canon entities)")
        if not self.beats:
            p.append(f"{self.id}: no beats")
        for i, b in enumerate(self.beats, 1):
            if not b.get("provenance"):
                p.append(f"{self.id}: beat {b.get('n', i)} has no provenance (every beat traces to a source)")
        return p


@dataclass
class Form:
    """RETIRED encoding (SPEC §4.8) — a form: what makes a work the KIND of thing it is.

    The CONCEPT survives; this specific encoding does not. It was retired in v0.17 having
    produced zero works, and §4.8 records that rather than specifying a live contract. The
    class is kept so a universe written against v0.6-v0.16 still loads and typechecks.

    Canon is the matter; a form is what shapes it; a Work (§4.9) is canon given form. The
    form names a surface, requires kinds, declares the slots to be filled and the
    invariants that must hold, and emits files.

    `requires` names KINDS, never ids. That is the whole mechanism that lets a form ship
    to a brand it has never seen, and it is enforced below rather than documented.

    Formerly `Projection`, then `ProjectionType`. A form is not a projection: it is what a
    projection happens THROUGH. Projection survives as the relationship canon bears to a
    work, which is the one job that word does correctly.
    """
    id: str
    raw: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Form":
        return Form(id=d.get("id", ""), raw=d)

    @property
    def version(self) -> str:
        return self.raw.get("version", "")

    @property
    def ref(self) -> str:
        return f"{self.id}@{self.version}"

    @property
    def slots(self) -> list[dict[str, Any]]:
        return list(self.raw.get("slots", []))

    @property
    def requires(self) -> list[dict[str, Any]]:
        return list(self.raw.get("requires", []))

    def validate(self) -> list[str]:
        p: list[str] = []
        if not self.id:
            p.append("form missing 'id'")
        if not self.version:
            p.append(f"{self.id}: no 'version' (a form is a distributable artifact, so it is versioned)")
        if not self.raw.get("surface"):
            p.append(f"{self.id}: no 'surface' (a form declares the medium it targets)")
        if not self.slots:
            p.append(f"{self.id}: no 'slots' (a form with nothing to fill emits nothing)")
        for i, s in enumerate(self.slots, 1):
            if not isinstance(s, dict) or not s.get("id"):
                p.append(f"{self.id}: slot {i} has no 'id'")
        # `requires` is what makes it portable. Naming an id here silently welds the
        # projection to one universe and it stops being distributable at all.
        for r in self.requires:
            if not isinstance(r, dict) or not r.get("kind"):
                p.append(f"{self.id}: a 'requires' entry names no kind")
            elif r.get("id"):
                p.append(
                    f"{self.id}: requires names id '{r['id']}'. A projection requires KINDS; "
                    "the instance binds ids (§4.8)."
                )
        if not self.raw.get("emits"):
            p.append(f"{self.id}: no 'emits' (nothing declares what this produces)")
        inv = self.raw.get("invariants") or {}
        for scope in ("perSlot", "crossSlot"):
            for j, c in enumerate(inv.get(scope, []) or [], 1):
                if not isinstance(c, dict) or not c.get("id"):
                    p.append(f"{self.id}: {scope} invariant {j} has no 'id'")
                elif c.get("check") not in ("judged", "computed"):
                    p.append(f"{self.id}: invariant '{c['id']}' check must be 'judged' or 'computed'")
        return p


@dataclass
class Work:
    """RETIRED encoding (SPEC §4.9) — a work: canon given form.

    As with Form above, the concept survives and this encoding does not; the class is kept
    for backward compatibility. Note that a StorySpec is NOT a Work whose form is
    storybook: that migration was recorded as done in v0.6 and never happened, so §4.3
    stays canonical for stories.

    Not an "instance", which is why it stopped being called one. A book's identity is not
    derived from being an instance of a book-shaped thing: a work carries AUTHORSHIP that
    exists in neither the canon nor the form. `beats` and `spine` are new facts about the
    world, and §4.9's `writesBack` lets a work add to canon outright — which is also the
    proof that a work is not literally a projection of the universe, since a shadow does
    not change the object.

    Validation that needs the form in hand (do the bound kinds satisfy `requires`, does
    every filled slot exist) lives in the store, which can resolve the reference.
    """
    id: str
    raw: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Work":
        return Work(id=d.get("id", ""), raw=d)

    @property
    def form(self) -> str:
        """The form this work is made in, as `id@version`. Reads `form`, falling back to
        the pre-0.14 `projection` key so a universe written against the old name still
        loads rather than silently presenting as formless."""
        return self.raw.get("form", self.raw.get("projection", ""))

    @property
    def slots(self) -> dict[str, Any]:
        return dict(self.raw.get("slots", {}) or {})

    @property
    def bind(self) -> dict[str, Any]:
        return dict(self.raw.get("bind", {}) or {})

    def validate(self) -> list[str]:
        """Structural checks only.

        This used to REQUIRE a pinned `form@version` and non-empty `slots`, which is the
        SPEC §4.8/§4.9 encoding retired in v0.17. The prose retired everywhere (SPEC, the
        linter's 136-line form section, README, ARCHITECTURE) and this enforcement was
        left behind, so the engine went on demanding a contract the standard no longer
        makes. A work authored against the current, deliberately-unwritten model failed
        validation for not filling slots that no longer exist.

        A form is still a real idea and a work may still declare one. It is simply no
        longer mandatory, and there is nothing to pin it to while the replacement is
        unwritten: `forms/event-flyer/` carries no version because it carries no schema.
        """
        p: list[str] = []
        if not self.id:
            p.append("work missing 'id'")
        return p


@dataclass
class Generator:
    """SPEC v0.13 §4.11 — a deterministic generator: code that DRAWS an asset.

    Structural validation only, filesystem-free, matching every other model here.
    Disk checks (entrypoint exists, declared outputs were actually written) live in
    the store, which has a root to resolve against.
    """
    id: str
    raw: dict[str, Any] = field(default_factory=dict)

    DETERMINISM = ("pure", "seeded")

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Generator":
        return Generator(id=d.get("id", ""), raw=d)

    @property
    def determinism(self) -> str:
        return self.raw.get("determinism", "")

    @property
    def outputs(self) -> list[dict[str, Any]]:
        return list(self.raw.get("outputs", []))

    @property
    def install(self) -> dict[str, Any]:
        return dict(self.raw.get("install", {}) or {})

    def validate(self) -> list[str]:
        p: list[str] = []
        if not self.id:
            p.append("generator missing 'id'")
        if self.raw.get("kind") != "generator":
            p.append(f"{self.id}: kind must be 'generator'")
        if not self.raw.get("entrypoint"):
            p.append(f"{self.id}: no 'entrypoint' (the program that draws the asset)")
        det = self.determinism
        if det not in self.DETERMINISM:
            p.append(f"{self.id}: determinism must be one of {self.DETERMINISM}, got '{det}'")
        # A seeded generator whose seed lives in the code is not reproducible by anyone
        # reading the manifest, which is the whole point of declaring determinism.
        if det == "seeded" and self.raw.get("seed") is None:
            p.append(f"{self.id}: determinism 'seeded' requires a 'seed' in the manifest, not in the code")
        if not self.outputs:
            p.append(f"{self.id}: declares no outputs (a generator that writes nothing is not one)")
        for i, o in enumerate(self.outputs, 1):
            if not isinstance(o, dict) or not o.get("path"):
                p.append(f"{self.id}: output {i} has no 'path'")
        # params are the contract with the artifact; a generator with none is hiding its knobs
        if not isinstance(self.raw.get("params", {}), dict):
            p.append(f"{self.id}: 'params' must be an object")
        declared = {o.get("path") for o in self.outputs if isinstance(o, dict)}
        for src in self.install:
            if src not in declared:
                p.append(f"{self.id}: install maps '{src}', which is not a declared output")
        return p
