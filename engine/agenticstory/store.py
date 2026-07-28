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

from .model import CraftCanon, Entity, Generator, ProjectionInstance, ProjectionType, Relation, StorySpec


class CanonStore:
    def __init__(self, universe_dir: str | Path):
        self.dir = Path(universe_dir).resolve()
        self.manifest: dict[str, Any] = {}
        self.entities: dict[str, Entity] = {}
        self.relations: list[Relation] = []
        self.stories: dict[str, StorySpec] = {}
        self.craft: dict[str, CraftCanon] = {}
        self.generators: dict[str, Generator] = {}
        self.projections: dict[str, ProjectionType] = {}
        self.instances: dict[str, ProjectionInstance] = {}
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

        # Projections may be local to the universe OR vendored from a registry; both are
        # keyed by `id@version`, because a universe may legitimately hold two versions
        # of one projection while an instance is mid-migration between them.
        proj_dir = self.dir / "projections"
        if proj_dir.is_dir():
            for f in sorted(proj_dir.glob("*/projection.json")):
                pr = ProjectionType.from_dict(json.loads(f.read_text()))
                self.projections[pr.ref] = pr
        inst_dir = self.dir / "instances"
        if inst_dir.is_dir():
            for f in sorted(inst_dir.glob("*/instance.json")):
                c = ProjectionInstance.from_dict(json.loads(f.read_text()))
                self.instances[c.id] = c

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
        for pr in self.projections.values():
            problems += pr.validate()
        for c in self.instances.values():
            problems += c.validate()
        problems += self._validate_instances()
        problems += self._validate_generators()
        problems += self._validate_canon_records()
        problems += self._validate_assets()
        return problems

    def _validate_instances(self) -> list[str]:
        """SPEC §4.8/§4.9 — does this instance actually satisfy the contract it claims?

        Three checks the instance cannot make about itself, because they need the
        projection resolved: the projection exists at the pinned version, every filled
        slot is a declared slot, and the COMPUTED cross-slot invariants hold.

        Judged invariants are not run here. Judgement is the Gate's job (§4.10), and
        the whole point of splitting Composer / Compiler / Gate is that the store does
        not quietly become a renderer.
        """
        problems: list[str] = []
        for c in self.instances.values():
            pr = self.projections.get(c.projection)
            if pr is None:
                if c.projection:
                    have = ", ".join(sorted(self.projections)) or "none"
                    problems.append(
                        f"instance '{c.id}': projection '{c.projection}' not found (have: {have})"
                    )
                continue
            declared = {s.get("id") for s in pr.slots}
            for name in c.slots:
                if name not in declared:
                    problems.append(
                        f"instance '{c.id}': fills slot '{name}', which {pr.ref} does not declare"
                    )
            # `requires` names kinds; the instance binds ids. An unbound requirement is
            # the failure this whole split exists to catch.
            for r in pr.requires:
                kind = r.get("kind")
                bound = c.bind.get(kind)
                n = len(bound) if isinstance(bound, list) else (1 if bound else 0)
                if n < int(r.get("min", 0)):
                    problems.append(
                        f"instance '{c.id}': {pr.ref} requires >={r.get('min')} of kind "
                        f"'{kind}', bound {n}"
                    )
            problems += self._computed_invariants(c, pr)
        return problems

    def _computed_invariants(self, c: ProjectionInstance, pr: ProjectionType) -> list[str]:
        """Evaluate the projection's computed invariants against the instance's slots.

        A generic engine cannot run a check it knows only by NAME, so a computed invariant
        carries a `rule` the engine evaluates as data. Three ops turn out to cover the
        cases so far, and each one is about a RELATIONSHIP between slot entries, which is
        exactly what a cross-slot invariant is for:

          monotonic  a field is ordered by another field   (depth: speed rises with z)
          count      how many entries match a predicate    (at most one opaque plane)
          extreme    a matching entry sits at an end       (the opaque one is backmost)

        An invariant with no `rule` is documentation, not enforcement, and is reported as
        such rather than silently passing.
        """
        out: list[str] = []
        inv = (pr.raw.get("invariants") or {}).get("crossSlot", []) or []
        for spec in inv:
            if not isinstance(spec, dict) or spec.get("check") != "computed":
                continue
            rule, iid = spec.get("rule"), spec.get("id", "?")
            if not isinstance(rule, dict):
                out.append(
                    f"{pr.ref}: invariant '{iid}' is marked computed but carries no 'rule', "
                    "so nothing checks it"
                )
                continue
            rows = c.slots.get(rule.get("over", ""), [])
            if not isinstance(rows, list):
                continue
            fail = self._eval_rule(rule, rows)
            if fail:
                out.append(f"instance '{c.id}': invariant '{iid}' fails — {fail}")
        return out

    @staticmethod
    def _eval_rule(rule: dict[str, Any], rows: list[Any]) -> str:
        """Return a failure description, or '' if the rule holds."""
        rows = [r for r in rows if isinstance(r, dict)]
        op = rule.get("op")

        def matching() -> list[dict[str, Any]]:
            where = rule.get("where") or {}
            return [r for r in rows if all(r.get(k) == v for k, v in where.items())]

        if op == "monotonic":
            by, field = rule.get("by"), rule.get("field")
            strict = bool(rule.get("strict", True))
            up = rule.get("direction", "increasing") == "increasing"
            seq = sorted(rows, key=lambda r: r.get(by, 0))
            for a, b in zip(seq, seq[1:]):
                x, y = a.get(field), b.get(field)
                if x is None or y is None:
                    return f"'{field}' missing on an entry"
                ok = (y > x if strict else y >= x) if up else (y < x if strict else y <= x)
                if not ok:
                    return (f"{field} must {'rise' if up else 'fall'} with {by}, but "
                            f"{by}={a.get(by)} has {field}={x} and {by}={b.get(by)} has {field}={y}")
            return ""

        if op == "count":
            n = len(matching())
            if "max" in rule and n > rule["max"]:
                return f"{n} entries match {rule.get('where')}, max is {rule['max']}"
            if "min" in rule and n < rule["min"]:
                return f"{n} entries match {rule.get('where')}, min is {rule['min']}"
            return ""

        if op == "extreme":
            hits, by = matching(), rule.get("by")
            if not hits or not rows:
                return ""
            want = min if rule.get("at", "min") == "min" else max
            edge = want(rows, key=lambda r: r.get(by, 0)).get(by)
            off = [h for h in hits if h.get(by) != edge]
            if off:
                return (f"entry matching {rule.get('where')} must sit at {rule.get('at')} "
                        f"{by}={edge}, found at {by}={off[0].get(by)}")
            return ""

        return f"unknown rule op '{op}'"

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
