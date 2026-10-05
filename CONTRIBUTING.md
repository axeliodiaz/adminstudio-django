# Contributing

## Branch flow

- `develop` is the default branch. Open every feature or fix PR against `develop`.
- Merge PRs into `develop` with squash and merge (one commit per PR).
- Releases go from `develop` to `main` with a merge commit (no squash).
- Never delete `develop`, `main` or `release/*`. Merged feature branches are deleted by the branch-cleanup workflow where the repo has one.
