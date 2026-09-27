"""check_delivery.py measures against the branch INSTALLS track, not the checked-out one.

A release pushed from a worktree with `git push origin HEAD:master` read as NO-REMOTE, and a
feature branch pushed only to origin/feature would have read as STALE-CACHE, telling Gary to
`/plugin update` for work that never reached master.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_delivery.py"


def git(cwd, *a):
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True)


class TestTargetsTheDefaultBranch(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        t = Path(self.t.name)
        self.origin = t / "origin.git"
        git(t, "init", "-q", "--bare", "-b", "master", str(self.origin))
        self.repo = t / "repo"
        git(t, "clone", "-q", str(self.origin), str(self.repo))
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        (self.repo / ".claude-plugin").mkdir()
        self.bump("1.0.0")
        git(self.repo, "push", "-q", "origin", "HEAD:master")
        git(self.repo, "remote", "set-head", "origin", "master")
        self.home = t / "home"
        self.home.mkdir()

    def tearDown(self):
        self.t.cleanup()

    def bump(self, v):
        (self.repo / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "abu", "version": v}))
        git(self.repo, "add", ".claude-plugin/plugin.json")
        git(self.repo, "commit", "-q", "-m", v)

    def check(self):
        env = dict(os.environ, HOME=str(self.home))
        r = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.repo), "--json"],
                           capture_output=True, text=True, env=env)
        return r.returncode, json.loads(r.stdout)

    def test_a_feature_branch_pushed_only_to_itself_is_still_yours(self):
        git(self.repo, "checkout", "-q", "-b", "feature")
        self.bump("1.1.0")
        git(self.repo, "push", "-q", "origin", "feature")
        rc, st = self.check()
        self.assertEqual(rc, 1, st)
        self.assertEqual(st["verdict"], "UNPUSHED")

    def test_a_worktree_branch_pushed_to_master_is_published(self):
        git(self.repo, "checkout", "-q", "-b", "worktree-agent-x")
        self.bump("1.1.0")
        git(self.repo, "push", "-q", "origin", "HEAD:master")
        rc, st = self.check()
        self.assertEqual(rc, 2, st)                       # Gary's move: nothing installed here
        self.assertEqual(st["verdict"], "NOT-INSTALLED")
        self.assertEqual(st["remote"], "1.1.0")


if __name__ == "__main__":
    unittest.main()
