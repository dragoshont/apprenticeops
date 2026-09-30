# Laptop-reset recovery snapshot

Captured: 2026-09-30

This branch is a preservation branch, not a reviewed integration or publication
branch. It keeps the dirty primary checkout, the separate detached Architrave
worktree, every local branch tip, and every registered worktree HEAD reachable
from one remote ref.

## Scope

- Recovery branch: `recovery/laptop-reset-20260930`
- Primary dirty checkout snapshot: `21ad2cd05e60f506e9e27cad7cfec55aa3872d31`
- Detached human-review worktree snapshot:
  `b561d40fcd79ce6ec85a29b5cfcf6d5f61b66e9d`
- Original local branch tips: 4, listed in `RECOVERY_LOCAL_BRANCHES.tsv`
- Original registered worktrees: 10, listed in `RECOVERY_WORKTREES.tsv`

The primary snapshot includes the 17 commits by which local `main` was ahead of
`origin/main`, all tracked edits, new analysis code and documentation, and about
15 MB of untracked analysis outputs. The detached human-review implementation
is preserved separately because several of its files differ from the versions
in the primary checkout.

Ignored virtual environments, `.tmp` raw model outputs, heavy completed-run
bundles, node modules, local runtime state, and Git objects unreachable from
every local ref or registered worktree HEAD are not guaranteed to be present.
This follows the repository's rule that heavy bundles remain out-of-band and
content-addressed rather than being placed in Git.

## Public visibility warning

The canonical ApprenticeOps repository is public. This recovery branch and all
content reachable from it become publicly visible when pushed. It contains
unfinished/provisional analysis. It must not be interpreted as a publication,
claim promotion, or update to the GitHub Pages site.

## Restore the primary checkout

```bash
git clone https://github.com/dragoshont/apprenticeops.git
cd apprenticeops
git fetch origin recovery/laptop-reset-20260930
git switch -c recovered-laptop-reset origin/recovery/laptop-reset-20260930
```

The resulting tree is the primary WIP snapshot plus these recovery files. Do
not merge it directly into `main`: pushes to `main` can publish the analysis
site, and the repository requires human claim-lock promotion first.

## Restore the detached human-review work

```bash
git switch -c recovered/human-review-builder \
  b561d40fcd79ce6ec85a29b5cfcf6d5f61b66e9d
```

Review it against base commit
`15c3a364cac1ec76464b414119c62a781c8fc67b` and against the independently
evolved primary-checkout versions. Do not overwrite one with the other solely
because the paths match.

## Other refs

`RECOVERY_LOCAL_BRANCHES.tsv` maps original branch names to commits.
`RECOVERY_WORKTREES.tsv` maps original paths to HEAD commits. Restore a named
branch with:

```bash
git branch <restored-name> <commit>
```

## Validation status

Existing checkouts and indexes were not switched, staged, committed, or
cleaned. Snapshots were created through isolated temporary indexes. The
recovery branch is an archival checkpoint, and its combined WIP tree has not
passed the full ApprenticeOps build/test contract. No suspicious credential
signature was found in the changed paths, but this is not a formal secret-scan
guarantee because the installed `gitleaks` binary could not run on the original
Mac's CPU architecture.
