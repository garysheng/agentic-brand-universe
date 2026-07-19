"""Agentic Story engine v0 — a universe is first-class; stories are compositions; refs are load-bearing."""
from .model import CraftCanon, Entity, Relation, StorySpec  # noqa: F401
from .store import CanonStore  # noqa: F401
from .refs import assert_story, assert_spread, resolve_entity_assets, resolve_setting, lock_level  # noqa: F401
from .matrix import REFERENCE_MATRIX, matrix_for  # noqa: F401
from .authoring import scaffold_entity, lock_shot  # noqa: F401

__version__ = "0.0.1"

# The framework spec every scaffolded universe conforms to. Canonical source of
# truth for provenance — a universe.json records these so it always names the
# spec version it follows and points back to the wiki that defines it (like a
# BOOMERANG.md `conforms_to`). Bump SPEC_VERSION in lockstep with SPEC.md.
SPEC_VERSION = "0.4.1"
SPEC_WIKI = "https://agenticstory.wiki"
SPEC_URL = "https://agenticstory.wiki/spec"
