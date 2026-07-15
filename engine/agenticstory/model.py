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
SETTING_CONTRACT_FIELDS = ("turnaround", "emptyPlates", "blueprint", "map", "blocking", "dressing")


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

    def validate(self) -> list[str]:
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
            if (rp.get("approval") or {}).get("state") not in ("gated", "approved"):
                p.append(f"{self.id}: realPerson.approval.state must be 'gated' or 'approved'")
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

    def validate(self) -> list[str]:
        """Structural validation only (no filesystem). Load-bearing asset + setting
        checks live in refs.assert_story, which needs the canon store + disk."""
        p: list[str] = []
        if not self.id:
            p.append("story missing 'id'")
        if not self.raw.get("spine"):
            p.append(f"{self.id}: no declared spine (every story declares its arc invariant)")
        if not self.features:
            p.append(f"{self.id}: no features (a story selects canon entities)")
        if not self.beats:
            p.append(f"{self.id}: no beats")
        for i, b in enumerate(self.beats, 1):
            if not b.get("provenance"):
                p.append(f"{self.id}: beat {b.get('n', i)} has no provenance (every beat traces to a source)")
        return p
