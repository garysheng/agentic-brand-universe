"""Agentic Brand Universe engine v0 — a universe is first-class; a story spec is its own primitive (SPEC §4.3); refs are load-bearing."""
from .model import CraftCanon, Entity, Relation, StorySpec  # noqa: F401
from .store import CanonStore  # noqa: F401
from .refs import (assert_story, assert_spread, resolve_entity_assets, resolve_setting,  # noqa: F401
                   lock_level, archived_casts, archived_entities)
from .matrix import REFERENCE_MATRIX, matrix_for  # noqa: F401
from .authoring import scaffold_entity, lock_shot  # noqa: F401

__version__ = "0.0.1"

# The framework spec every scaffolded universe conforms to. Canonical source of
# truth for provenance — a universe.json records these so it always names the
# spec version it follows and points back to the wiki that defines it (like a
# BOOMERANG.md `conforms_to`). Bump SPEC_VERSION in lockstep with SPEC.md.
#
# It went out of lockstep, which is the failure this constant exists to prevent.
# SPEC.md reached v0.6 (the projection release) while this still said 0.4.1, so every
# universe the engine scaffolded claimed conformance to a spec two releases old.
# `lint-universe` now checks a universe's pin against this value, so the two can no
# longer disagree quietly.
SPEC_VERSION = "0.25"
SPEC_WIKI = "https://agenticbranduniverse.com"
# The spec URL must RESOLVE. agenticstory.wiki was cited as the authority in every
# universe manifest and served nothing (parked DNS, no HTTP response), and its
# replacement agenticbranduniverse.com/spec 404s. A citation that does not resolve is
# the same defect as a recipe pointing at a file that is not there, so this points at
# the spec document itself, which is verifiably served.
SPEC_URL = "https://github.com/garysheng/agentic-brand-universe/blob/master/SPEC.md"
