# Decisions to confirm with the owner

Every item is a **baseline to adapt**, not a mandate. Walk the list with the
owner, present a recommendation plus trade-offs, get agreement, then record the
agreed choices and any deviations in the PR description or conversation.

## Checklist

1. **Host**: github.com, self-hosted Forgejo, or Forgejo + a GitHub twin.
   _Default:_ whatever `git remote -v` says. Determines workflow directory,
   runner labels, and PR creation (`gh` vs native AGit).
2. **Project mode**: maintenance or active development.
   _Default:_ active development. Determinates whether the release workflow gets
   an `on.schedule` cron at all.
3. **Release model**: weekly batch (maintenance mode: scheduled cron) plus
   manual dispatch; manual dispatch only (active). The `release.yml` workflow
   is one run: gate on all of CI, then bump → commit + tag → push → build →
   publish. A `ref` input rebuilds an old tag. _Alternatives:_ release on
   every merge, label-gated releases.
4. **Version source of truth and manifest bump**: git tags, with
   [`ietf-tools/semver-action`](https://github.com/ietf-tools/semver-action)
   deriving the next version from Conventional Commits since the last tag.
   **Never** a hand-rolled calculation or a manually typed version. `release.yml`
   updates the package manager's config file via the package-agnostic
   `just version set <version>` recipe, commits and tags on `main` directly.
   _Alternatives:_ `release-plz`, `release-please`.
   **Before the first release run, the repo needs one existing `v*` tag.** Draft
   it at the root commit so the first release covers the whole history:
   `git tag -a v0.0.0 "$(git rev-list --max-parents=0 HEAD)"`. Anchor it at the
   root, not at `HEAD`; at `HEAD` the tag and branch point at the same commit,
   so the compare range is empty and that run releases nothing.
   `fallbackTag: v0.0.0` does not cover this gap: it supplies only a _name_, and
   the action then asks the API to compare `v0.0.0...main`, which 404s while no
   such tag exists on the server. Without a tag the run fails at the compare call.
5. **Release artifacts**: prebuilt binaries for linux x64 only; every other
   platform builds from source through the Homebrew tap. Confirm formats and
   publish targets (GitHub Releases, the tap). Additional prebuilts need an
   explicit recorded exception. On a Forgejo+twin project, artifacts publish
   from the twin.
6. **CI gate**: one `just check` gate, no build matrix, plus the shared
   [scan workflow](https://github.com/Delnegend/actions) called as a job
   (`@main  # nosemgrep`): security scans (Gitleaks, actionlint, Semgrep, Trivy,
   OSV-Scanner), `config-policy` (`common-configs` for Rust/Bun), and mandatory
   `emdash`, `facade` (`common-facade`), and `docs-references` checks. Take the
   scans from there rather than writing `docker run` jobs per project: they
   drift, and a shared gate keeps the fleet in agreement. _Default:_ add only
   the runtimes/services the check needs.
7. **Dependencies**: daily at 02:00 for code dependencies (via native package
   managers with native cooldown). On GitHub-hosted repos, Dependabot runs
   weekly for `package-ecosystem: "github-actions"` only, with a 14-day
   `cooldown: { default-days: 14 }`.
8. **Security & config**: rebase-only, linear history, no required status
   checks (the release gates on all of CI via `workflow_call`). Prefer the
   built-in token for same-repo automation; a fine-grained PAT or GitHub App
   only for cross-repo dispatch to a twin. Avoid polling loops.
9. **Downstream sync**: event-driven when a token is acceptable, otherwise a
   short-interval poll that pushes directly. _Confirm the acceptable latency._
10. **Runner budget**: cheapest single-core label for orchestration, platform
    runners only for artifact builds.

## Project mode: maintenance vs active

The single most consequential choice here, because it is the only thing that
changes the shape of `release.yml`.

|                  | **Maintenance mode**                                               | **Active development**                                                                                                      |
| ---------------- | ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| What's happening | Bug fixes and dependency bumps only; no feature work planned       | Features in flight; a release means more than "latest build"                                                                |
| Weekly cron      | **Include** `on.schedule`                                          | **Omit `on.schedule` entirely**                                                                                             |
| Trigger          | `schedule` + `workflow_dispatch`                                   | `workflow_dispatch` only                                                                                                    |
| Why              | An unattended weekly tag is pure upside when nobody is mid-feature | A version cut mid-feature implies a shippable state that does not exist, and tags a commit the owner is still rebasing onto |

**The only difference in `release.yml` is the `on:` block.** The semver
derivation, the `release-main` lock, and the artifact build stay byte-identical.
Do not fork the release workflow into two variants.

Heuristic: _would a tag cut on Sunday surprise anyone?_ No → maintenance mode.
Yes → active development. Revisit when the roadmap changes; this is a
per-application choice, not a permanent property.

### Transitioning to maintenance mode

When feature work freezes and an unattended Sunday tag would no longer surprise
anyone, flip the project to **maintenance mode** by adding the `on.schedule`
weekly cron (`0 0 * * 0`) to `release.yml`. Do not add a `## Roadmap` section to
root `README.md` (`common-facade`'s schema does not support extra root sections).

## Why the hard rules exist

- **Rule 5 (cooldown).** Compromised packages are usually yanked within days. The gate must come from the package manager because only its resolver evaluates transitive dependencies.
- **Rule 6 (Dependabot scope).** Native package managers handle their own libraries. Dependabot is scoped exclusively to `github-actions`.
- **Rule 8 (no cron when active).** Scheduled weekly releases belong only in maintenance mode; active development releases on manual dispatch to avoid shipping unfinished work.
- **Rule 9 (single-core runners).** Workflow orchestration is I/O-bound; multi-core runners are reserved for builds.
- **Rule 11 (concurrency locks).** `release-main` (`cancel-in-progress: false`) prevents races on tag creation; dynamic per-branch CI locks cancel stale runs safely.
- **Rule 18 (version get/set).** Standard `just version get` and `just version set <ver>` contract eliminates ad-hoc per-language parsing scripts in release workflows.
