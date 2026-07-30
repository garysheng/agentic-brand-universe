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

    def test_marketplace_name_differs_from_plugin_name(self):
        """Naming both `abu` makes the install read `abu@abu`. The marketplace is the
        SOURCE; the plugin is the thing inside it."""
        m = json.loads(MARKET.read_text())
        self.assertNotEqual(m["name"], m["plugins"][0]["name"])

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


class TestPortability(unittest.TestCase):
    """Nothing a stranger installs may point into the author's home directory."""

    # evolve-abu is the MAINTAINER's skill: it edits the framework's own working
    # copy and is meaningless without it. Every other skill ships to strangers.
    MAINTAINER_ONLY = {"evolve-abu"}

    def _shipped(self):
        for f in sorted((ROOT / "skills").rglob("SKILL.md")):
            if f.parent.name not in self.MAINTAINER_ONLY:
                yield f
        for f in sorted((ROOT / "skills").rglob("*.py")):
            if "__pycache__" not in f.parts and f.parent.parent.name not in self.MAINTAINER_ONLY:
                yield f

    def test_no_personal_absolute_paths(self):
        bad = []
        for f in self._shipped():
            for i, line in enumerate(f.read_text().splitlines(), 1):
                if "Documents/github-repos" in line or "/Users/" in line:
                    bad.append(f"{f.relative_to(ROOT)}:{i}")
        self.assertEqual(bad, [], "personal paths in shipped skills:\n" + "\n".join(bad))

    def test_no_fixed_depth_engine_lookup(self):
        """A fixed parents[N] encodes ONE directory layout. This code runs from a
        git clone and from a plugin cache, and counting silently picks wrong."""
        bad = []
        for f in (ROOT / "skills").rglob("*.py"):
            # Test harnesses always run from a clone, never from a plugin cache,
            # so counting parents is safe there and only there.
            if "__pycache__" in f.parts or "tests" in f.parts:
                continue
            for i, line in enumerate(f.read_text().splitlines(), 1):
                if "parents[" in line and "engine" in line:
                    bad.append(f"{f.relative_to(ROOT)}:{i}: {line.strip()[:70]}")
        self.assertEqual(bad, [], "fixed-depth engine lookup:\n" + "\n".join(bad))

    def test_root_finder_walks_up_from_a_deep_path(self):
        import sys
        sys.path.insert(0, str(ROOT / "skills" / "abu" / "scripts"))
        import importlib
        status = importlib.import_module("status")
        deep = ROOT / "skills" / "abu" / "scripts" / "status.py"
        self.assertEqual(status._abu_root(deep), ROOT)
