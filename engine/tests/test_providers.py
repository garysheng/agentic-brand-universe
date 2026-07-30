"""Provider/engine resolution, and the portability rule it exists to enforce."""
import os
import re
import unittest
from pathlib import Path

from agenticstory import providers

ROOT = providers.repo_root()


class TestResolution(unittest.TestCase):
    def test_repo_root_is_the_framework(self):
        self.assertTrue((ROOT / "SPEC.md").is_file())
        self.assertTrue((ROOT / "providers").is_dir())

    def test_engine_dir_is_importable_path(self):
        self.assertTrue((providers.engine_dir() / "agenticstory" / "__init__.py").is_file())

    def test_both_providers_are_vendored(self):
        """A fresh clone must be able to draw. Vendoring is the whole fix."""
        for p in ("gpt-image-2", "nano-banana-pro"):
            self.assertTrue((ROOT / "providers" / p / "generate_image.py").is_file(), p)

    def test_vendored_copy_wins_over_legacy(self):
        for p in ("gpt-image-2", "nano-banana-pro"):
            self.assertEqual(providers.resolve(p), ROOT / "providers" / p / "generate_image.py")

    def test_env_override_wins_over_everything(self):
        key = providers.env_var("gpt-image-2")
        self.assertEqual(key, "ABU_PROVIDER_GPT_IMAGE_2")
        target = ROOT / "providers" / "nano-banana-pro" / "generate_image.py"
        old = os.environ.get(key)
        os.environ[key] = str(target)
        try:
            self.assertEqual(providers.resolve("gpt-image-2"), target)
        finally:
            os.environ.pop(key, None)
            if old is not None:
                os.environ[key] = old

    def test_unknown_provider_lists_what_it_tried(self):
        """'not found' with no search path is the error that costs an hour."""
        with self.assertRaises(FileNotFoundError) as cm:
            providers.resolve("no-such-provider")
        msg = str(cm.exception)
        self.assertIn("no-such-provider", msg)
        self.assertIn("Tried:", msg)
        self.assertIn("ABU_PROVIDER_NO_SUCH_PROVIDER", msg)


class TestNoHardcodedHomePaths(unittest.TestCase):
    """The regression that made the framework unrunnable on any other machine.

    Four scripts each hardcoded an absolute path into one developer's home
    directory. A fresh clone could validate canon and pass every test, then fail
    to generate a single image. Nothing may reintroduce that.
    """

    OFFENDER = re.compile(r'expanduser\(\s*["\']~/\.(agents|claude)/|/Users/[a-z]')

    def _sources(self):
        for base in ("skills", "engine"):
            for f in (ROOT / base).rglob("*.py"):
                if "__pycache__" in f.parts or f.parts[-2] == "tests":
                    continue
                yield f

    def test_no_script_hardcodes_a_home_directory(self):
        bad = []
        for f in self._sources():
            for i, line in enumerate(f.read_text().splitlines(), 1):
                if line.lstrip().startswith("#"):
                    continue  # prose about the old bug is allowed; code is not
                if self.OFFENDER.search(line):
                    bad.append(f"{f.relative_to(ROOT)}:{i}: {line.strip()[:90]}")
        self.assertEqual(bad, [], "hardcoded home paths reintroduced:\n" + "\n".join(bad))

    def test_legacy_paths_are_declared_not_scattered(self):
        """The old locations still work, but they live in ONE table."""
        self.assertIn("gpt-image-2", providers.LEGACY)
        self.assertTrue(any("chatgpt-images" in p for p in providers.LEGACY["gpt-image-2"]))


if __name__ == "__main__":
    unittest.main()
