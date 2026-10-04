---
name: autonomous-upgrade
description: Sets up or maintains an autonomous dependency-update and release pipeline for a GitHub or Forgejo repository — native package-manager upgrades with a 2-week supply-chain cooldown, a single-gate 'just check' CI, instant auto-rebase, and weekly consolidated releases for maintenance-mode projects only. Always determines the project's host before applying anything.
---

# Autonomous Upgrade

Pipeline: **native upgrade (daily + 14d cooldown) → `just check` → auto-rebase → `release` (3 targets: new-tag, tag, commit)**.

## Do these three things first, in order

| # | Gate | Why it blocks everything after |
|---|---|---|
| 1 | **Locate the host** — `git remote -v` | Decides `.github/` vs `.forgejo/`, runner labels, `gh` vs `fj`, and whether a GitHub twin exists |
| 2 | **Ask the project mode** — maintenance or active | Decides whether `release.yml` gets `on.schedule` (active projects track milestones in an optional roadmap) |
| 3 | **Consult the owner** on the checklist in `references/decisions.md` | The rest are baselines to adapt, not mandates |

Never assume github.com. Never write a weekly cron for a project under active
development.

```mermaid
flowchart TD
    Z[1. Locate host] --> Y[2. Project mode]
    Y --> A[Native upgrade<br/>daily 02:00 UTC<br/>14d cooldown from the tool]
    A -->|patch/minor| B[PR labelled dependencies]
    A -->|major| C[Stays open<br/>human review]
    B --> D[just check]
    D -->|green| E[auto-merge, rebase]
    E --> F[Accumulate on main]
    F --> G[release workflow]
    G -->|new-tag: cron or manual| H[CI gate -> just bump -> atomic tag push -> publish]
    G -->|tag: manual| I[rebuild existing tag -> publish]
    G -->|commit: manual| J[test build -> Actions artifacts only]
```

## Reference files

Read the file for the task at hand; do not read all four.

| File | Read when |
|---|---|
| `references/decisions.md` | The customization checklist — host, release model, artifacts, runner budget |
| `references/hosts.md` | Writing any workflow: GitHub vs Forgejo differences, the twin-repository pattern, branch protection |
| `references/ecosystems.md` | Setting the 14-day cooldown, or choosing whether an ecosystem qualifies at all |
| `references/workflows.md` | The four YAML templates: deps, CI, auto-merge, release |

## Hard rules

These are not negotiable. Rationale is in `references/decisions.md`.

1. **Consult the owner before applying.** No universal CI/CD flow. Record agreed
   choices and deviations in the PR/conversation — never a committed decision file.
2. **One CI gate: `just check`.** No build matrix in CI. Building artifacts is
   the release workflow's job.
3. **14-day cooldown, enforced by the package manager itself.** Never re-implement
   the age filter as a shell script — the tool's own gate also covers transitive
   dependencies. If an ecosystem has no native gate, that project does not get
   autonomous bumps.
4. **Dependabot for GitHub Actions only.** On GitHub-hosted repos, Dependabot is
   used exclusively for `package-ecosystem: "github-actions"` to keep workflow
   actions up to date, and nothing else. Code dependencies are upgraded through
   native package managers (`bun update`, `cargo update`, `ncu`).
5. **Split patch/minor from major**, so a breaking major cannot block routine merges.
6. **Weekly releases only in maintenance mode.** Active development gets
   `workflow_dispatch` alone. The unified `release.yml` workflow provides 3
   targets: `new-tag` (default/cron: CI gate + bump + tag + publish), `tag`
   (rebuild existing tag), and `commit` (test build, Actions artifacts only).
7. **Cheapest single-core runner for orchestration** (`ubuntu-slim` on GitHub, the
   owner's self-hosted label on Forgejo). Full runners only for `just check` and
   artifact builds.
8. **Rebase-only, linear history.** No squash, no merge commits.
9. **`release-main` concurrency lock**, `cancel-in-progress: false`.
10. **Verify action runtimes match the runner.** `using: node24` actions fail on
    lean images like Alpine. Prefer shell-only composites on self-hosted runners.
11. **Push the version commit and its tag in one `git push`**, and never tag a
    commit whose manifest still carries the old version.

## Project contract

A repo qualifies only if all of these hold:

1. A root `justfile` with:
   - `check`: executes formatting, linting, tests, and static analysis.
   - `bump version`: updates the package manager's manifest (package-agnostic, see `references/ecosystems.md`).
2. Branch protection requires exactly `"Check (just check)"`.
3. The package manager has a native cooldown gate, configured to 14 days
   (see `references/ecosystems.md`).
4. The owner has stated the project mode.
5. Release artifacts are decided and implemented; CI stays build-free.
