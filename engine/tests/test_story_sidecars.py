"""stories/*.json enumeration: a sidecar is not a story.

voice-gate's DEFAULT waiver path is `<manuscript-stem>.voice-waivers.json` INSIDE
stories/ (beside the manuscript it waives). The store loaded every stories/*.json
as a StorySpec, so a waiver sidecar validated as a story and `abu validate` emitted
a false "story missing 'id'" plus "no declared spine" for each one. Bit twice in one
book run, 2026-08-02 (the-bible-all-points-to-jesus, nation-of-fire).
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE_DIR))

from agenticstory import CanonStore  # noqa: E402
from agenticstory.store import is_story_sidecar  # noqa: E402


def build(root: Path) -> Path:
    (root / "canon" / "entities").mkdir(parents=True)
    (root / "stories").mkdir()
    (root / "universe.json").write_text(json.dumps({"name": "t", "assetRoot": "."}))
    (root / "stories" / "tale.json").write_text(json.dumps(
        {"id": "tale", "spine": "testimony", "status": "stub"}))
    # the exact real-world shape: a waiver sidecar named after the manuscript,
    # holding waiver records and (correctly) no story fields at all
    (root / "stories" / "tale.voice-waivers.json").write_text(json.dumps(
        {"waivers": [{"finding": "em-dash L12", "reason": "quoted scripture verbatim"}]}))
    return root


class TestStorySidecars(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = build(Path(self.tmp.name))
        self.store = CanonStore(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_waiver_sidecar_is_not_loaded_as_a_story(self):
        self.assertEqual(set(self.store.stories), {"tale"})

    def test_waiver_sidecar_produces_zero_validate_findings(self):
        problems = self.store.validate_canon()
        self.assertEqual(problems, [],
                         f"a voice-waiver sidecar in stories/ must not validate as a "
                         f"story; got: {problems}")

    def test_predicate_names_exactly_the_sidecars(self):
        self.assertTrue(is_story_sidecar(Path("stories/x.voice-waivers.json")))
        self.assertFalse(is_story_sidecar(Path("stories/x.json")))
        # a story whose ID merely contains the words is still a story
        self.assertFalse(is_story_sidecar(Path("stories/voice-waivers.json")))


if __name__ == "__main__":
    unittest.main()
