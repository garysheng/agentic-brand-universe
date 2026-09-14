"""The seen record, and the refusal it gives `lock_shot` (SPEC v0.50).

`shoot-references` said "no shot locks until a human has actually seen it" in prose for
months, and its own map named the blocker: what COUNTS as shown. The answer is a tap on an
AskUserQuestion card, recorded beside the image in the same sidecar the v0.49 guard
verdicts use.

Each test here pins one way the record could be forged, because every one of them looks
like success from outside: a verdict for a shot nobody was shown, a verdict that was not on
the board, a re-roll approved anyway, and bytes that changed after the yes.
"""
import json
import pathlib
import tempfile
import unittest

from agenticstory import seen
from agenticstory.authoring import lock_shot


def _entity():
    return {"id": "the-wingman", "kind": "character",
            "structured": {"sheets": {"master": None}, "requiredForRender": []},
            "authority": {"lockedBy": "someone"}}


def _shot(root, name="master.png", data=b"\x89PNG-one"):
    d = pathlib.Path(root) / "reference" / "x"
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_bytes(data)
    return p


def _board(p, options=(seen.VERDICTS[0], seen.VERDICTS[1])):
    return seen.record_board(p, question="master — look at it", options=list(options))


class TheRecord(unittest.TestCase):
    def test_the_sidecar_is_the_readback_sidecar_not_a_third_shape(self):
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            self.assertEqual(seen.sidecar_path(p).name, "master.png.readback.json")

    def test_a_board_and_a_guard_verdict_share_one_file_without_clobbering(self):
        # verify_render.py writes guardVerdicts into this same file. The two records are
        # judged by different checks at different moments and must both survive.
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            seen.sidecar_path(p).write_text(json.dumps(
                {"guardVerdicts": {"device-anatomy": {"verdict": "pass"}}}))
            _board(p)
            seen.record_tap(p, "keep")
            doc = json.loads(seen.sidecar_path(p).read_text())
            self.assertEqual(doc["guardVerdicts"]["device-anatomy"]["verdict"], "pass")
            self.assertEqual(doc["seen"]["verdict"], "keep")

    def test_a_board_records_the_bytes_the_operator_was_shown(self):
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            rec = _board(p)
            self.assertEqual(rec["board"]["digest"], seen.digest(p))
            self.assertEqual(rec["board"]["options"], ["keep", "reroll"])

    def test_a_new_board_supersedes_the_old_verdict(self):
        # Showing the picture again means the old yes does not carry over.
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            _board(p)
            seen.record_tap(p, "keep")
            _board(p)
            self.assertIsNone(seen.read_seen(p).get("verdict"))


class TheRefusals(unittest.TestCase):
    def test_a_verdict_for_a_shot_that_was_never_on_a_board_is_refused(self):
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            with self.assertRaises(ValueError) as cm:
                seen.record_tap(p, "keep")
            self.assertIn("never on a board", str(cm.exception))

    def test_a_verdict_the_board_did_not_offer_is_refused(self):
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            seen.record_board(p, question="q", options=["keep"])
            with self.assertRaises(ValueError) as cm:
                seen.record_tap(p, "reroll", why="bad hands")
            self.assertIn("board offered", str(cm.exception))

    def test_waived_is_allowed_off_the_board_but_needs_a_reason(self):
        # A waiver is by definition not a tap, so it is never an option; the written
        # reason is what keeps it from being a skip with better manners.
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            seen.record_board(p, question="q", options=["keep"])
            with self.assertRaises(ValueError) as cm:
                seen.record_tap(p, "waived")
            self.assertIn("no reason", str(cm.exception))
            seen.record_tap(p, "waived", why="operator unreachable before the deadline")
            self.assertIsNone(seen.seen_problem(p))

    def test_an_unknown_verdict_word_is_refused(self):
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            _board(p)
            with self.assertRaises(ValueError):
                seen.record_tap(p, "looks-fine")

    def test_a_reroll_needs_a_reason_and_then_blocks_the_lock(self):
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            _board(p)
            with self.assertRaises(ValueError):
                seen.record_tap(p, "reroll")
            seen.record_tap(p, "reroll", why="screen on the wrong side")
            self.assertIn("RE-ROLL", seen.seen_problem(p))

    def test_bytes_that_changed_between_the_board_and_the_tap_are_refused(self):
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            _board(p)
            p.write_bytes(b"\x89PNG-a-different-picture")
            with self.assertRaises(ValueError) as cm:
                seen.record_tap(p, "keep")
            self.assertIn("bytes changed", str(cm.exception))

    def test_bytes_that_changed_after_the_tap_invalidate_the_approval(self):
        # A re-roll writes the new picture at the SAME path. Without this, the operator's
        # yes to the old one silently approves art nobody has looked at.
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            _board(p)
            seen.record_tap(p, "keep")
            self.assertIsNone(seen.seen_problem(p))
            p.write_bytes(b"\x89PNG-rerolled")
            self.assertIn("changed since it was judged", seen.seen_problem(p))

    def test_a_board_with_no_answer_is_not_an_approval(self):
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            _board(p)
            self.assertIn("no verdict came back", seen.seen_problem(p))


class TheLockRefusal(unittest.TestCase):
    """THE TEST THAT FAILS WITHOUT THE FIX: locking unseen art used to succeed."""

    def test_lock_shot_refuses_art_nobody_has_seen(self):
        with tempfile.TemporaryDirectory() as root:
            _shot(root)
            with self.assertRaises(ValueError) as cm:
                lock_shot(_entity(), "master", "reference/x/master.png", root=root)
            msg = str(cm.exception)
            self.assertIn("nobody has been shown", msg)
            # The refusal must say how to record it, or the reader goes looking for a flag
            # that turns the gate off.
            self.assertIn("AskUserQuestion", msg)

    def test_lock_shot_accepts_a_shot_with_a_recorded_keep(self):
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            _board(p)
            seen.record_tap(p, "keep")
            ent = lock_shot(_entity(), "master", "reference/x/master.png", root=root)
            self.assertEqual(ent["structured"]["sheets"]["master"], "reference/x/master.png")

    def test_lock_shot_refuses_a_shot_the_operator_turned_down(self):
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            _board(p)
            seen.record_tap(p, "reroll", why="wrong hands")
            with self.assertRaises(ValueError) as cm:
                lock_shot(_entity(), "master", "reference/x/master.png", root=root)
            self.assertIn("RE-ROLL", str(cm.exception))

    def test_a_symbolic_lock_with_no_root_is_still_allowed(self):
        # Same carve-out as the file-existence check: a relative path with no root resolves
        # to nowhere, and refusing it would break every caller that locks in memory.
        ent = lock_shot(_entity(), "master", "reference/x/master.png")
        self.assertEqual(ent["structured"]["sheets"]["master"], "reference/x/master.png")


if __name__ == "__main__":
    unittest.main()
