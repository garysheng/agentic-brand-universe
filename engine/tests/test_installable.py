"""The repo must stay installable by a stranger.

Every previous gap in this project was invisible until someone tried it: a spec URL
that served nothing, provider scripts resolved out of one developer's home directory,
a marketplace nobody but the author could reach. This suite asserts the install path
mechanically so "installable" stops being a claim and becomes a check.
"""
import json
import unittest
from pathlib import Path

from agenticstory import providers

ROOT = providers.repo_root()
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
MARKET = ROOT / ".claude-plugin" / "marketplace.json"


class TestSelfMarketplace(unittest.TestCase):
    def test_manifests_exist(self):
        """Without these, the only install path is clone-and-symlink by hand."""
        self.assertTrue(PLUGIN.is_file(), "missing .claude-plugin/plugin.json")
        self.assertTrue(MARKET.is_file(), "missing .claude-plugin/marketplace.json")

    def test_manifests_parse(self):
        json.loads(PLUGIN.read_text())
        json.loads(MARKET.read_text())

    def test_plugin_is_named_abu(self):
        self.assertEqual(json.loads(PLUGIN.read_text())["name"], "abu")

    def test_marketplace_points_at_this_repo(self):
        entries = json.loads(MARKET.read_text())["plugins"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["source"], ".")
        self.assertEqual(entries[0]["name"], "abu")

    def test_the_plugin_payload_is_actually_here(self):
        """source '.' means skills/ and agents/ must sit at the repo root."""
        self.assertTrue((ROOT / "skills").is_dir())
        self.assertGreater(len(list((ROOT / "skills").glob("*/SKILL.md"))), 20)

    def test_front_door_and_installer_ship(self):
        for s in ("abu", "onboard"):
            self.assertTrue((ROOT / "skills" / s / "SKILL.md").is_file(), s)

    def test_version_is_a_release(self):
        v = json.loads(PLUGIN.read_text())["version"]
        self.assertRegex(v, r"^\d+\.\d+\.\d+$")


class TestNoDeadCitations(unittest.TestCase):
    def test_welcome_exists_and_teaches_no_commands(self):
        """WELCOME is what a stranger is sent. Its whole premise is that they type
        nothing, so a shell block in it is a defect, not a convenience."""
        w = (ROOT / "WELCOME.md")
        self.assertTrue(w.is_file())
        self.assertNotIn("```bash", w.read_text())

    def test_spec_urls_are_not_the_dead_domain(self):
        """agenticstory.wiki resolved to parked DNS and served nothing while being
        cited as the authority in every universe manifest."""
        from agenticstory import SPEC_WIKI, SPEC_URL
        for u in (SPEC_WIKI, SPEC_URL):
            self.assertNotIn("agenticstory.wiki", u)
            self.assertTrue(u.startswith("https://"))

    def test_providers_are_vendored_not_borrowed(self):
        for p in ("gpt-image-2", "nano-banana-pro"):
            self.assertEqual(providers.resolve(p),
                             ROOT / "providers" / p / "generate_image.py")


if __name__ == "__main__":
    unittest.main()
