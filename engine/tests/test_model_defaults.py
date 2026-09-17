"""No render path may draw with, record, or replay a superseded image model on its own.

Earned 2026-09-16. The `gpt-image-2` adapter moved to gpt-image-2.5-sunburst on 2026-09-09,
with a test pinning its default. A week later three scripts one layer up still typed the old
name: compose-spread and shoot-references stamped `"model": "gpt-image-2"` into the recipe of
every 2.5 render, and reroll-slot replayed that recorded name with `--model`, so re-rolling a
spread quietly went back to the old model. Every render succeeded, which is why nothing
noticed. The adapter's own test could not see it, because the defect was never in the adapter.

So this guards the whole population rather than one file: the adapter's default must be a
current model, and no executable line anywhere in the render path may name a superseded model
as a value it USES. Recipes that already say gpt-image-2 are history and are not touched.
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "engine"))

from agenticstory import providers  # noqa: E402

# Where render code lives. Tests are excluded: a fixture recipe saying "gpt-image-2" is a
# faithful copy of an old recipe on disk, which is exactly what reroll must handle.
SCANNED = [
    *sorted((ROOT / "skills").glob("*/scripts/*.py")),
    *sorted((ROOT / "engine" / "agenticstory").glob("*.py")),
    *sorted((ROOT / "providers").glob("*/*.py")),
]

OLD = r"(?:gpt-image-(?!2\.5)[0-9][\w.-]*|dall-e-[23])"
# The three shapes a USED model takes in this codebase. Naming the PROVIDER id
# ("gpt-image-2" handed to resolve_str / _provider_script / provider=) is not a model and
# does not match any of these.
USES_A_MODEL = [
    re.compile(r'["\']model["\']\s*:\s*["\']' + OLD + r'["\']'),          # "model": "gpt-image-2"
    re.compile(r'--model["\']\s*,\s*(?:default\s*=\s*)?["\']' + OLD + r'["\']'),  # --model default
    re.compile(r'model\s*=\s*["\']' + OLD + r'["\']'),                     # model="gpt-image-2"
    re.compile(r'model["\']\)\s*or\s*["\']' + OLD + r'["\']'),             # .get("model") or "..."
]


def executable_lines(path: Path):
    """(lineno, text) for lines that are not comments or docstring body."""
    in_doc = False
    for n, line in enumerate(path.read_text().splitlines(), 1):
        s = line.strip()
        quotes = s.count('"""') + s.count("'''")
        if in_doc:
            if quotes % 2 == 1:
                in_doc = False
            continue
        if s.startswith(('"""', "'''")):
            if quotes % 2 == 1:
                in_doc = True
            continue
        if s.startswith("#"):
            continue
        yield n, line


class AdapterDefaultIsCurrent(unittest.TestCase):
    def test_the_adapter_default_is_a_gpt_image_2_5_model(self):
        model = providers.adapter_default_model("gpt-image-2")
        self.assertTrue(model.startswith("gpt-image-2.5"),
                        f"the adapter now defaults to {model!r}; every ABU render and the art "
                        f"universe inherit it. The operator asked for 2.5 everywhere.")

    def test_the_adapter_default_is_never_a_superseded_model(self):
        self.assertNotIn(providers.adapter_default_model("gpt-image-2"),
                         providers.SUPERSEDED_MODELS)

    def test_gpt_image_2_is_superseded(self):
        self.assertIn("gpt-image-2", providers.SUPERSEDED_MODELS)
        self.assertNotIn("gpt-image-2.5-sunburst", providers.SUPERSEDED_MODELS)
        self.assertNotIn("gpt-image-2.5-flare", providers.SUPERSEDED_MODELS)

    def test_an_unreadable_adapter_raises_rather_than_guessing(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            fake = Path(td) / "generate_image.py"
            fake.write_text("print('no parser here')\n")
            key = providers.env_var("gpt-image-2")
            old = os.environ.get(key)
            os.environ[key] = str(fake)
            try:
                with self.assertRaises(LookupError):
                    providers.adapter_default_model("gpt-image-2")
            finally:
                if old is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old


class NoScriptReachesForASupersededModel(unittest.TestCase):
    def test_the_scan_actually_covers_the_render_path(self):
        names = {p.name for p in SCANNED}
        for must in ("render_spread.py", "chain_matrix.py", "reroll_from_recipe.py",
                     "generate.py", "render_cover.py", "generate_image.py", "providers.py"):
            self.assertIn(must, names, f"{must} fell out of the scan; the guard is blind to it")

    def test_the_patterns_catch_the_shapes_that_actually_shipped(self):
        # Each of these is a line that was really in the repo before 2026-09-16.
        shipped = [
            '        "model": "gpt-image-2",',
            '        "model": "gpt-image-2", "size": shot_size, "prompt": prompt,',
            '            "model": sr.get("model") or "gpt-image-2",',
            '    ap.add_argument("--model", default="gpt-image-2",',
        ]
        for line in shipped:
            self.assertTrue(any(p.search(line) for p in USES_A_MODEL), line)
        for fine in ('    gen = ["uv", "run", resolve_str("gpt-image-2"), "--prompt", p]',
                     'def _provider_script(provider="gpt-image-2"):',
                     '    ap.add_argument("--model", default="gpt-image-2.5-sunburst",'):
            self.assertFalse(any(p.search(fine) for p in USES_A_MODEL), fine)

    def test_no_executable_line_uses_a_superseded_model(self):
        offenders = []
        for path in SCANNED:
            for n, line in executable_lines(path):
                if any(p.search(line) for p in USES_A_MODEL):
                    offenders.append(f"{path.relative_to(ROOT)}:{n}: {line.strip()}")
        self.assertEqual(
            offenders, [],
            "a render script names a superseded model as a value it uses. Record the model "
            "the adapter reported, or ask agenticstory.providers.adapter_default_model(); "
            "never type a model name.\n  " + "\n  ".join(offenders))


if __name__ == "__main__":
    unittest.main()
