#!/usr/bin/env python3
"""next_actions.py — the board of next moves.

Earned 2026-09-12. Gary, after a twelve-hour build: "ABU should leverage askuserquestion a lot
more / I keep wondering what the next possible actions are / This should feel more like a game
idk". The framework already knew the answer (grade.py emits `fix` = the closing verb) and had no
shape or moment in which to say it.

NO GRADER RUNS HERE. `grade` is stubbed, so these exercise the arranging, which is the part with
the judgement in it.
"""
import importlib.util
import json
import pathlib
import re
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE.parent / "scripts" / "next_actions.py"
_spec = importlib.util.spec_from_file_location("na", SRC)
na = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(na)


def fake(issues, score=74, grade_letter="C"):
    return {"universe": "u", "grade": grade_letter, "score": score, "issues": issues}


def issue(fix, impact, what="something", dimension="d"):
    return {"fix": fix, "impact": impact, "what": what, "dimension": dimension}


class Board(unittest.TestCase):
    def board(self, issues, **kw):
        with mock.patch.object(na, "grade", lambda u: fake(issues)):
            return na.board(pathlib.Path("/tmp/u"), **kw)

    def test_it_never_offers_more_than_four(self):
        """AskUserQuestion allows four. A fifth option cannot be rendered, so emitting one is a
        board the operator is told about and cannot use."""
        b = self.board([issue(f"v{i}", 10 - i) for i in range(9)])
        self.assertLessEqual(len(b["options"]), 4)
        self.assertEqual(b["omitted"], 5)

    def test_highest_impact_is_recommended(self):
        b = self.board([issue("small", 1), issue("big", 10), issue("mid", 5)])
        self.assertEqual(b["options"][0]["verb"], "big")
        self.assertTrue(b["options"][0]["recommended"])
        self.assertIn("(Recommended)", b["options"][0]["label"])
        self.assertFalse(any(o["recommended"] for o in b["options"][1:]))

    def test_it_groups_by_verb_rather_than_reciting_issues(self):
        """A real universe returns hundreds of issues. One row per verb is the whole point."""
        b = self.board([issue("same", 3, f"thing {i}") for i in range(40)])
        self.assertEqual(len(b["options"]), 1)
        self.assertEqual(b["options"][0]["openItems"], 40)

    def test_after_drops_the_move_just_made(self):
        """Topping the board of a job you have this second finished with that same job is the
        single most obviously wrong thing this could do."""
        b = self.board([issue("explore", 10), issue("other", 1)], after="explore")
        self.assertNotIn("explore", [o["verb"] for o in b["options"]])

    def test_after_promotes_what_the_move_makes_possible(self):
        b = self.board([issue("add-story", 10), issue("shoot-references", 2)], after="explore")
        self.assertEqual(b["options"][0]["verb"], "shoot-references",
                         "a declared follow-on must outrank a higher-impact unrelated verb")

    def test_a_follow_on_with_no_open_issue_is_still_promoted_near_the_top(self):
        """REGRESSION. These were appended after the sort and sank to the bottom, which is the
        opposite of promoting them. A verb usually has no open issue because nobody has reached
        it yet, which is exactly when offering it is useful."""
        b = self.board([issue("add-story", 10)], after="explore")
        verbs = [o["verb"] for o in b["options"]]
        self.assertIn("create-style-pack", verbs)
        self.assertLess(verbs.index("create-style-pack"), verbs.index("add-story"))

    def test_an_unknown_after_verb_degrades_to_a_plain_board(self):
        b = self.board([issue("a", 5), issue("b", 1)], after="not-a-verb")
        self.assertEqual([o["verb"] for o in b["options"]], ["a", "b"])


class LabelsAreUsableVerbatim(unittest.TestCase):
    """The labels go straight into AskUserQuestion, so a malformed one reaches the operator."""

    def board(self, issues, **kw):
        with mock.patch.object(na, "grade", lambda u: fake(issues)):
            return na.board(pathlib.Path("/tmp/u"), **kw)

    def test_a_bare_verb_gets_the_slash_prefix(self):
        b = self.board([issue("shoot-references", 5)])
        self.assertTrue(b["options"][0]["label"].startswith("/abu:shoot-references"))

    def test_a_fix_THAT_IS_NOT_A_VERB_IS_NOT_PREFIXED(self):
        """REGRESSION. grade.py legitimately returns prose hints like
        'abu backfill-provenance (records what is knowable)' and
        'start-new-story-universe / edit universe.json'. Prefixing those produced
        '/abu:abu backfill-provenance (...)', which is not a command anyone can run."""
        for hint in ("abu backfill-provenance (records what is knowable)",
                     "start-new-story-universe / edit universe.json"):
            b = self.board([issue(hint, 3)])
            o = b["options"][0]
            self.assertNotIn("/abu:", o["label"], f"prefixed a non-verb: {o['label']}")
            self.assertIsNone(o["verb"])
            self.assertEqual(o["instruction"], hint)

    def test_every_description_says_what_it_is_worth(self):
        """The points are what make it a game rather than a menu."""
        b = self.board([issue("shoot-references", 7), issue("mystery-verb", 0)])
        self.assertIn("worth up to 7 point(s)", b["options"][0]["description"])
        self.assertIn("no open item scored", b["options"][1]["description"])

    def test_descriptions_start_capitalised_and_end_in_a_stop(self):
        b = self.board([issue("shoot-references", 5)])
        d = b["options"][0]["description"]
        self.assertTrue(d[0].isupper(), d)
        self.assertTrue(d.endswith("."), d)

    def test_the_score_is_carried_so_the_board_can_show_progress(self):
        b = self.board([issue("a", 1)])
        self.assertEqual(b["score"], 74)
        self.assertEqual(b["grade"], "C")
        self.assertEqual(b["to100"], 26)


class ItRefusesToAskForYou(unittest.TestCase):
    def test_it_tells_the_caller_not_to_use_a_preview(self):
        """A preview costs the visible Other row, and on a menu of next moves the real answer is
        often the fifth one, in the operator's head."""
        with mock.patch.object(na, "grade", lambda u: fake([issue("a", 1)])):
            b = na.board(pathlib.Path("/tmp/u"))
        self.assertIn("preview", b["askWith"].lower())
        self.assertIn("Other", b["askWith"])

    def test_the_script_does_not_call_askuserquestion_itself(self):
        """A script cannot know what else is in flight in the conversation. The asking belongs to
        the agent; this only arranges the options."""
        self.assertNotIn("AskUserQuestion(", SRC.read_text())


class WiredWhereTheWorkEnds(unittest.TestCase):
    def test_explore_prints_the_board_at_the_end_of_a_fan_out(self):
        src = (HERE.parents[1] / "explore" / "scripts" / "explore.py").read_text()
        self.assertIn("next_actions.py", src)
        self.assertIn('"--after", "explore"', src)

    def test_explore_never_fails_a_run_over_the_board(self):
        """The rolls cost money and are not reproducible. A board is a courtesy on top."""
        src = (HERE.parents[1] / "explore" / "scripts" / "explore.py").read_text()
        i = src.index("next_actions.py")
        self.assertIn("subprocess.call", src[i - 400:i + 400],
                      "must use call, not check_call: a board failure cannot abort a fan-out")

    def test_the_rule_is_written_where_an_agent_reads_it(self):
        """A catalog read at session start loses to an instruction read at the point of use."""
        md = (HERE.parent / "SKILL.md").read_text()
        self.assertIn("next_actions.py", md)
        self.assertIn("AskUserQuestion", md)
        self.assertIn("--after", md)


if __name__ == "__main__":
    unittest.main()
