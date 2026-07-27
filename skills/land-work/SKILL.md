---
name: land-work
description: Merge a finished work branch home instead of leaving it parked, in ANY git repo (a universe, a platform repo, a site, anything). Runs at the START of a pipeline to drain previously-blocked merges and at the END to land the run's own branch, and it queues rather than parking when a sibling agent session holds the target branch. Use when a run is finishing, when a report is about to say "branch parked / not merged / left for you to merge", when worktrees have piled up, when the operator says "merge it", "use your judgment on the merge", "land this", "clean up the worktrees", or "why is this never merged". NOT for pushing to a remote or opening a PR.
---

# Land Work

The last step of every pipeline run, and the first step too.

## The rule

**A finished branch gets merged. Do not report it as parked.**

The operator has no opinion about merges and never will. Every previous run ended
with some version of "the canon branch is committed but parked, master is checked
out in another worktree", and every single time the answer was "use your judgment,
merge it". That exchange is pure overhead: the agent knows how to merge safely, and
asking is not caution, it is an unfinished job handed back.

It also compounds. Parked branches and their worktrees accumulate until a repo is
carrying a dozen of them, which is the same defect a dozen times.

## Why this is not just "run git merge"

There is a real hazard, and it is why parking felt safer. The target branch is
frequently checked out in a **sibling worktree belonging to a live session**. Moving
a branch under a live worktree corrupts that session: their files stay on disk but
HEAD now lists yours, so their index reports YOUR files as deletions, and their next
bare `git commit` reverts your work as part of their unrelated commit.

So `land` classifies the target and only acts where action is provably safe:

| state | meaning | what happens |
|---|---|---|
| **free** | target checked out nowhere | merge in a throwaway worktree; touches nobody |
| **idle** | target checked out in a CLEAN worktree, no operation in progress | merge in that worktree, so ref and files move together |
| **busy** | that worktree has staged/unstaged changes, or a merge/rebase/cherry-pick in progress | **do not touch**; queue it |
| **conflict** | the merge does not apply cleanly | abort, change nothing, queue, and tell the human |

It never uses `git update-ref` or `git branch -f`, which are exactly the two ways to
move a branch out from under a live worktree.

**A queued merge is a SUCCESS, not a failure.** The work is committed and safe, and
the next run finishes it. That is the whole design: no daemon, no cron, no human.

## Use it

```bash
ENG=~/Documents/github-repos/agenticstory/engine

# START of a run: finish whatever a previous run could not.
(cd "$ENG" && python3 -m agenticstory.cli land <repo> --drain-only)

# END of a run: land this run's branch (drains first, automatically).
(cd "$ENG" && python3 -m agenticstory.cli land <repo> --branch <work-branch>)

# Housekeeping: also delete worktrees whose branch is already fully merged.
(cd "$ENG" && python3 -m agenticstory.cli land <repo> --prune-stale)
```

`<repo>` is **any git repo**, not a universe. Run it once per repo a run touched: a
book run usually touches both the canon repo and the platform repo.

Useful flags: `--onto <branch>` (default `main`, else `master`), `--dry-run`,
`--keep-branch`, `--keep-worktree`, `--no-drain`.

On success it deletes the work branch and removes its worktree, because a merged
branch with a leftover worktree is the other half of the same mess. It verifies
containment in the **target** before deleting, not in HEAD, since `git branch -d`
asks the wrong question whenever the main checkout sits on some unrelated branch.

## Wire it into a pipeline

Two lines, at the two ends:

1. **First thing**, before any work: `land <repo> --drain-only`. Previously blocked
   merges land now that the other session has moved on.
2. **Last thing**, after the run's own commits: `land <repo> --branch <work-branch>`.

Then **report what actually happened in one line** and move on. Do not ask.

- merged -> say it merged, and say what was cleaned up.
- queued -> say it is queued and that the next run lands it. This is normal. Do not
  present it as a decision, a risk, or something the operator must act on.
- conflict -> **this one you surface**, because a conflict is a genuine judgment call.
  Say which files, and that nothing was changed.

## When to still involve the human

Only a **conflict**, or a repo whose target branch you cannot identify. Everything
else is handled or queued.

## Not this skill

- Pushing to a remote, opening a PR, or deploying. `land` is local-history only.
- Deciding *whether* work is finished. That is the pipeline's job; `land` assumes
  the branch is committed and refuses if it is not.
