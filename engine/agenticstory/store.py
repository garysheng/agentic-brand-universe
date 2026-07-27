"""
Agentic Story — canon store.

Loads a universe directory into a queryable in-memory graph of entities and
relations. A universe is:

    <universe>/
      universe.json                 # { "name", "assetRoot" }  assetRoot is where entity asset paths resolve
      canon/entities/*.json         # one Entity per file
      canon/relations/*.json        # one Relation per file (or a list)
      stories/*.json                # StorySpec per file

Stdlib only.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model import CraftCanon, Entity, Generator, Relation, StorySpec


class CanonStore:
    def __init__(self, universe_dir: str | Path):
        self.dir = Path(universe_dir).resolve()
        self.manifest: dict[str, Any] = {}
        self.entities: dict[str, Entity] = {}
        self.relations: list[Relation] = []
        self.stories: dict[str, StorySpec] = {}
        self.craft: dict[str, CraftCanon] = {}
        self.generators: dict[str, Generator] = {}
        self._load()

    def _load(self) -> None:
        man = self.dir / "universe.json"
        if not man.exists():
            raise FileNotFoundError(f"no universe.json in {self.dir}")
        self.manifest = json.loads(man.read_text())
        for f in sorted((self.dir / "canon" / "entities").glob("*.json")):
            e = Entity.from_dict(json.loads(f.read_text()))
            self.entities[e.id] = e
        craft_dir = self.dir / "canon" / "craft"
        if craft_dir.exists():
            for f in sorted(craft_dir.glob("*.json")):
                c = CraftCanon.from_dict(json.loads(f.read_text()))
                self.craft[c.id] = c
        gen_dir = self.dir / "generators"
        if gen_dir.is_dir():
            for f in sorted(gen_dir.glob("*/generator.json")):
                g = Generator.from_dict(json.loads(f.read_text()))
                self.generators[g.id] = g

        rel_dir = self.dir / "canon" / "relations"
        if rel_dir.exists():
            for f in sorted(rel_dir.glob("*.json")):
                data = json.loads(f.read_text())
                for d in (data if isinstance(data, list) else [data]):
                    self.relations.append(Relation.from_dict(d))
        st_dir = self.dir / "stories"
        if st_dir.exists():
            for f in sorted(st_dir.glob("*.json")):
                s = StorySpec.from_dict(json.loads(f.read_text()))
                self.stories[s.id] = s

    @property
    def asset_root(self) -> Path:
        """Where entity asset paths resolve. Relative assetRoot is relative to the universe dir."""
        ar = self.manifest.get("assetRoot", ".")
        p = Path(ar)
        return p if p.is_absolute() else (self.dir / p).resolve()

    @property
    def subject_approval(self) -> str | None:
        """The universe's real-living-person approval policy, or None if it declares none.

        'none-required' means the per-subject blessing gate is abolished universe-wide and
        entity validation must not demand an approval state (see Entity.validate).
        """
        identity = self.manifest.get("identity") or {}
        return (identity.get("subjectApproval") or {}).get("realLivingPerson")

    # --- queries ---
    def entity(self, eid: str) -> Entity | None:
        return self.entities.get(eid)

    def crossovers(self, eid: str) -> list[Relation]:
        return [r for r in self.relations if eid in (r.from_, r.to) and r.rel == "crossover-with"]

    def relations_of(self, eid: str) -> list[Relation]:
        return [r for r in self.relations if eid in (r.from_, r.to)]

    # --- validation ---
    def validate_canon(self) -> list[str]:
        problems: list[str] = []
        for e in self.entities.values():
            problems += e.validate(subject_approval=self.subject_approval)
        for c in self.craft.values():
            problems += c.validate()
        # a relation side may be an entity OR a story (e.g. `wisp appears-in <story>`)
        known = set(self.entities) | set(self.stories)
        for r in self.relations:
            problems += r.validate()
            for side in (r.from_, r.to):
                if side and side not in known:
                    problems.append(f"relation references unknown id '{side}' ({r.rel})")
        for s in self.stories.values():
            problems += s.validate()
            for fid in s.features:
                if fid not in known:
                    problems.append(f"story '{s.id}' features unknown entity '{fid}'")
        for g in self.generators.values():
            problems += g.validate()
        problems += self._validate_generators()
        problems += self._validate_canon_records()
        problems += self._validate_assets()
        return problems

    ASSET_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp3", ".wav", ".m4a")

    def _validate_assets(self) -> list[str]:
        """Principle 3: a declared asset resolves to a real file under assetRoot, or it is a problem.

        Entity.validate() is deliberately filesystem-free, and refs.resolve_entity_assets()
        only walks `requiredForRender` at render time. Between them sat a gap wide enough
        that a universe could validate GREEN while eight declared paths pointed at nothing:
        a lock step that joined four shot names into one key, three slots declared on
        `status: locked` entities whose art was never generated, and two paths into
        book-folder directories a consolidation sweep had deleted. None of it was caught
        because nothing ever checked that a declared path exists.

        This also enforces 3a (self-containment): a path that resolves only OUTSIDE the
        universe fails here, because it is not under assetRoot. Cloning the universe
        alone must not break a reference.
        """
        root = self.asset_root
        problems: list[str] = []

        def check(eid: str, slot: str, val: object) -> None:
            if not isinstance(val, str) or not val:
                return
            if not val.lower().endswith(self.ASSET_SUFFIXES) and "/" not in val:
                return  # a prose field, not a path
            target = val.split("#", 1)[0]
            if not target:
                return
            p = root / target
            if not (p.exists() or p.is_dir()):
                problems.append(f"{eid}: {slot} -> {target} (NOT ON DISK under assetRoot)")
            elif not self._under_root(p, root):
                problems.append(f"{eid}: {slot} -> {target} (OUTSIDE the universe; breaks self-containment)")

        def walk(eid: str, obj: object, slot: str) -> None:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    walk(eid, v, f"{slot}.{k}")
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    walk(eid, v, f"{slot}[{i}]")
            elif isinstance(obj, str) and obj.lower().endswith(self.ASSET_SUFFIXES):
                check(eid, slot, obj)

        for e in self.entities.values():
            walk(e.id, e.structured, "structured")
            if e.raw.get("contract"):
                walk(e.id, e.raw["contract"], "contract")
            rp = e.real_person
            if rp:
                for i, ph in enumerate(rp.get("photoStack") or []):
                    if isinstance(ph, str) and ph:
                        p = root / ph.split("#", 1)[0]
                        if not (p.is_file() or p.is_dir()):
                            problems.append(
                                f"{e.id}: realPerson.photoStack[{i}] -> {ph} (NOT ON DISK under assetRoot)"
                            )
                        elif not self._under_root(p, root):
                            problems.append(
                                f"{e.id}: realPerson.photoStack[{i}] -> {ph} (OUTSIDE the universe; breaks self-containment)"
                            )
        return sorted(problems)

    @staticmethod
    def _under_root(p, root) -> bool:
        """3a: existing is not enough, it must live UNDER assetRoot.

        A `../sibling/photo.jpg` resolves fine on the authoring machine and still
        breaks the clone test, so existence alone cannot enforce self-containment.
        """
        try:
            p.resolve().relative_to(root.resolve())
            return True
        except ValueError:
            return False

    def _validate_canon_records(self) -> list[str]:
        """Duplicate crossover display numbers.

        Numbers used to be assigned by each run reading the last one and adding
        one, so two concurrent runs produced two rows with the same number on
        different lines: git merged them cleanly and nothing ever complained.
        Only checked for universes that have migrated to the record store, so
        an unmigrated universe is unaffected."""
        from . import canonfile
        if not canonfile.xover_dir(self.dir).is_dir():
            return []
        out = []
        recs = canonfile.load_crossovers(self.dir)
        for n in canonfile.duplicate_numbers(recs):
            ids = ", ".join(r["id"] for r in recs if r.get("n") == n)
            out.append(f"duplicate crossover number {n}: {ids}")
        return out


    def _validate_generators(self) -> list[str]:
        """SPEC v0.13 §4.11 disk checks: the entrypoint exists, and a declared output
        that was never written is a lie the manifest tells about itself."""
        problems: list[str] = []
        for g in self.generators.values():
            gdir = self.dir / "generators" / g.id
            entry = g.raw.get("entrypoint")
            if entry and not (gdir / entry).exists():
                problems.append(f"generator '{g.id}': entrypoint '{entry}' does not exist")
            for o in g.outputs:
                path = o.get("path") if isinstance(o, dict) else None
                if path and not (gdir / path).exists():
                    problems.append(
                        f"generator '{g.id}': declared output '{path}' has never been written "
                        f"(run the generator, or stop declaring it)")
        return problems
