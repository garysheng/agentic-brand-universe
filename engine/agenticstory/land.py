"""
Landing work branches safely in a repo that other agent sessions are also using.

WHY THIS EXISTS
---------------
Every long pipeline run (a book, a universe expansion, a platform ship) is done
in its own branch and usually its own worktree, because a repo with several
concurrent agent sessions cannot be shared any other way. The run then ends and
the branch has to go home. In practice it never did: the operator got a report
saying "branch parked, not merged, master is checked out in another worktree",
and every single time the answer was the same, "use your judgment, merge it".

Parking is not caution, it is an unfinished job. It also compounds: one repo
here accumulated ELEVEN worktrees and a pile of unmerged branches, which is the
same defect eleven times.

So this module does the merge, and where a merge genuinely cannot be done safely
right now it QUEUES the intent and the NEXT run drains the queue. No daemon, no
cron, no human in the loop.

WHAT MAKES IT SAFE
------------------
The reason merging is scary is a real, earned hazard: the target branch is often
checked out in a SIBLING worktree belonging to a live session. Moving a branch
under a live worktree corrupts that session's view (their files stay on disk but
HEAD now lists yours, so their index reports YOUR files as deletions and their
next bare `git commit` reverts your work). `git update-ref` and `git branch -f`
are the classic ways to do exactly that, so this module NEVER uses either.

Instead it classifies the target and only acts where action is provably safe:

  FREE      target is checked out nowhere -> merge inside a fresh temporary
            worktree, which touches nobody's files. Safest case.
  IDLE      target is checked out in a worktree that is CLEAN with no operation
            in progress -> merge IN THAT WORKTREE, which moves the ref and its
            working tree together and atomically, exactly as a human would.
  BUSY      target is checked out in a worktree with staged/unstaged changes, or
            a merge/rebase/cherry-pick/bisect in progress -> DO NOT TOUCH.
            Queue it and let a later run land it.
  CONFLICT  the merge itself does not apply cleanly -> abort, queue, and say so.
            A conflict is the one case that genuinely wants a human.

Everything is repo-generic. Nothing here knows what a universe is, so it works
equally for a canon repo, a platform repo, or any other git repo.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Where the queue lives. Inside .git/ on purpose: it is local state about local
# branches, it must never be committed, and it must survive between runs.
QUEUE_BASENAME = "agenticstory-pending-merges.json"

# Ordered by preference. The first of these that exists is the default target.
DEFAULT_TARGETS = ("main", "master")

_IN_PROGRESS_MARKERS = (
    "MERGE_HEAD",
    "REBASE_HEAD",
    "rebase-merge",
    "rebase-apply",
    "CHERRY_PICK_HEAD",
    "REVERT_HEAD",
    "BISECT_LOG",
)


class GitError(RuntimeError):
    pass


def git(repo: Path, *args: str, check: bool = True) -> str:
    """Run git in `repo` and return stdout stripped."""
    p = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True,
    )
    if check and p.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed: {(p.stderr or p.stdout).strip()}")
    return p.stdout.strip()


# ---------------------------------------------------------------- repo facts

def git_common_dir(repo: Path) -> Path:
    """The shared .git dir, identical for the main checkout and every worktree."""
    d = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    return d


def current_branch(repo: Path) -> str | None:
    b = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    return None if b == "HEAD" else b


def branch_exists(repo: Path, branch: str) -> bool:
    p = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
        capture_output=True, text=True,
    )
    return p.returncode == 0


def default_target(repo: Path) -> str | None:
    for name in DEFAULT_TARGETS:
        if branch_exists(repo, name):
            return name
    return None


@dataclass
class Worktree:
    path: Path
    branch: str | None
    detached: bool


def worktrees(repo: Path) -> list[Worktree]:
    out = git(repo, "worktree", "list", "--porcelain")
    res: list[Worktree] = []
    cur: dict = {}
    for line in out.splitlines() + [""]:
        if not line.strip():
            if cur.get("worktree"):
                br = cur.get("branch")
                if br and br.startswith("refs/heads/"):
                    br = br[len("refs/heads/"):]
                # resolve(): on macOS git reports /private/var while callers hold
                # /var (the same dir via a symlink), and unresolved paths made
                # worktree identity comparisons silently fail.
                res.append(Worktree(Path(cur["worktree"]).resolve(), br, "detached" in cur))
            cur = {}
            continue
        key, _, val = line.partition(" ")
        cur[key] = val or True
    return res


def worktree_holding(repo: Path, branch: str) -> Worktree | None:
    for w in worktrees(repo):
        if w.branch == branch:
            return w
    return None


def is_dirty(repo: Path, *, include_untracked: bool = False) -> bool:
    """Staged or unstaged changes. Untracked files count only if asked for.

    TWO DIFFERENT QUESTIONS, and conflating them produced a wrong number.

    For MERGING, untracked files are irrelevant: nearly every repo with a live
    agent session has stray untracked scratch output, and refusing to merge over
    an untracked log file would put us straight back to parking everything,
    which is the bug this module exists to kill. So merging uses the default.

    For PRUNING a worktree, untracked files matter a great deal, because pruning
    DELETES the directory and an untracked file is unrecoverable work nobody has
    committed yet. `git worktree remove` knows this and refuses. Before this
    parameter existed, `stale_worktrees` used the merge-shaped check and so
    advertised worktrees that `prune_stale` then failed to remove: it reported
    "5 can be removed" when the true answer was 3. Pruning passes
    include_untracked=True so the count it reports is the count it can deliver.
    """
    args = ["status", "--porcelain"]
    args.append("--untracked-files=normal" if include_untracked else "--untracked-files=no")
    return bool(git(repo, *args))


def operation_in_progress(repo: Path) -> str | None:
    """Name any half-finished git operation in this worktree."""
    gitdir = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-dir"))
    for marker in _IN_PROGRESS_MARKERS:
        if (gitdir / marker).exists():
            return marker
    return None


def is_ancestor(repo: Path, maybe_ancestor: str, descendant: str) -> bool:
    p = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", maybe_ancestor, descendant],
        capture_output=True, text=True,
    )
    return p.returncode == 0


# ---------------------------------------------------------------- the plan

@dataclass
class Plan:
    repo: Path
    branch: str
    onto: str
    state: str                  # free | idle | busy | already-merged | nothing-to-do
    reason: str
    holder: Path | None = None  # the worktree holding `onto`, when there is one
    branch_worktree: Path | None = None  # the worktree holding `branch`, if any

    @property
    def can_land_now(self) -> bool:
        return self.state in ("free", "idle", "already-merged")


def plan(repo: Path, branch: str, onto: str) -> Plan:
    repo = repo.resolve()
    if not branch_exists(repo, branch):
        raise GitError(f"branch {branch!r} does not exist in {repo}")
    if not branch_exists(repo, onto):
        raise GitError(f"target branch {onto!r} does not exist in {repo}")
    if branch == onto:
        raise GitError(f"refusing to land {branch!r} onto itself")

    bw = worktree_holding(repo, branch)
    holder = worktree_holding(repo, onto)

    if is_ancestor(repo, branch, onto):
        return Plan(repo, branch, onto, "already-merged",
                    f"{branch} is already contained in {onto}; nothing to merge",
                    holder.path if holder else None, bw.path if bw else None)

    # The work branch itself must be committed. We are landing finished work.
    if bw and is_dirty(bw.path):
        return Plan(repo, branch, onto, "busy",
                    f"the work branch's own worktree {bw.path} has uncommitted changes; commit them first",
                    holder.path if holder else None, bw.path)

    if holder is None:
        return Plan(repo, branch, onto, "free",
                    f"{onto} is checked out nowhere, so it can be merged in a temporary worktree",
                    None, bw.path if bw else None)

    op = operation_in_progress(holder.path)
    if op:
        return Plan(repo, branch, onto, "busy",
                    f"{onto} is checked out at {holder.path} with {op} in progress",
                    holder.path, bw.path if bw else None)
    if is_dirty(holder.path):
        return Plan(repo, branch, onto, "busy",
                    f"{onto} is checked out at {holder.path} and that tree has uncommitted changes, "
                    f"so moving the branch would corrupt that session's view",
                    holder.path, bw.path if bw else None)
    return Plan(repo, branch, onto, "idle",
                f"{onto} is checked out at {holder.path} and that tree is clean, "
                f"so the merge can be made there safely",
                holder.path, bw.path if bw else None)


# ---------------------------------------------------------------- the queue

def queue_path(repo: Path) -> Path:
    return git_common_dir(repo) / QUEUE_BASENAME


def read_queue(repo: Path) -> list[dict]:
    p = queue_path(repo)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text())
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        # A corrupt queue must never wedge a pipeline. Start clean.
        return []


def write_queue(repo: Path, items: list[dict]) -> None:
    p = queue_path(repo)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(items, indent=2) + "\n")


def enqueue(repo: Path, branch: str, onto: str, reason: str,
            delete_branch: bool, remove_worktree: bool) -> None:
    items = [i for i in read_queue(repo)
             if not (i.get("branch") == branch and i.get("onto") == onto)]
    items.append({
        "branch": branch,
        "onto": onto,
        "reason": reason,
        "deleteBranch": delete_branch,
        "removeWorktree": remove_worktree,
    })
    write_queue(repo, items)


def dequeue(repo: Path, branch: str, onto: str) -> None:
    write_queue(repo, [i for i in read_queue(repo)
                       if not (i.get("branch") == branch and i.get("onto") == onto)])


# ---------------------------------------------------------------- landing

@dataclass
class Result:
    branch: str
    onto: str
    outcome: str          # merged | already-merged | queued | conflict | error
    detail: str
    cleaned: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.outcome in ("merged", "already-merged")


def _merge_message(branch: str, onto: str) -> str:
    return f"Merge {branch} into {onto}"


def _cleanup(repo: Path, p: Plan, delete_branch: bool, remove_worktree: bool) -> list[str]:
    """Retire the work branch and its worktree once the work is safely in `onto`.

    This is the other half of the parking bug: even runs that did merge left the
    worktree behind, which is why worktrees pile up.
    """
    done: list[str] = []
    if remove_worktree and p.branch_worktree:
        wt = p.branch_worktree
        try:
            if not is_dirty(wt):
                git(repo, "worktree", "remove", str(wt))
                done.append(f"removed worktree {wt}")
            else:
                done.append(f"kept worktree {wt} (uncommitted changes)")
        except GitError as e:
            done.append(f"kept worktree {wt} ({e})")
    if delete_branch:
        # `git branch -d` measures "fully merged" against HEAD, NOT against the
        # branch we just merged into. Whenever the main checkout happens to sit
        # on some unrelated third branch (which is the normal state of a repo
        # running several sessions) it therefore refuses to delete a branch that
        # IS safely merged. So verify against the real target ourselves and then
        # use -D. This is strictly stronger than -d, not weaker: -d would have
        # asked the wrong question.
        if is_ancestor(repo, p.branch, p.onto):
            try:
                git(repo, "branch", "-D", p.branch)
                done.append(f"deleted branch {p.branch} (verified merged into {p.onto})")
            except GitError as e:
                done.append(f"kept branch {p.branch} ({e})")
        else:
            done.append(f"kept branch {p.branch} (not contained in {p.onto}; refusing to delete)")
    return done


def land(repo: Path, branch: str, onto: str | None = None, *,
         delete_branch: bool = True, remove_worktree: bool = True,
         dry_run: bool = False) -> Result:
    """Merge `branch` into `onto`, or queue the intent if that is not safe now."""
    repo = repo.resolve()
    onto = onto or default_target(repo)
    if not onto:
        return Result(branch, "?", "error",
                      f"no default target branch found in {repo} (looked for {', '.join(DEFAULT_TARGETS)})")

    try:
        p = plan(repo, branch, onto)
    except GitError as e:
        return Result(branch, onto, "error", str(e))

    if dry_run:
        return Result(branch, onto, "queued" if not p.can_land_now else "merged",
                      f"DRY RUN [{p.state}] {p.reason}")

    if p.state == "already-merged":
        dequeue(repo, branch, onto)
        return Result(branch, onto, "already-merged", p.reason,
                      _cleanup(repo, p, delete_branch, remove_worktree))

    if p.state == "busy":
        enqueue(repo, branch, onto, p.reason, delete_branch, remove_worktree)
        return Result(branch, onto, "queued",
                      f"{p.reason}. Queued; the next land run will finish it.")

    # ---- FREE: merge in a throwaway worktree so nobody's files are touched.
    if p.state == "free":
        tmp = Path(tempfile.mkdtemp(prefix="agenticstory-land-"))
        wt = tmp / "wt"
        try:
            git(repo, "worktree", "add", "--quiet", str(wt), onto)
            merged = subprocess.run(
                ["git", "-C", str(wt), "merge", "--no-ff", "-m", _merge_message(branch, onto), branch],
                capture_output=True, text=True,
            )
            if merged.returncode != 0:
                subprocess.run(["git", "-C", str(wt), "merge", "--abort"],
                               capture_output=True, text=True)
                enqueue(repo, branch, onto, "merge conflict", delete_branch, remove_worktree)
                return Result(branch, onto, "conflict",
                              f"merge of {branch} into {onto} does not apply cleanly, so nothing was "
                              f"changed. This one needs a human. git said: "
                              f"{(merged.stdout or merged.stderr).strip().splitlines()[-1] if (merged.stdout or merged.stderr).strip() else 'conflict'}")
            head = git(wt, "rev-parse", "--short", "HEAD")
        finally:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(wt)],
                           capture_output=True, text=True)
            shutil.rmtree(tmp, ignore_errors=True)
            git(repo, "worktree", "prune", check=False)
        dequeue(repo, branch, onto)
        return Result(branch, onto, "merged",
                      f"merged into {onto} ({head}) via a temporary worktree; {onto} was checked out nowhere",
                      _cleanup(repo, p, delete_branch, remove_worktree))

    # ---- IDLE: merge in the clean worktree that holds the target.
    assert p.holder is not None
    holder = p.holder
    merged = subprocess.run(
        ["git", "-C", str(holder), "merge", "--no-ff", "-m", _merge_message(branch, onto), branch],
        capture_output=True, text=True,
    )
    if merged.returncode != 0:
        subprocess.run(["git", "-C", str(holder), "merge", "--abort"],
                       capture_output=True, text=True)
        enqueue(repo, branch, onto, "merge conflict", delete_branch, remove_worktree)
        return Result(branch, onto, "conflict",
                      f"merge of {branch} into {onto} does not apply cleanly in {holder}, so it was "
                      f"aborted and that tree is untouched. This one needs a human.")
    head = git(holder, "rev-parse", "--short", "HEAD")
    dequeue(repo, branch, onto)
    return Result(branch, onto, "merged",
                  f"merged into {onto} ({head}) inside its own clean worktree {holder}",
                  _cleanup(repo, p, delete_branch, remove_worktree))


def drain(repo: Path, *, dry_run: bool = False) -> list[Result]:
    """Attempt every queued merge. Safe to call at the START of any run."""
    repo = repo.resolve()
    results: list[Result] = []
    for item in list(read_queue(repo)):
        branch, onto = item.get("branch"), item.get("onto")
        if not branch or not onto:
            continue
        if not branch_exists(repo, branch):
            # The branch went away (landed or deleted elsewhere). Drop the entry.
            dequeue(repo, branch, onto)
            results.append(Result(branch, onto, "already-merged",
                                  "branch no longer exists; dropped from the queue"))
            continue
        results.append(land(repo, branch, onto,
                            delete_branch=bool(item.get("deleteBranch", True)),
                            remove_worktree=bool(item.get("removeWorktree", True)),
                            dry_run=dry_run))
    return results


def stale_worktrees(repo: Path) -> list[Worktree]:
    """Worktrees whose branch is already fully merged into the default target.

    These are finished work with nothing left in them, and they are what makes a
    repo accumulate a dozen directories. Reported, never removed implicitly.
    """
    repo = repo.resolve()
    onto = default_target(repo)
    if not onto:
        return []
    main = worktrees(repo)
    main_path = main[0].path if main else repo
    out: list[Worktree] = []
    for w in main:
        if w.path == main_path or w.detached or not w.branch or w.branch == onto:
            continue
        # include_untracked: pruning DELETES the directory, so an uncommitted
        # untracked file there is unrecoverable work. This is what makes the
        # advertised count match what prune_stale can actually remove.
        if is_ancestor(repo, w.branch, onto) and not is_dirty(w.path, include_untracked=True):
            out.append(w)
    return out


def prune_stale(repo: Path, *, delete_branch: bool = True, dry_run: bool = False) -> list[str]:
    """Remove worktrees whose branch is already fully merged into the target.

    Finished work with nothing left in it. Only ever touches worktrees that are
    (a) not the main checkout, (b) not holding the target branch, (c) clean, and
    (d) provably already contained in the target, so nothing can be lost.
    """
    repo = repo.resolve()
    onto = default_target(repo)
    done: list[str] = []
    for w in stale_worktrees(repo):
        if dry_run:
            done.append(f"would remove {w.path} [{w.branch}]")
            continue
        try:
            git(repo, "worktree", "remove", str(w.path))
        except GitError as e:
            done.append(f"kept {w.path} ({e})")
            continue
        msg = f"removed {w.path} [{w.branch}]"
        if delete_branch and w.branch and onto and is_ancestor(repo, w.branch, onto):
            try:
                git(repo, "branch", "-D", w.branch)
                msg += " and deleted the branch"
            except GitError as e:
                msg += f" (kept branch: {e})"
        done.append(msg)
    git(repo, "worktree", "prune", check=False)
    return done
