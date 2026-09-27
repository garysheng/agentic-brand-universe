"""An alt-look's OWN photoStack reaches the render (gap G26, #28).

The shooter builds an era from the look's photographs; a render that ignored them would
hand the spreads a different face from the one the matrix was shot on.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_assemble_prompt import build_universe, png, run, write_spec  # noqa: E402


class TestLookPhotoStack(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = Path(self.t.name)
        build_universe(self.root)
        png(self.root / "reference" / "stache" / "young" / "a.png")
        png(self.root / "reference" / "stache" / "young" / "b.png")
        p = self.root / "canon" / "entities" / "stache.json"
        d = json.loads(p.read_text())
        d["structured"]["altLooks"]["mustache-wavy"]["photoStack"] = [
            "reference/stache/young/a.png", "reference/stache/young"]
        p.write_text(json.dumps(d))

    def tearDown(self):
        self.t.cleanup()

    def test_look_photos_are_passed_once_each_after_the_anchor_photo(self):
        r = run(self.root, write_spec(self.root, [{"id": "stache", "look": "mustache-wavy"}]))
        self.assertEqual(r.returncode, 0, r.stderr)
        refs = json.loads(r.stdout)["refs"]
        tail = [Path(x).name for x in refs if "/stache/" in x]
        self.assertEqual(tail[:3], ["alt-photo.png", "a.png", "b.png"], refs)
        self.assertEqual(tail.count("a.png"), 1)


if __name__ == "__main__":
    unittest.main()
