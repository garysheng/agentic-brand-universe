"""The adapter's defaults, and the one kwarg that used to go missing.

These are cheap assertions about a parser, and they exist because both failures they
guard are SILENT. A stale model default keeps rendering, just on last year's model. A
dropped `quality` on the edit path keeps rendering too, at whatever the API picks, while
the provenance file written beside it names a tier nobody sent. Neither one raises, so
neither one gets noticed until somebody compares a plate to one made six months earlier
and cannot explain the difference.
"""
import ast
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "generate_image.py"
SOURCE = SCRIPT.read_text()


def default_for(flag: str):
    """The parser default for one flag, read off the AST rather than by running argparse.

    Importing the module would pull in the openai SDK, which the test runner has no key
    for and no reason to install. The parser is a literal, so read the literal.
    """
    tree = ast.parse(SOURCE)
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr != "add_argument" or not node.args:
            continue
        if not (isinstance(node.args[0], ast.Constant) and node.args[0].value == flag):
            continue
        for kw in node.keywords:
            if kw.arg == "default" and isinstance(kw.value, ast.Constant):
                return kw.value.value
        return None
    raise AssertionError(f"{flag} is not declared in {SCRIPT.name}")


class Defaults(unittest.TestCase):
    def test_model_is_a_current_openai_image_model(self):
        # Verified against /v1/models on 2026-09-09. Sunburst is the edit-precision sibling,
        # which is what an adapter that chains every render off locked plates needs.
        self.assertEqual(default_for("--model"), "gpt-image-2.5-sunburst")

    def test_quality_default_holds_the_fidelity_the_old_model_gave(self):
        # GPT Image 2.5's ladder gained xhigh and max, and the names moved under the old
        # ones: 2.5 `high` bills 1,372 output tokens at 1536x1024 where gpt-image-2 `high`
        # billed 5,488. Defaulting to `high` here would quietly buy a quarter of the plate
        # this framework used to make.
        self.assertEqual(default_for("--quality"), "max")

    def test_the_edit_path_sends_quality(self):
        # Almost everything ABU renders goes through images.edit, because passing locked
        # plates as references is how canon is held. quality was missing from those kwargs.
        start = SOURCE.index("client.images.edit")
        block = SOURCE[SOURCE.index("kwargs = dict(", 0, start):start]
        self.assertIn("quality=args.quality", block,
                      "images.edit kwargs must carry quality, or the recipe beside the "
                      "asset describes a render that never happened")

    def test_the_generate_path_still_sends_quality(self):
        block = SOURCE[SOURCE.index("generate_kwargs = dict("):SOURCE.index("client.images.generate")]
        self.assertIn("quality=args.quality", block)


if __name__ == "__main__":
    unittest.main()
