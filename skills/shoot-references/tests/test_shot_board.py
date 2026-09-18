#!/usr/bin/env python3
"""shot_board.py: the board must SHOW the art, and the fallback must admit that it does not.

Three properties are load-bearing:

  * on a machine with Freedom, the board is a FRAPP, which serves the picture and records
    having served it, so no verdict rests on anybody's claim about what was displayed;
  * on a machine without one it falls back to AskUserQuestion cards, and every approval taken
    there is recorded as `unshown` with the reason, so the two records cannot be confused;
  * on the card path every option still carries a PREVIEW, which costs the visible `Other`
    row, so the off-list answer sits in the question TEXT where no layout can drop it.

NOTHING HERE STARTS A FRAPP. The channel is forced to `card` for the whole module and the
frapp path is exercised with a fake launcher, because a test that opens a browser, takes
:443 on the operator's tailnet and leaves a detached node process behind is a test that
changes the machine it runs on. (Earned in this file's own first run, 2026-09-14: two stray
frapps and a live tailnet mapping.)
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ["ABU_DISPLAY_CHANNEL"] = "card"

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "shot_board.py"
spec = importlib.util.spec_from_file_location("shot_board", SCRIPT)
sb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sb)

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "engine"))
from agenticstory import display, seen  # noqa: E402

CARD = display.pending(display.CARD, "no Freedom install on this machine.")
FRAPP_URLS = {"ok": True, "mac": "http://127.0.0.1:7462/?k=abc",
              "phone": "https://box.ts.net/abu-shot-board/?k=def", "pid": 4242,
              "log": "/tmp/frapp.log"}


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


def _json_of(argv):
    """Run a command and parse its --json payload off stdout."""
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = sb.main(argv)
    assert code == 0, buf.getvalue()
    return json.loads(buf.getvalue())


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
            boards = sb.build(pngs, {}, u, "hero", CARD)
            self.assertEqual([len(b["questions"]) for b in boards], [4, 4, 1])
            self.assertEqual(len({b["boardId"] for b in boards}), 3)


class TheRecord(unittest.TestCase):
    def test_composing_a_board_stamps_every_shot_as_shown(self):
        with tempfile.TemporaryDirectory() as d:
            u = _universe(Path(d))
            pngs = [_png(u, f"s{n}.png") for n in range(3)]
            sb.build(pngs, {}, u, "hero", CARD)
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
            sb.build([a, b], {}, u, "hero", CARD)
            seen.record_tap(a, "keep")
            self.assertEqual(sb.main(["status", str(a), str(b)]), 1)
            seen.record_tap(b, "keep")
            self.assertEqual(sb.main(["status", str(a), str(b)]), 0)

    def test_board_refuses_a_path_with_no_file(self):
        with tempfile.TemporaryDirectory() as d:
            u = _universe(Path(d))
            self.assertEqual(sb.main(["board", str(u / "reference" / "hero" / "nope.png")]), 2)


class TheFrappChannel(unittest.TestCase):
    """With Freedom installed the board is a page that SERVES the picture, so the record is
    the page's own account of what it sent rather than an agent's account of what it showed."""

    def _frapp(self, launcher):
        """The frapp channel with a FAKE launcher: the resolver would say `card` here,
        because the module forces it, and nothing may actually start a page."""
        return (mock.patch.object(sb, "launch_frapp", launcher),
                mock.patch.object(sb.display, "resolve_channel",
                                  lambda: (sb.display.FRAPP, "")))

    def test_the_board_opens_the_page_and_hands_back_the_phone_link(self):
        """THE TEST THAT FAILS WITHOUT THE FIX: the v0.50 board handed back text only, so the
        art reached the operator only if somebody remembered to send it."""
        with tempfile.TemporaryDirectory() as d:
            u = _universe(Path(d))
            p = _png(u, "m.png")
            a, b = self._frapp(lambda *_a, **_k: dict(FRAPP_URLS))
            with a, b:
                out = _json_of(["board", str(p), "--universe", str(u), "--entity", "hero",
                                "--json"])
            self.assertEqual(out["channel"], "frapp")
            self.assertEqual(out["frapp"]["phone"], FRAPP_URLS["phone"])
            # A frapp link goes to the operator's PHONE, by text, every time.
            self.assertIn("message-myself", out["textIt"])
            disp = seen.read_seen(p)["board"]["display"]
            self.assertEqual(disp["channel"], "frapp")
            self.assertFalse(disp["served"])      # the page flips this, nothing else may

    def test_a_keep_is_refused_until_the_page_has_served_the_picture(self):
        with tempfile.TemporaryDirectory() as d:
            u = _universe(Path(d))
            p = _png(u, "m.png")
            a, b = self._frapp(lambda *_a, **_k: dict(FRAPP_URLS))
            with a, b:
                sb.main(["board", str(p), "--universe", str(u), "--entity", "hero"])
            self.assertEqual(sb.main(["tap", str(p), "--verdict", "keep"]), 2)
            self.assertIsNone(seen.read_seen(p).get("verdict"))
            # ...and the serve is what unblocks it, recorded through the same script the
            # frapp calls, because the engine owns the vocabulary and the page owns nothing.
            self.assertEqual(sb.main(["served", str(p), "--digest", seen.digest(p)]), 0)
            self.assertEqual(sb.main(["tap", str(p), "--verdict", "keep"]), 0)
            self.assertIsNone(seen.seen_problem(p))
            self.assertIsNone(seen.seen_caveat(p))

    def test_a_served_record_for_bytes_the_file_does_not_have_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            u = _universe(Path(d))
            p = _png(u, "m.png")
            a, b = self._frapp(lambda *_a, **_k: dict(FRAPP_URLS))
            with a, b:
                sb.main(["board", str(p), "--universe", str(u), "--entity", "hero"])
            self.assertEqual(sb.main(["served", str(p), "--digest", "0" * 16]), 2)

    def test_a_frapp_that_will_not_start_degrades_to_the_card_and_records_why(self):
        """THE TEST THAT FAILS WITHOUT THE FIX: without the re-stamp the board would claim
        the frapp channel while nothing was ever served, and every keep would be refused with
        no route out of it."""
        with tempfile.TemporaryDirectory() as d:
            u = _universe(Path(d))
            p = _png(u, "m.png")
            a, b = self._frapp(lambda *_a, **_k: {"ok": False, "why": "port 7462 is wedged"})
            with a, b:
                out = _json_of(["board", str(p), "--universe", str(u), "--entity", "hero",
                                "--json"])
            self.assertEqual(out["channel"], "card")
            self.assertIn("port 7462 is wedged", out["unshown"])
            self.assertEqual(sb.main(["tap", str(p), "--verdict", "keep"]), 0)
            self.assertIn("port 7462 is wedged", seen.read_seen(p)["unshown"]["why"])


class ThePageItself(unittest.TestCase):
    """The frapp is a shipped artifact of this skill, so its two contracts are tested here
    rather than left to whoever next opens it."""

    SRC = (Path(__file__).resolve().parents[1] / "frapps" / "shot-board.mjs").read_text()

    def test_it_exists_and_parses(self):
        node = display.node()
        if not node:
            self.skipTest("no node on this machine")
        r = subprocess.run([node, "--check",
                            str(Path(__file__).resolve().parents[1] / "frapps" / "shot-board.mjs")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_every_write_goes_through_this_script_and_none_through_the_sidecar(self):
        # Two copies of the refusals -- never boarded, off the board, no reason, bytes
        # changed, never served -- would disagree with lock-shot within a month.
        self.assertIn("SHOT_BOARD", self.SRC)
        self.assertIn('py(["served"', self.SRC)
        self.assertIn('py(["tap"', self.SRC)
        self.assertNotIn("writeFileSync(sidecar", self.SRC)

    def test_it_resolves_the_freedom_library_at_start_rather_than_pinning_a_version(self):
        # A frapp that imported from a versioned cache path died the day the next plugin
        # update deleted that directory (freedom#106).
        self.assertIn("freedomLib", self.SRC)
        self.assertIn("versions.at(-1)", self.SRC)
        self.assertNotIn("/freedom/4.", self.SRC)

    def test_it_vendors_no_part_of_the_frapp_library(self):
        # The token gate, the tailnet route, the journal and the design system are Freedom's.
        for owned in ("function serveFrapp", "function shell(", "createServer("):
            self.assertNotIn(owned, self.SRC)

    def test_the_serve_records_the_route_it_served_rather_than_the_filename(self):
        # A record that states a URL nothing serves is a small lie in the one file whose job
        # is being true about what happened.
        self.assertIn("`/shot/${encodeURIComponent(key)}`", self.SRC)

    def test_the_serve_is_recorded_after_the_bytes_leave_never_before(self):
        i = self.SRC.index('res.on("finish"')
        self.assertLess(i, self.SRC.index("res.end(bytes)"))
        self.assertIn("recordServe(img, digest,", self.SRC)



class FrappCardsAreTellable(unittest.TestCase):
    """Two takes of one shot must never look the same on a card, and one board serves every
    batch. Earned 2026-09-18: four boards stacked on one store slug, each with a card named
    only by shot, and the operator asked which full body was the new one.

    The proxy through the store rejects any path with a file extension as a static asset, and
    the board's page cannot know the store's prefix, so every URL it builds is relative and
    keyed by the shot's stem.
    """

    SRC = (Path(__file__).resolve().parents[1] / "frapps" / "shot-board.mjs").read_text()

    def test_a_card_says_which_take_and_when_it_was_rendered(self):
        self.assertIn("take ${i.take}", self.SRC)
        self.assertIn("rendered ${esc(i.rendered)}", self.SRC)
        self.assertIn('"rejected"', self.SRC, "the take number is counted from rejected/<shot>-*.png")

    def test_the_queue_is_the_entity_folder_not_the_launch_list(self):
        self.assertIn('join(UNIVERSE, "reference", ENTITY)', self.SRC)
        self.assertIn("readdirSync(dir, { withFileTypes: true })", self.SRC, "the entity folder AND each look folder one level down")

    def test_urls_are_relative_and_keyed_by_stem(self):
        self.assertNotIn('src="${base}/shot/', self.SRC, "an absolute /shot/ URL breaks under the store's prefix")
        self.assertIn("at(base, `shot/", self.SRC)
        self.assertIn("basename(r.img).replace(/\\.[^.]+$/, \"\")", self.SRC,
                      "a key with an extension is served as a static asset by the store and 404s")
        self.assertNotIn("/shot/(\\d+)", self.SRC, "index routing dies the moment the queue changes under a live page")


class OneBoardPerEntity(unittest.TestCase):
    """A second `board` call for the same entity reuses the page that is already up."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._records = mock.patch.object(sb, "BOARD_RECORDS", Path(self.tmp))
        self._records.start()

    def tearDown(self):
        self._records.stop()

    def test_a_live_board_is_reused_and_no_second_process_starts(self):
        rec = {"pid": os.getpid(), "mac": "http://127.0.0.1:7462/?k=x", "phone": None, "log": "/tmp/x"}
        sb._remember_board("desi", rec)
        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("must not start a second board")):
            out = sb.launch_frapp([Path("/tmp/a.png")], Path("/tmp/u"), "desi")
        self.assertTrue(out["ok"])
        self.assertTrue(out["reused"])
        self.assertEqual(out["mac"], rec["mac"])

    def test_a_dead_board_is_not_reused(self):
        sb._remember_board("desi", {"pid": 2**22 + 12345, "mac": "http://127.0.0.1:7462/?k=x"})
        self.assertIsNone(sb.live_board("desi"))

    def test_no_entity_means_no_reuse(self):
        rec = {"pid": os.getpid(), "mac": "http://127.0.0.1:7462/?k=x"}
        sb._remember_board(None, rec)
        # No universe/entity: the launcher must not consult the record at all.
        with mock.patch.object(sb, "live_board", side_effect=AssertionError("must not be consulted")):
            with mock.patch.object(sb.display, "node", return_value=None):
                out = sb.launch_frapp([Path("/tmp/a.png")], None, None)
        self.assertFalse(out["ok"])

if __name__ == "__main__":
    unittest.main()
