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

from .model import Entity, Relation, StorySpec


class CanonStore:
    def __init__(self, universe_dir: str | Path):
        self.dir = Path(universe_dir).resolve()
        self.manifest: dict[str, Any] = {}
        self.entities: dict[str, Entity] = {}
        self.relations: list[Relation] = []
        self.stories: dict[str, StorySpec] = {}
        self._load()

    def _load(self) -> None:
        man = self.dir / "universe.json"
        if not man.exists():
            raise FileNotFoundError(f"no universe.json in {self.dir}")
        self.manifest = json.loads(man.read_text())
        for f in sorted((self.dir / "canon" / "entities").glob("*.json")):
            e = Entity.from_dict(json.loads(f.read_text()))
            self.entities[e.id] = e
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
            problems += e.validate()
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
        return problems
