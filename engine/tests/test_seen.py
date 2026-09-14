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

from agenticstory import display, seen
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


def _board(p, options=(seen.VERDICTS[0], seen.VERDICTS[1]), channel=display.FRAPP, why=""):
    return seen.record_board(p, question="master — look at it", options=list(options),
                             display=display.pending(channel, why))


def _shown(p, **kw):
    """A board on the frapp channel whose page has served the picture. The ordinary case."""
    rec = _board(p, **kw)
    seen.record_serve(p)
    return rec


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
            _shown(p)
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
            _shown(p)
            seen.record_tap(p, "keep")
            _board(p)
            self.assertIsNone(seen.read_seen(p).get("verdict"))
            # ...AND the serve with it: the old page's bytes are not this board's showing.
            self.assertFalse((seen.read_seen(p)["board"]["display"] or {}).get("served"))


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
            _board(p, options=["keep"])
            with self.assertRaises(ValueError) as cm:
                seen.record_tap(p, "reroll", why="bad hands")
            self.assertIn("board offered", str(cm.exception))

    def test_waived_is_allowed_off_the_board_but_needs_a_reason(self):
        # A waiver is by definition not a tap, so it is never an option; the written
        # reason is what keeps it from being a skip with better manners.
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            _board(p, options=["keep"])
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
            _shown(p)
            p.write_bytes(b"\x89PNG-a-different-picture")
            with self.assertRaises(ValueError) as cm:
                seen.record_tap(p, "keep")
            self.assertIn("bytes changed", str(cm.exception))

    def test_bytes_that_changed_after_the_tap_invalidate_the_approval(self):
        # A re-roll writes the new picture at the SAME path. Without this, the operator's
        # yes to the old one silently approves art nobody has looked at.
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            _shown(p)
            seen.record_tap(p, "keep")
            self.assertIsNone(seen.seen_problem(p))
            p.write_bytes(b"\x89PNG-rerolled")
            self.assertIn("changed since it was judged", seen.seen_problem(p))

    def test_a_board_with_no_answer_is_not_an_approval(self):
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            _board(p)
            self.assertIn("no verdict came back", seen.seen_problem(p))


class TheBoardMustShowThePicture(unittest.TestCase):
    """v0.51. A tap proves a decision was made; it does not prove there was anything to
    decide FROM. An AskUserQuestion preview is TEXT, so v0.50's record proved the operator
    tapped a card NAMING a file."""

    def test_a_board_with_no_display_channel_is_refused(self):
        """THE TEST THAT FAILS WITHOUT THE FIX: a board could ask about art it never showed."""
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            with self.assertRaises(ValueError) as cm:
                seen.record_board(p, question="q", options=["keep"], display={})
            self.assertIn("no display channel", str(cm.exception))
            # The refusal names the fix, or the reader goes looking for a flag.
            self.assertIn("display.pending", str(cm.exception))

    def test_an_approving_tap_on_a_frapp_board_that_never_served_is_refused(self):
        """THE TEST THAT FAILS WITHOUT THE FIX: the page not sending the bytes is the case
        where the operator was looking at a broken image."""
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            _board(p)
            with self.assertRaises(ValueError) as cm:
                seen.record_tap(p, "keep")
            self.assertIn("never served this picture", str(cm.exception))

    def test_a_reroll_is_exempt_because_turning_art_down_is_the_safe_direction(self):
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            _board(p)
            seen.record_tap(p, "reroll", why="the hands are wrong")
            self.assertIn("RE-ROLL", seen.seen_problem(p))

    def test_a_waiver_is_exempt_because_a_waiver_is_by_definition_not_a_look(self):
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            _board(p)
            seen.record_tap(p, "waived", why="operator unreachable before the deadline")
            self.assertIsNone(seen.seen_problem(p))
            self.assertIn("unshown", seen.read_seen(p))

    def test_a_served_picture_can_then_be_kept(self):
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            _shown(p)
            seen.record_tap(p, "keep")
            self.assertIsNone(seen.seen_problem(p))
            self.assertIsNone(seen.seen_caveat(p))
            self.assertNotIn("unshown", seen.read_seen(p))

    def test_the_serve_records_the_bytes_and_the_moment(self):
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            _board(p)
            disp = seen.record_serve(p, url="/shot/0")
            self.assertTrue(disp["served"])
            self.assertEqual(disp["digest"], seen.digest(p))
            self.assertEqual(disp["url"], "/shot/0")
            self.assertTrue(disp["servedOn"])

    def test_a_serve_for_a_shot_that_was_never_on_a_board_is_refused(self):
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            with self.assertRaises(ValueError) as cm:
                seen.record_serve(p)
            self.assertIn("never on a board", str(cm.exception))

    def test_a_card_board_cannot_report_a_serve_because_it_sent_nothing(self):
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            _board(p, channel=display.CARD, why="no Freedom install")
            with self.assertRaises(ValueError) as cm:
                seen.record_serve(p)
            self.assertIn("serves nothing", str(cm.exception))

    def test_a_serve_of_bytes_the_board_is_not_about_is_refused(self):
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            _board(p)
            p.write_bytes(b"\x89PNG-a-re-roll-landed-here")
            with self.assertRaises(ValueError) as cm:
                seen.record_serve(p)
            self.assertIn("bytes changed", str(cm.exception))

    def test_a_page_reporting_a_digest_the_file_does_not_have_is_refused(self):
        # The serve record is about the bytes that LEFT. A page that read one file and
        # reported another is the forgery this closes.
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            _board(p)
            with self.assertRaises(ValueError) as cm:
                seen.record_serve(p, sent_digest="0000000000000000")
            self.assertIn("not the same bytes", str(cm.exception))


class TheHonestDegrade(unittest.TestCase):
    """ABU runs on machines with no Freedom install, so the card channel survives as the
    fallback. What it must NOT do is produce a record that looks like the real thing."""

    def test_a_card_channel_keep_locks_but_is_recorded_as_unshown(self):
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            _board(p, channel=display.CARD, why="no Freedom install on this machine.")
            seen.record_tap(p, "keep")
            self.assertIsNone(seen.seen_problem(p))          # it locks
            un = seen.read_seen(p)["unshown"]                # and it says what it is
            self.assertEqual(un["channel"], display.CARD)
            self.assertIn("no Freedom install", un["why"])

    def test_the_two_kinds_of_yes_do_not_look_alike(self):
        """THE TEST THAT FAILS WITHOUT THE FIX: a degrade whose record matched the real
        thing would be this gate's own failure mode, one level along."""
        with tempfile.TemporaryDirectory() as root:
            shown, unshown = _shot(root, "a.png", b"\x89PNG-a"), _shot(root, "b.png", b"\x89PNG-b")
            _shown(shown)
            seen.record_tap(shown, "keep")
            _board(unshown, channel=display.CARD, why="no Freedom install on this machine.")
            seen.record_tap(unshown, "keep")
            self.assertEqual(seen.read_seen(shown)["verdict"],
                             seen.read_seen(unshown)["verdict"])   # same word
            self.assertNotIn("unshown", seen.read_seen(shown))     # different record
            self.assertIn("unshown", seen.read_seen(unshown))
            self.assertIsNone(seen.seen_caveat(shown))
            self.assertIn("WITHOUT the art being displayed", seen.seen_caveat(unshown))

    def test_a_hand_edited_sidecar_is_caught_at_lock_time(self):
        # record_tap already refuses this, so reaching it here means the file was written by
        # something other than the verbs.
        with tempfile.TemporaryDirectory() as root:
            p = _shot(root)
            _shown(p)
            seen.record_tap(p, "keep")
            doc = json.loads(seen.sidecar_path(p).read_text())
            doc["seen"]["board"]["display"]["served"] = False
            seen.sidecar_path(p).write_text(json.dumps(doc))
            self.assertIn("never served the picture", seen.seen_problem(p))


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
            _shown(p)
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
