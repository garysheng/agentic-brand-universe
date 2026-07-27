"""
Tests for `agenticstory land` — merging finished work home without corrupting a
sibling agent session.

These build REAL git repos in a temp dir rather than mocking git, because every
hazard here is a real git behaviour (a branch checked out in a second worktree,
a dirty index, a conflicting merge) and a mock would happily assert the wrong
thing. The whole point of the module is what git actually does.

The load-bearing test is `test_busy_target_is_never_touched`: it proves that a
sibling worktree with staged changes is left byte-for-byte alone, which is the
exact failure that made every previous run park its branch instead.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE_DIR))

from agenticstory import land  # noqa: E402


def git(repo, *args, check=True):
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and p.returncode != 0:
        raise AssertionError(f"git {' '.join(args)}: {p.stderr or p.stdout}")
    return p.stdout.strip()


def write(repo, name, text):
    (Path(repo) / name).write_text(text)


class LandTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "--quiet", "--initial-branch=main")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "T")
        write(self.repo, "README.md", "base\n")
        git(self.repo, "add", "README.md")
        git(self.repo, "commit", "--quiet", "-m", "base")

    def tearDown(self):
        self._tmp.cleanup()

    def make_work_branch(self, name="work", filename="work.txt", body="work\n"):
        """A committed work branch in its own worktree, the shape a real run leaves."""
        wt = self.root / f"wt-{name}"
        git(self.repo, "worktree", "add", "--quiet", "-b", name, str(wt), "main")
        git(wt, "config", "user.email", "t@example.com")
        git(wt, "config", "user.name", "T")
        write(wt, filename, body)
        git(wt, "add", filename)
        git(wt, "commit", "--quiet", "-m", f"add {filename}")
        return wt

    # ---------------------------------------------------------------- FREE

    def test_free_target_is_merged_in_a_temp_worktree(self):
        """main is checked out nowhere-but-the-main-checkout, so it just merges."""
        wt = self.make_work_branch()
        # Move the main checkout off `main` so the target is genuinely free.
        git(self.repo, "checkout", "--quiet", "-b", "parking")
        res = land.land(self.repo, "work")
        self.assertEqual(res.outcome, "merged", res.detail)
        self.assertIn("work.txt", git(self.repo, "ls-tree", "--name-only", "main"))
        # cleanup happened
        self.assertFalse(wt.exists(), "the work worktree should be removed after landing")
        self.assertNotIn("work", git(self.repo, "branch", "--format=%(refname:short)").split())

    def test_free_target_leaves_no_temp_worktree_behind(self):
        self.make_work_branch()
        git(self.repo, "checkout", "--quiet", "-b", "parking")
        land.land(self.repo, "work")
        listed = git(self.repo, "worktree", "list")
        self.assertNotIn("agenticstory-land-", listed)

    # ---------------------------------------------------------------- IDLE

    def test_idle_target_merges_in_its_own_worktree_and_updates_its_files(self):
        """main checked out in a CLEAN worktree: merge there, files and ref move together."""
        self.make_work_branch()
        res = land.land(self.repo, "work")
        self.assertEqual(res.outcome, "merged", res.detail)
        # The holder's working tree really has the file, not just the ref.
        self.assertTrue((self.repo / "work.txt").exists(),
                        "merging in the holding worktree must update its files too")

    # ---------------------------------------------------------------- BUSY

    def test_busy_target_is_never_touched(self):
        """THE load-bearing case. A dirty sibling holding main must be left alone."""
        self.make_work_branch()
        write(self.repo, "their-file.txt", "someone else's in-flight work\n")
        git(self.repo, "add", "their-file.txt")  # staged, i.e. a live session
        before_head = git(self.repo, "rev-parse", "main")
        before_status = git(self.repo, "status", "--porcelain")

        res = land.land(self.repo, "work")

        self.assertEqual(res.outcome, "queued", res.detail)
        self.assertEqual(before_head, git(self.repo, "rev-parse", "main"),
                         "main must not move while a session holds it dirty")
        self.assertEqual(before_status, git(self.repo, "status", "--porcelain"),
                         "the other session's index must be untouched")
        self.assertFalse((self.repo / "work.txt").exists())
        # and the intent was recorded
        self.assertEqual([(i["branch"], i["onto"]) for i in land.read_queue(self.repo)],
                         [("work", "main")])

    def test_operation_in_progress_also_counts_as_busy(self):
        self.make_work_branch()
        (Path(git(self.repo, "rev-parse", "--path-format=absolute", "--git-dir")) / "MERGE_HEAD").write_text("x\n")
        res = land.land(self.repo, "work")
        self.assertEqual(res.outcome, "queued")
        self.assertIn("MERGE_HEAD", res.detail)

    def test_untracked_files_do_not_block_a_merge(self):
        """Stray untracked scratch output is normal and must not park the branch."""
        self.make_work_branch()
        write(self.repo, "scratch.log", "noise\n")
        res = land.land(self.repo, "work")
        self.assertEqual(res.outcome, "merged", res.detail)

    # ---------------------------------------------------------------- queue

    def test_queue_drains_on_a_later_run(self):
        """The self-healing property: the next run finishes the parked merge."""
        self.make_work_branch()
        write(self.repo, "their-file.txt", "in flight\n")
        git(self.repo, "add", "their-file.txt")
        self.assertEqual(land.land(self.repo, "work").outcome, "queued")

        # the other session finishes and commits
        git(self.repo, "commit", "--quiet", "-m", "their work")

        results = land.drain(self.repo)
        self.assertEqual([r.outcome for r in results], ["merged"], results[0].detail)
        self.assertIn("work.txt", git(self.repo, "ls-tree", "--name-only", "main"))
        self.assertEqual(land.read_queue(self.repo), [])

    def test_drain_drops_entries_whose_branch_vanished(self):
        self.make_work_branch()
        land.enqueue(self.repo, "ghost", "main", "test", True, True)
        results = land.drain(self.repo)
        self.assertTrue(any(r.branch == "ghost" and r.outcome == "already-merged" for r in results))
        self.assertFalse(any(i["branch"] == "ghost" for i in land.read_queue(self.repo)))

    def test_queue_survives_corruption(self):
        land.queue_path(self.repo).write_text("{ not json")
        self.assertEqual(land.read_queue(self.repo), [])

    # ---------------------------------------------------------------- conflicts

    def test_conflict_aborts_and_changes_nothing(self):
        wt = self.make_work_branch(filename="README.md", body="from the branch\n")
        # main moves in an incompatible way
        write(self.repo, "README.md", "from main\n")
        git(self.repo, "add", "README.md")
        git(self.repo, "commit", "--quiet", "-m", "main edit")
        before = git(self.repo, "rev-parse", "main")

        res = land.land(self.repo, "work")

        self.assertEqual(res.outcome, "conflict", res.detail)
        self.assertEqual(before, git(self.repo, "rev-parse", "main"))
        self.assertEqual("", git(self.repo, "status", "--porcelain", "--untracked-files=no"),
                         "a conflicted merge must be fully aborted, leaving a clean tree")
        self.assertTrue(wt.exists(), "the work must be preserved for the human")

    # ---------------------------------------------------------------- misc

    def test_already_merged_is_a_success_and_cleans_up(self):
        wt = self.make_work_branch()
        land.land(self.repo, "work", remove_worktree=False, delete_branch=False)
        res = land.land(self.repo, "work")
        self.assertEqual(res.outcome, "already-merged")
        self.assertFalse(wt.exists())

    def test_dirty_work_branch_is_refused(self):
        """We land FINISHED work. Uncommitted changes on the branch are not finished."""
        wt = self.make_work_branch()
        write(wt, "work.txt", "half-done edit\n")
        res = land.land(self.repo, "work")
        self.assertEqual(res.outcome, "queued")
        self.assertIn("uncommitted", res.detail)

    def test_refuses_to_land_a_branch_onto_itself(self):
        res = land.land(self.repo, "main", onto="main")
        self.assertEqual(res.outcome, "error")

    def test_default_target_prefers_main_then_master(self):
        self.assertEqual(land.default_target(self.repo), "main")
        git(self.repo, "branch", "-m", "main", "master")
        self.assertEqual(land.default_target(self.repo), "master")

    def test_stale_worktrees_reports_merged_leftovers(self):
        wt = self.make_work_branch()
        land.land(self.repo, "work", remove_worktree=False, delete_branch=False)
        stale = land.stale_worktrees(self.repo)
        self.assertEqual([w.path for w in stale], [wt])

    def test_prune_stale_removes_only_merged_clean_worktrees(self):
        wt_done = self.make_work_branch("done", "done.txt")
        wt_busy = self.make_work_branch("busy", "busy.txt")
        land.land(self.repo, "done", remove_worktree=False, delete_branch=False)
        # `busy` is NOT merged, so it must survive
        removed = land.prune_stale(self.repo)
        self.assertFalse(wt_done.exists(), "a merged, clean worktree should be pruned")
        self.assertTrue(wt_busy.exists(), "an unmerged worktree must never be pruned")
        self.assertEqual(len(removed), 1, removed)
        self.assertNotIn("done", git(self.repo, "branch", "--format=%(refname:short)").split())

    def test_stale_worktrees_excludes_ones_with_untracked_files(self):
        """The advertised count must equal what prune can actually remove."""
        wt = self.make_work_branch("done", "done.txt")
        land.land(self.repo, "done", remove_worktree=False, delete_branch=False)
        self.assertEqual([w.path for w in land.stale_worktrees(self.repo)], [wt])
        write(wt, "scratch.log", "uncommitted, unrecoverable\n")
        self.assertEqual(land.stale_worktrees(self.repo), [],
                         "a worktree with untracked files is not safe to delete")
        self.assertEqual(land.prune_stale(self.repo), [])
        self.assertTrue(wt.exists())

    def test_prune_stale_spares_a_dirty_worktree(self):
        wt = self.make_work_branch("done", "done.txt")
        land.land(self.repo, "done", remove_worktree=False, delete_branch=False)
        write(wt, "uncommitted.txt", "in flight\n")
        git(wt, "add", "uncommitted.txt")
        self.assertEqual(land.prune_stale(self.repo), [])
        self.assertTrue(wt.exists())

    def test_dry_run_changes_nothing(self):
        self.make_work_branch()
        before = git(self.repo, "rev-parse", "main")
        res = land.land(self.repo, "work", dry_run=True)
        self.assertEqual(before, git(self.repo, "rev-parse", "main"))
        self.assertIn("DRY RUN", res.detail)
        self.assertEqual(land.read_queue(self.repo), [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
