#!/usr/bin/env python3
"""A vendored provider must be COMPLETE, not just present.

providers.resolve_str prefers the vendored copy under <repo>/providers/<id>/ over the
one in ~/.agents/skills. On 2026-07-30 generate_image.py was vendored WITHOUT its
prompt_guards.py sibling, so the preferred copy raised ModuleNotFoundError on import and
took precedence over the working one. Twelve renders failed in a row and the batch
reported success, because the failure was inside a subprocess log nobody parsed.
"""
import os, re, subprocess, sys, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROVIDERS = REPO / "providers"


class TestVendoredProvidersAreImportable(unittest.TestCase):
    def test_every_vendored_script_imports_cleanly(self):
        """Import the vendored script's local siblings, no API calls involved."""
        if not PROVIDERS.exists():
            self.skipTest("no vendored providers in this checkout")
        broken = []
        for script in sorted(PROVIDERS.glob("*/generate_image.py")):
            src = script.read_text()
            siblings = sorted({m for m in re.findall(r"^\s*(?:from|import)\s+(\w+)", src, re.M)
                               if (script.parent / f"{m}.py").exists()
                               or f"from {m} import" in src and not (script.parent / f"{m}.py").exists()
                               and m in ("prompt_guards",)})
            for mod in siblings:
                if not (script.parent / f"{mod}.py").exists():
                    broken.append((script.parent.name, f"missing sibling {mod}.py"))
                    continue
                r = subprocess.run([sys.executable, "-c",
                                    f"import sys; sys.path.insert(0, {str(script.parent)!r}); import {mod}"],
                                   capture_output=True, text=True)
                if r.returncode != 0:
                    broken.append((script.parent.name, (r.stderr.strip().splitlines() or ["?"])[-1]))
        self.assertEqual(broken, [],
                         "a vendored provider is missing or cannot import a sibling module; "
                         "vendor the whole directory, not one file")

    def test_vendored_dir_has_no_lone_generate_image(self):
        """The tell for an incomplete vendor: exactly one .py in the provider dir."""
        if not PROVIDERS.exists():
            self.skipTest("no vendored providers in this checkout")
        for d in sorted(p for p in PROVIDERS.iterdir() if p.is_dir()):
            pys = list(d.glob("*.py"))
            gen = d / "generate_image.py"
            if gen.exists():
                src = gen.read_text()
                needs_sibling = "from prompt_guards" in src or "import prompt_guards" in src
                if needs_sibling:
                    self.assertTrue((d / "prompt_guards.py").exists(),
                                    f"{d.name}: generate_image.py imports prompt_guards "
                                    "but the sibling was not vendored")


if __name__ == "__main__":
    unittest.main(verbosity=2)
