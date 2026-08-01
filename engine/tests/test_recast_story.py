"""recast-story: the structural half is provable, the prose half is a judgment.

Earned 2026-08-01 on will-there-be-ice-cream, which did two entity swaps by blanket
string replacement and shipped five beats still describing furniture that was gone.
"""
import sys, json, pathlib, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills/update-book/scripts"))
import recast_story as rs


def _uni(tmp, old_extra=None, new_extra=None):
    u = pathlib.Path(tmp) / "u"
    (u / "stories").mkdir(parents=True)
    (u / "canon" / "entities").mkdir(parents=True)
    old = {"id": "old-room", "kind": "setting",
           "contract": {"map": "a counter and two stools", "dressing": "a scoop case"},
           "structured": {"sheets": {"master": "x.png", "empty": "y.png"}}}
    new = {"id": "new-room", "kind": "setting",
           "contract": {"map": "a bench under a tree"},
           "structured": {"sheets": {"wide": "w.png", "close": "c.png"}}}
    old.update(old_extra or {}); new.update(new_extra or {})
    (u / "canon/entities/old-room.json").write_text(json.dumps(old))
    (u / "canon/entities/new-room.json").write_text(json.dumps(new))
    (u / "stories/s.json").write_text(json.dumps({
        "id": "s", "features": ["old-room"],
        "beats": [{"n": 1, "text": "He taps the counter twice.", "location": "old-room"},
                  {"n": 2, "text": "They look at the sky.", "location": "old-room"}]}))
    return u


class TestRecast(unittest.TestCase):
    def test_swaps_every_structural_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            u = _uni(tmp)
            rs.main([str(u), "s", "old-room", "new-room", "--apply"])
            st = json.loads((u / "stories/s.json").read_text())
            self.assertEqual(st["features"], ["new-room"])
            self.assertTrue(all(b["location"] == "new-room" for b in st["beats"]))

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            u = _uni(tmp)
            before = (u / "stories/s.json").read_text()
            rs.main([str(u), "s", "old-room", "new-room"])
            self.assertEqual((u / "stories/s.json").read_text(), before)

    def test_refuses_an_unregistered_entity(self):
        with tempfile.TemporaryDirectory() as tmp:
            u = _uni(tmp)
            with self.assertRaises(SystemExit):
                rs.main([str(u), "s", "old-room", "not-a-real-entity"])

    def test_flags_a_plate_the_new_entity_does_not_have(self):
        """A camera is the one thing a swap must never guess."""
        with tempfile.TemporaryDirectory() as tmp:
            u = _uni(tmp)
            spec = {"story": "s", "spreads": [
                {"id": "spread-01", "setting": "old-room", "plate": "master", "scene": "x"}]}
            bad, legal = rs.illegal_plates(
                rs.swap(spec, "old-room", "new-room", {}), "new-room",
                json.loads((u / "canon/entities/new-room.json").read_text()))
            self.assertEqual(bad, ["master"])
            self.assertEqual(legal, {"wide", "close"})

    def test_review_packet_carries_both_entities_and_every_beat(self):
        """The judgment is a ROLE, not a service: the packet must be readable alone."""
        with tempfile.TemporaryDirectory() as tmp:
            u = _uni(tmp)
            story = json.loads((u / "stories/s.json").read_text())
            old = json.loads((u / "canon/entities/old-room.json").read_text())
            new = json.loads((u / "canon/entities/new-room.json").read_text())
            pkt = rs.review_packet(old, new, story, None)
            self.assertIn("a counter and two stools", pkt)   # what was removed
            self.assertIn("a bench under a tree", pkt)       # what replaced it
            self.assertIn("He taps the counter twice.", pkt)  # the stale beat
            self.assertIn("They look at the sky.", pkt)       # and the innocent one
            self.assertNotIn("vocabulary", pkt.lower(),
                             "this is a read, not a word list")


if __name__ == "__main__":
    unittest.main()
