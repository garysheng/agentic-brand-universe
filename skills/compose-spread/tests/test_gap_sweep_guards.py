"""Spread-compiler guards from the v0.54 gap sweep: #2 G1, #19 G14, #48, #36 G34."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_assemble_prompt import build_universe, png, run, write_spec  # noqa: E402

AUDIT = Path(__file__).resolve().parents[2] / "compose-spec" / "scripts" / "audit_spec_shots.py"


def _edit(root: Path, eid: str, fn):
    p = root / "canon" / "entities" / f"{eid}.json"
    d = json.loads(p.read_text())
    fn(d)
    p.write_text(json.dumps(d))


def _add_char(root: Path, eid: str, **structured):
    png(root / "reference" / eid / "full.png")
    st = {"sheets": {"forward-fullbody": f"reference/{eid}/full.png"},
          "requiredForRender": ["forward-fullbody"], "invariants": ["x"]}
    st.update(structured)
    (root / "canon" / "entities" / f"{eid}.json").write_text(json.dumps(
        {"id": eid, "kind": "character", "structured": st}))


class Base(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = Path(self.t.name)
        build_universe(self.root)

    def tearDown(self):
        self.t.cleanup()

    def spec(self, cast, **sp_extra):
        spec = write_spec(self.root, cast)
        d = json.loads(spec.read_text())
        d["spreads"][0].update(sp_extra)
        spec.write_text(json.dumps(d))
        return spec


class TestPoseDropSheets(Base):
    """G1: a pose that changes the body drops the base sheet it contradicts."""

    def setUp(self):
        super().setUp()
        png(self.root / "reference" / "scout" / "soaked.png")
        _edit(self.root, "scout", lambda d: d["structured"]["render"]["poses"].update(
            {"soaked": {"sheets": ["soaked"], "dropSheets": ["forward-fullbody"],
                        "bake": "SOAKED through."}}) or
              d["structured"]["sheets"].update({"soaked": "reference/scout/soaked.png"}))

    def refs(self, pose):
        r = run(self.root, self.spec([{"id": "scout", "pose": pose}]))
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)["refs"]

    def test_the_contradicted_base_sheet_is_not_passed(self):
        refs = self.refs("soaked")
        self.assertFalse(any(x.endswith("scout/full.png") for x in refs), refs)
        self.assertTrue(any(x.endswith("scout/soaked.png") for x in refs), refs)
        self.assertTrue(any(x.endswith("scout/face.png") for x in refs), refs)

    def test_other_poses_still_pass_it(self):
        self.assertTrue(any(x.endswith("scout/full.png") for x in self.refs("front")))

    def test_dropping_an_unknown_sheet_refuses(self):
        _edit(self.root, "scout", lambda d: d["structured"]["render"]["poses"]["soaked"]
              .update({"dropSheets": ["nope"]}))
        r = run(self.root, self.spec([{"id": "scout", "pose": "soaked"}]))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("nope", r.stderr + r.stdout)


class TestUncastGuard(Base):
    """G14: a scoped allowUncast; #48: alsoKnownAs feeds the guard."""

    def test_a_scoped_allow_silences_only_the_named_entity(self):
        _add_char(self.root, "miss-odessa")
        _add_char(self.root, "hugo-dyson")
        spec = self.spec([{"id": "clean"}], scene="impossible to miss, and Hugo waves",
                         allowUncast=["miss-odessa"])
        r = run(self.root, spec)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("hugo-dyson", r.stderr + r.stdout)
        self.assertNotIn("miss-odessa", (r.stderr + r.stdout).split("UNCAST")[-1].split("e.g.")[0])

    def test_a_scoped_allow_passes_when_it_covers_the_only_false_positive(self):
        _add_char(self.root, "miss-odessa")
        spec = self.spec([{"id": "clean"}], scene="impossible to miss",
                         allowUncast=["miss-odessa"])
        self.assertEqual(run(self.root, spec).returncode, 0)

    def test_blanket_true_still_disarms(self):
        _add_char(self.root, "hugo-dyson")
        spec = self.spec([{"id": "clean"}], scene="Hugo waves", allowUncast=True)
        self.assertEqual(run(self.root, spec).returncode, 0)

    def test_a_nickname_declared_in_alsoKnownAs_is_caught(self):
        _add_char(self.root, "larrance-dopson", alsoKnownAs=["Rance"])
        spec = self.spec([{"id": "clean"}], scene="RANCE leans on the counter")
        r = run(self.root, spec)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("larrance-dopson", r.stderr + r.stdout)

    def test_a_cast_entitys_nickname_is_accounted_for(self):
        _add_char(self.root, "larrance-dopson", alsoKnownAs=["Rance"])
        spec = self.spec([{"id": "larrance-dopson"}], scene="RANCE leans on the counter")
        self.assertEqual(run(self.root, spec).returncode, 0, run(self.root, spec).stderr)


class TestInsertWithAPersonCast(Base):
    """G34: an insert that casts a person is refused before any spend."""

    def audit(self, cast):
        spec = {"book": "b", "spreads": [
            {"id": "spread-01", "setting": "home", "plate": "kitchen", "shot": "insert",
             "cast": cast}]}
        f = self.root / "rs.json"
        f.write_text(json.dumps(spec))
        r = subprocess.run([sys.executable, str(AUDIT), str(self.root), str(f), "--json"],
                           capture_output=True, text=True)
        return r.returncode, json.loads(r.stdout)["problems"]

    def test_a_character_in_an_insert_is_refused(self):
        code, probs = self.audit([{"id": "clean"}])
        self.assertEqual(code, 2)
        self.assertTrue(any("R5 INSERT WITH A PERSON CAST" in p for p in probs), probs)

    def test_a_prop_in_an_insert_is_what_an_insert_is_for(self):
        code, probs = self.audit([{"id": "tome"}])
        self.assertFalse(any("R5" in p for p in probs), probs)


class TestSettingOccupants(Base):
    """G16 (#21): a setting that declares its occupants refuses a stranger in its home."""

    def setUp(self):
        super().setUp()
        _edit(self.root, "home", lambda d: d.setdefault("structured", {}).update(
            {"occupants": ["clean", "stache"]}))

    def test_an_occupant_is_fine(self):
        r = run(self.root, self.spec([{"id": "clean"}]))
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_a_stranger_is_refused(self):
        r = run(self.root, self.spec([{"id": "scout"}]))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("NOT AN OCCUPANT", r.stderr + r.stdout)
        self.assertIn("guests", r.stderr + r.stdout)

    def test_a_declared_guest_is_admitted(self):
        r = run(self.root, self.spec([{"id": "scout"}], guests=["scout"]))
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_allow_guests_on_the_setting_admits_anyone(self):
        _edit(self.root, "home", lambda d: d["structured"].update({"allowGuests": True}))
        self.assertEqual(run(self.root, self.spec([{"id": "scout"}])).returncode, 0)

    def test_a_setting_without_occupants_is_unchanged(self):
        _edit(self.root, "home", lambda d: d["structured"].pop("occupants"))
        self.assertEqual(run(self.root, self.spec([{"id": "scout"}])).returncode, 0)


if __name__ == "__main__":
    unittest.main()
