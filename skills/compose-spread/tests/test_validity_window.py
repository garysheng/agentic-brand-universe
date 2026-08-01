"""compose-spread — VARIANT VALIDITY WINDOW tests (SPEC v0.18). Stdlib unittest.

The gap: nothing gated WHICH variant a spread could select. A character's
altLooks and a setting's era plates were all equally legal on every spread, so on
a book spanning three ages of one man nothing stopped a 1933 beat picking the
`elder` look, and nothing stopped a 1990 beat silently falling through to the
default young face. Both failures are SILENT: the render succeeds, it is simply
of the wrong person, and it is internally consistent and beautiful, so nobody
looks twice.

Earned 2026-07-31 on the-power-of-obeying (69 spreads, 1917 to 2003). The look
was named by hand on all 71 spreads because nothing could check it.

Two properties matter as much as the gate itself:

  * OPT-IN AT BOTH ENDS. A spread with no `when`, or an entity whose variants
    declare no window, compiles exactly as before. No universe migrates.
  * THE REFUSAL NAMES THE LEGAL VARIANT. A gate that only says "no" makes the
    operator go read canon; the whole cost saving is that it says which one.

Run:  python3 -m unittest discover -s tests -v   (from the compose-spread skill dir)
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_assemble_prompt import build_universe, png  # noqa: E402
from assemble_prompt import build, load, Refuse  # noqa: E402


class TestValidityWindow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        build_universe(self.root)
        self.ents = self.root / "canon" / "entities"

    def tearDown(self):
        self.tmp.cleanup()

    # ── fixtures ─────────────────────────────────────────────────────────────

    def man(self, default_window=None, alts=None):
        """One man in three eras, off one identity: the kenneth-hagin shape."""
        for rel in ("face-neutral", "forward-fullbody",
                    "young/face-3q", "elder/face-3q", "bedfast/face-3q"):
            png(self.root / "reference" / "man" / f"{rel}.png")
        st = {
            "sheets": {"face-neutral": "reference/man/face-neutral.png",
                       "forward-fullbody": "reference/man/forward-fullbody.png"},
            "requiredForRender": ["face-neutral", "forward-fullbody"],
            "invariants": ["long-narrow-face"],
            "altLooks": alts if alts is not None else {
                "bedfast": {"validFor": {"from": 1933, "to": 1934},
                            "anchorPhoto": "reference/man/bedfast/face-3q.png",
                            "invariants": ["gaunt"]},
                "elder": {"validFor": {"from": 1974},
                          "anchorPhoto": "reference/man/elder/face-3q.png",
                          "invariants": ["full-white-hair"]},
            },
        }
        if default_window is not None:
            st["validFor"] = default_window
        (self.ents / "man.json").write_text(json.dumps({
            "id": "man", "kind": "character", "status": "locked", "structured": st}))

    def ground(self):
        """One piece of ground in two eras: the-broken-arrow-ground shape."""
        for k in ("era-farm-empty-pasture", "era-1976-empty-from-the-corner"):
            png(self.root / "reference" / "ground" / f"{k}.png")
        (self.ents / "ground.json").write_text(json.dumps({
            "id": "ground", "kind": "setting", "status": "locked",
            "structured": {"sheets": {
                "era-farm-empty-pasture": "reference/ground/era-farm-empty-pasture.png",
                "era-1976-empty-from-the-corner":
                    "reference/ground/era-1976-empty-from-the-corner.png"}},
            "contract": {
                "map": "flat Oklahoma prairie with one shallow rise",
                "emptyPlates": ["reference/ground/era-farm-empty-pasture.png",
                                "reference/ground/era-1976-empty-from-the-corner.png"],
                "plates": {
                    "era-farm-empty-pasture": {"validFor": {"to": 1930}},
                    "era-1976-empty-from-the-corner": {"validFor": {"from": 1970}},
                }}}))

    def spec(self, **spread):
        sp = {"id": "s1", "scene": "a man on a day"}
        sp.update(spread)
        p = self.root / "render-spec.json"
        p.write_text(json.dumps({
            "size": "1536x1024", "style": "warm test style.",
            "negatives": ["no text anywhere"], "spreads": [sp]}))
        return load(p)

    def go(self, **spread):
        return build(self.root, self.spec(**spread), "s1")

    # ── the gate ─────────────────────────────────────────────────────────────

    def test_wrong_era_alt_look_is_refused_before_spending(self):
        self.man()
        with self.assertRaises(Refuse) as e:
            self.go(when=1933, cast=[{"id": "man", "look": "elder"}])
        self.assertIn("WRONG ERA", str(e.exception))
        self.assertIn("elder", str(e.exception))

    def test_the_refusal_names_the_variant_that_IS_legal(self):
        self.man()
        with self.assertRaises(Refuse) as e:
            self.go(when=1933, cast=[{"id": "man", "look": "elder"}])
        self.assertIn("bedfast", str(e.exception))

    def test_right_era_alt_look_passes(self):
        self.man()
        job = self.go(when=1933, cast=[{"id": "man", "look": "bedfast"}])
        self.assertIn("gaunt", " ".join(job["qa"]))

    def test_open_ended_window_covers_everything_after_it(self):
        self.man()
        self.go(when=2003, cast=[{"id": "man", "look": "elder"}])

    def test_the_DEFAULT_look_can_carry_a_window_too(self):
        """The dangerous case is not only picking the wrong alt look. It is
        FORGETTING to name one and falling through to the default face."""
        self.man(default_window={"from": 1935, "to": 1973})
        with self.assertRaises(Refuse) as e:
            self.go(when=1990, cast=[{"id": "man"}])
        self.assertIn("default look", str(e.exception))
        self.assertIn("elder", str(e.exception))

    def test_default_look_inside_its_window_passes(self):
        self.man(default_window={"from": 1935, "to": 1973})
        self.go(when=1950, cast=[{"id": "man"}])

    # ── a setting's ERA axis is its PLATES ───────────────────────────────────

    def test_wrong_era_setting_plate_is_refused(self):
        self.ground()
        with self.assertRaises(Refuse) as e:
            self.go(when=1976, setting="ground", plate="era-farm-empty-pasture")
        self.assertIn("WRONG ERA", str(e.exception))
        self.assertIn("era-1976-empty-from-the-corner", str(e.exception))

    def test_right_era_setting_plate_passes(self):
        self.ground()
        self.go(when=1976, setting="ground", plate="era-1976-empty-from-the-corner")

    def test_the_other_era_of_the_same_ground_passes_at_its_own_date(self):
        """Both eras stay ONE entity. That is the whole point: the argument is
        that it is the same ground, so splitting it into two entities would
        destroy the only claim the setting exists to make."""
        self.ground()
        self.go(when=1910, setting="ground", plate="era-farm-empty-pasture")

    # ── opt-in at both ends: nothing already shipped changes shape ───────────

    def test_a_spread_with_no_when_is_unconstrained(self):
        self.man()
        self.go(cast=[{"id": "man", "look": "elder"}])

    def test_an_entity_with_no_declared_windows_is_unconstrained(self):
        self.man(alts={"elder": {"anchorPhoto": "reference/man/elder/face-3q.png"}})
        self.go(when=1933, cast=[{"id": "man", "look": "elder"}])

    def test_a_non_numeric_when_is_refused_rather_than_ignored(self):
        self.man()
        with self.assertRaises(Refuse) as e:
            self.go(when="1933", cast=[{"id": "man", "look": "bedfast"}])
        self.assertIn("must be a number", str(e.exception))

    def test_an_inverted_window_is_refused(self):
        self.man(alts={"elder": {"validFor": {"from": 2000, "to": 1900},
                                 "anchorPhoto": "reference/man/elder/face-3q.png"}})
        with self.assertRaises(Refuse) as e:
            self.go(when=1950, cast=[{"id": "man", "look": "elder"}])
        self.assertIn("inverted", str(e.exception))

    def test_when_may_be_a_beat_index_not_only_a_year(self):
        """The framework compares numbers and does not care what scale the
        universe counts in."""
        self.man(alts={"late": {"validFor": {"from": 40},
                                "anchorPhoto": "reference/man/elder/face-3q.png"}})
        self.go(when=55, cast=[{"id": "man", "look": "late"}])
        with self.assertRaises(Refuse):
            self.go(when=3, cast=[{"id": "man", "look": "late"}])


if __name__ == "__main__":
    unittest.main(verbosity=2)
