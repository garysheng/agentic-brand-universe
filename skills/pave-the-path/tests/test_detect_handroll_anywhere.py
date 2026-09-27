"""detect_handroll runs outside a chain: from the cwd, or over a git diff (gap G28, #18).

The third PIL-montage hand-roll happened in a consuming repo (garysheng-books) that never
enters an ABU chain, so the detector never ran. A consuming repo must be able to run it as a
pre-commit or CI step over what it just changed.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "detect_handroll.py"
MONTAGE = ("from PIL import Image\nsheet = Image.new('RGB', (100, 100))\n"
           "for p in pngs:\n    sheet.paste(Image.open(p), (0, 0))\nsheet.save('contact.png')\n")


def git(cwd, *a):
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)


def run(cwd, *a):
    return subprocess.run([sys.executable, str(SCRIPT), *a], cwd=cwd,
                          capture_output=True, text=True)


class TestRunsAnywhere(unittest.TestCase):
    def test_no_argument_scans_the_current_directory(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "judge.py").write_text(MONTAGE)
            r = run(t)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("contact_sheet.py", r.stdout)

    def test_since_scans_only_what_the_diff_touched(self):
        with tempfile.TemporaryDirectory() as t:
            repo = Path(t)
            git(repo, "init", "-q", "-b", "main")
            git(repo, "config", "user.email", "t@example.com")
            git(repo, "config", "user.name", "t")
            (repo / "old.py").write_text(MONTAGE)          # a known, already-committed one
            git(repo, "add", "old.py")
            git(repo, "commit", "-q", "-m", "base")
            r = run(repo, "--since", "HEAD")
            self.assertEqual(r.returncode, 0, r.stdout)    # nothing changed since HEAD
            (repo / "new.py").write_text(MONTAGE)          # the session's new hand-roll
            r = run(repo, "--since", "HEAD")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("new.py", r.stdout)
            self.assertNotIn("old.py", r.stdout)

    def test_since_outside_a_repo_says_so(self):
        with tempfile.TemporaryDirectory() as t:
            r = run(t, "--since", "HEAD")
            self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
