"""
Agentic Story — core model.

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
SETTING_CONTRACT_FIELDS = ("turnaround", "emptyPlates", "blueprint", "scalePlate", "map", "blocking", "dressing", "scale")


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
        # Consumption decides structure: an entity a renderer draws needs sheets + requiredForRender.
        if self.kind == "character":
            if not (self.structured.get("sheets")):
                p.append(f"{self.id}: character has no structured.sheets (renderer-consumed → must be structured)")
            for k in self.required_sheet_keys():
                if not self.sheet_path(k):
                    p.append(f"{self.id}: requiredForRender '{k}' has no path in sheets")
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
class ProjectionType:
    """SPEC §4.8 — a typed contract for a KIND of deliverable.

    Specified since v0.11 and never implemented, which is why a layered parallax scene
    got hand-rolled as a bespoke primitive instead of being expressed as what it is.
    `requires` names KINDS, never ids: that is the whole mechanism that lets a projection
    ship to a brand it has never seen.
    """
    id: str
    raw: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "ProjectionType":
        return ProjectionType(id=d.get("id", ""), raw=d)

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
            p.append("projection missing 'id'")
        if not self.version:
            p.append(f"{self.id}: no 'version' (a projection is a distributable artifact, so it is versioned)")
        if not self.raw.get("surface"):
            p.append(f"{self.id}: no 'surface' (a projection declares the medium it targets)")
        if not self.slots:
            p.append(f"{self.id}: no 'slots' (a projection with nothing to fill emits nothing)")
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
class ProjectionInstance:
    """SPEC §4.9 — ONE instance of a projection.

    Validation that needs the projection in hand (do the bound kinds satisfy `requires`,
    does every filled slot exist) lives in the store, which can resolve the reference.
    """
    id: str
    raw: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "ProjectionInstance":
        return ProjectionInstance(id=d.get("id", ""), raw=d)

    @property
    def projection(self) -> str:
        return self.raw.get("projection", "")

    @property
    def slots(self) -> dict[str, Any]:
        return dict(self.raw.get("slots", {}) or {})

    @property
    def bind(self) -> dict[str, Any]:
        return dict(self.raw.get("bind", {}) or {})

    def validate(self) -> list[str]:
        p: list[str] = []
        if not self.id:
            p.append("instance missing 'id'")
        if not self.projection:
            p.append(f"{self.id}: no 'projection' (a instance is an instance OF something)")
        elif "@" not in self.projection:
            p.append(f"{self.id}: projection '{self.projection}' is unpinned; use 'id@version'")
        if not self.slots:
            p.append(f"{self.id}: fills no slots")
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
