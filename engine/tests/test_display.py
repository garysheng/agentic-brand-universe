"""Which surface a decision is shown on, and the honest degrade (SPEC v0.51).

The whole point of this module is that the two answers must not be interchangeable. A frapp
can serve the picture, so the record it produces is a fact; a text card cannot, so the record
it produces has to SAY it is about a filename. Every test here pins one half of that.

Nothing in this file starts a frapp, opens a browser or touches the network. The resolver is
the only thing under test, and it is a pure function of the environment.
"""
import pathlib
import tempfile
import unittest

from agenticstory import display


def _fake_freedom(root, versions=("4.9.0", "4.269.0")):
    """A cache dir shaped like a Freedom install, with the one file the resolver looks for."""
    for v in versions:
        lib = pathlib.Path(root) / v / ".agents" / "lib"
        lib.mkdir(parents=True, exist_ok=True)
        (lib / display.LIB_FILE).write_text("// not the real library, just its shape")
    return {"FREEDOM_CACHE_DIR": str(root)}


class WhereTheLibraryIs(unittest.TestCase):
    def test_the_newest_install_wins_and_it_is_not_a_string_sort(self):
        # 4.269.0 is newer than 4.9.0 and sorts before it as a string. A frapp resolved
        # against the wrong one imports a library the operator has already replaced.
        with tempfile.TemporaryDirectory() as root:
            env = _fake_freedom(root)
            self.assertEqual(display.freedom_lib(env=env).parts[-4], "4.269.0")

    def test_no_install_is_none_rather_than_a_guess(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(display.freedom_lib(env={"FREEDOM_CACHE_DIR": root}))

    def test_a_dev_checkout_overrides_the_cache(self):
        # The maintainer's own machine runs the library from a checkout, and a frapp that
        # ignored it would test the shipped copy rather than the change being made.
        with tempfile.TemporaryDirectory() as root:
            lib = pathlib.Path(root) / "lib"
            lib.mkdir()
            (lib / display.LIB_FILE).write_text("// dev")
            self.assertEqual(display.freedom_lib(env={display.ENV_LIB: str(lib)}).parent, lib)


class WhichChannel(unittest.TestCase):
    def test_a_freedom_install_and_node_give_the_frapp(self):
        with tempfile.TemporaryDirectory() as root:
            env = _fake_freedom(root)
            env["ABU_NODE"] = "/bin/sh"          # any real binary: node's presence is the test
            self.assertEqual(display.resolve_channel(env=env), (display.FRAPP, ""))

    def test_no_freedom_install_degrades_to_the_card_and_says_why(self):
        """THE TEST THAT FAILS WITHOUT THE FIX: a machine that cannot show the art must not
        produce the same answer as one that can."""
        with tempfile.TemporaryDirectory() as root:
            channel, why = display.resolve_channel(
                env={"FREEDOM_CACHE_DIR": root, "ABU_NODE": "/bin/sh"})
            self.assertEqual(channel, display.CARD)
            self.assertIn("no Freedom install", why)
            # It must say what the card cannot do, or the record carries a shrug.
            self.assertIn("cannot carry the picture", why)

    def test_no_node_degrades_to_the_card_because_a_frapp_is_a_node_program(self):
        with tempfile.TemporaryDirectory() as root:
            env = _fake_freedom(root)
            env["ABU_NODE"] = str(pathlib.Path(root) / "no-such-node")
            channel, why = display.resolve_channel(env=env)
            self.assertEqual(channel, display.CARD)
            self.assertIn("no `node`", why)

    def test_the_channel_can_be_forced_to_the_card_and_the_record_names_the_force(self):
        # A test suite and a headless run both need this, and it is not an off switch: an
        # approval taken on the card channel is recorded as unshown whatever set it.
        with tempfile.TemporaryDirectory() as root:
            env = _fake_freedom(root)
            env.update({"ABU_NODE": "/bin/sh", "ABU_DISPLAY_CHANNEL": "card"})
            channel, why = display.resolve_channel(env=env)
            self.assertEqual(channel, display.CARD)
            self.assertIn("ABU_DISPLAY_CHANNEL=card", why)


class ThePendingRecord(unittest.TestCase):
    def test_a_pending_record_is_never_already_served(self):
        # Only the page that sends the bytes may flip this, which is the reason the whole
        # mechanism is not another attestation.
        self.assertFalse(display.pending(display.FRAPP)["served"])
        self.assertFalse(display.pending(display.CARD, "no install")["served"])

    def test_the_card_record_carries_its_reason_and_the_frapp_record_has_none_to_carry(self):
        self.assertEqual(display.pending(display.CARD, "no install")["why"], "no install")
        self.assertNotIn("why", display.pending(display.FRAPP))

    def test_an_unknown_channel_is_refused(self):
        with self.assertRaises(ValueError):
            display.pending("preview")


if __name__ == "__main__":
    unittest.main()
