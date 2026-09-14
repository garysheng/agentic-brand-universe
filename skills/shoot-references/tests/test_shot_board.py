#!/usr/bin/env python3
"""shot_board.py: the board IS the delivery, and the escape must survive the layout.

Two properties are load-bearing and both are easy to lose:

  * every option carries a PREVIEW, because a reference shot is the case where the options
    ARE the artifact;
  * and therefore the visible `Other` row is not drawn, so the off-list answer has to sit
    in the question TEXT, where no layout can drop it.

The second only holds if the script writes it rather than the caller remembering to, so the
test is against the composed question, not against a docstring.
"""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "shot_board.py"
spec = importlib.util.spec_from_file_location("shot_board", SCRIPT)
sb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sb)

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "engine"))
from agenticstory import seen  # noqa: E402


def _universe(root: Path, invariants=("a scar over the left brow",)):
    (root / "canon" / "entities").mkdir(parents=True)
    (root / "reference" / "hero").mkdir(parents=True)
    (root / "canon" / "entities" / "hero.json").write_text(json.dumps({
        "id": "hero", "kind": "character",
        "structured": {"sheets": {"master": "reference/hero/m.png"},
                       "invariants": list(invariants)},
    }))
    return root


def _png(root: Path, name):
    p = root / "reference" / "hero" / name
    p.write_bytes(b"\x89PNG" + name.encode())
    return p


class Composition(unittest.TestCase):
    def test_every_option_carries_a_preview(self):
        with tempfile.TemporaryDirectory() as d:
            u = _universe(Path(d))
            p = _png(u, "m.png")
            q = sb.compose_question(p, json.loads((u / "canon" / "entities" / "hero.json").read_text()), u)
            self.assertTrue(q["options"])
            for o in q["options"]:
                self.assertTrue(o.get("preview"), o["label"])

    def test_the_off_list_answer_is_in_the_question_text(self):
        """THE TEST THAT FAILS WITHOUT THE FIX. A preview costs the visible Other row."""
        with tempfile.TemporaryDirectory() as d:
            u = _universe(Path(d))
            q = sb.compose_question(_png(u, "m.png"), {}, u)
            self.assertIn(sb.ESCAPE, q["question"])
            self.assertIn("say so in the chat", q["question"])

    def test_the_checklist_is_the_entity_s_own_invariants(self):
        with tempfile.TemporaryDirectory() as d:
            u = _universe(Path(d), invariants=["a scar over the left brow", "no hat, ever"])
            ent = json.loads((u / "canon" / "entities" / "hero.json").read_text())
            q = sb.compose_question(_png(u, "m.png"), ent, u)
            self.assertIn("no hat, ever", q["question"])
            self.assertIn("no hat, ever", q["options"][0]["preview"])

    def test_the_slot_name_comes_from_canon_not_from_the_filename(self):
        # An entity's id is not a promise about where its art lives (SPEC v0.33), and a
        # filename is a convention rather than a contract.
        with tempfile.TemporaryDirectory() as d:
            u = _universe(Path(d))
            ent = json.loads((u / "canon" / "entities" / "hero.json").read_text())
            q = sb.compose_question(_png(u, "m.png"), ent, u)
            self.assertEqual(q["shot"], "master")

    def test_a_matrix_is_chunked_into_boards_of_four(self):
        # AskUserQuestion takes four questions. A fifth is a shot the operator is told
        # about and cannot answer.
        with tempfile.TemporaryDirectory() as d:
            u = _universe(Path(d))
            pngs = [_png(u, f"s{n}.png") for n in range(9)]
            boards = sb.build(pngs, {}, u, "hero")
            self.assertEqual([len(b["questions"]) for b in boards], [4, 4, 1])
            self.assertEqual(len({b["boardId"] for b in boards}), 3)


class TheRecord(unittest.TestCase):
    def test_composing_a_board_stamps_every_shot_as_shown(self):
        with tempfile.TemporaryDirectory() as d:
            u = _universe(Path(d))
            pngs = [_png(u, f"s{n}.png") for n in range(3)]
            sb.build(pngs, {}, u, "hero")
            for p in pngs:
                self.assertTrue(seen.read_seen(p)["board"]["id"])

    def test_a_tap_with_no_board_exits_2_rather_than_recording(self):
        with tempfile.TemporaryDirectory() as d:
            u = _universe(Path(d))
            p = _png(u, "m.png")
            self.assertEqual(sb.main(["tap", str(p), "--verdict", "keep"]), 2)
            self.assertEqual(seen.read_seen(p), {})

    def test_the_happy_path_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            u = _universe(Path(d))
            p = _png(u, "m.png")
            self.assertEqual(sb.main(["board", str(p), "--universe", str(u),
                                      "--entity", "hero"]), 0)
            self.assertEqual(sb.main(["tap", str(p), "--verdict", "keep"]), 0)
            self.assertIsNone(seen.seen_problem(p))

    def test_a_reroll_tap_is_accepted_against_a_board_this_script_built(self):
        # The board stores the VERDICT TOKEN, never the label: a card reading "Re-roll"
        # records `reroll`, and comparing the two rejected a legitimate tap.
        with tempfile.TemporaryDirectory() as d:
            u = _universe(Path(d))
            p = _png(u, "m.png")
            sb.main(["board", str(p), "--universe", str(u), "--entity", "hero"])
            self.assertEqual(seen.read_seen(p)["board"]["options"], ["keep", "reroll"])
            self.assertEqual(seen.read_seen(p)["board"]["labels"], ["Keep", "Re-roll"])
            self.assertEqual(sb.main(["tap", str(p), "--verdict", "reroll",
                                      "--why", "screen on the wrong side"]), 0)
            self.assertIn("RE-ROLL", seen.seen_problem(p))

    def test_status_exits_nonzero_while_anything_is_unlockable(self):
        with tempfile.TemporaryDirectory() as d:
            u = _universe(Path(d))
            a, b = _png(u, "a.png"), _png(u, "b.png")
            sb.build([a, b], {}, u, "hero")
            seen.record_tap(a, "keep")
            self.assertEqual(sb.main(["status", str(a), str(b)]), 1)
            seen.record_tap(b, "keep")
            self.assertEqual(sb.main(["status", str(a), str(b)]), 0)

    def test_board_refuses_a_path_with_no_file(self):
        with tempfile.TemporaryDirectory() as d:
            u = _universe(Path(d))
            self.assertEqual(sb.main(["board", str(u / "reference" / "hero" / "nope.png")]), 2)


if __name__ == "__main__":
    unittest.main()
