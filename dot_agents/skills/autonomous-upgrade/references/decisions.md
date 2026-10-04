# Decisions to confirm with the owner

Every item is a **baseline to adapt**, not a mandate. Walk the list with the
owner, present a recommendation plus trade-offs, get agreement, then record the
agreed choices and any deviations in the PR description or conversation.

## Checklist

1. **Host** — github.com, self-hosted Forgejo, or Forgejo + a GitHub twin.
   *Default:* whatever `git remote -v` says. Determines workflow directory,
   runner labels, and `gh` vs `fj`.
2. **Project mode** — maintenance or active development.
   *Default:* active development. Determinates whether the release workflow gets
   an `on.schedule` cron at all.
3. **Release model** — weekly batch (maintenance mode) plus manual dispatch;
   manual dispatch only (active). In both modes, manual dispatch supports two
   targets: `tag` (default, publishes release) and `commit` (test build against
   latest commit on `main`, uploads to Actions run artifacts without publishing).
   *Alternatives:* release on every merge, label-gated releases.
4. **Version source of truth and manifest bump** — git tags, with
   [`ietf-tools/semver-action`](https://github.com/ietf-tools/semver-action)
   deriving the next version from Conventional Commits since the last tag.
   **Never** a hand-rolled calculation or a manually typed version. The
   `bump-version` action updates the package manager's config file via the
   package-agnostic `just bump <version>` recipe before committing and tagging
   atomically on `main`. *Alternatives:* `release-plz`, `release-please`.
5. **Release artifacts** — build only what the project ships: for CLIs, commonly
   Linux x64 + Windows x64 + macOS arm64; notes-only otherwise. Confirm formats
   and publish targets (GitHub Releases, a registry, a Homebrew tap, a CDN). On
   a Forgejo+twin project, artifacts publish from the twin.
6. **CI gate** — one `just check` gate, no build matrix. *Default:* add only the
   runtimes/services the check needs.
7. **Dependencies** — daily at 02:00 for code dependencies (via native package
   managers with native cooldown). On GitHub-hosted repos, Dependabot runs
   weekly for `package-ecosystem: "github-actions"` only.
8. **Security & config** — rebase-only, linear history, required
   `Check (just check)`. Prefer the built-in token for same-repo automation; a
   fine-grained PAT or GitHub App only for cross-repo dispatch to a twin. Avoid
   polling loops.
9. **Downstream sync** — event-driven when a token is acceptable, otherwise a
   short-interval poll that pushes directly. *Confirm the acceptable latency.*
10. **Runner budget** — cheapest single-core label for orchestration, platform
    runners only for artifact builds.

## Project mode: maintenance vs active

The single most consequential choice here, because it is the only thing that
changes the shape of `release.yml`.

| | **Maintenance mode** | **Active development** |
|---|---|---|
| What's happening | Bug fixes and dependency bumps only; no feature work planned | Features in flight; a release means more than "latest build" |
| Weekly cron | **Include** `on.schedule` | **Omit `on.schedule` entirely** |
| Trigger | `schedule` + `workflow_dispatch` | `workflow_dispatch` only |
| Why | An unattended weekly tag is pure upside when nobody is mid-feature | A version cut mid-feature implies a shippable state that does not exist, and tags a commit the owner is still rebasing onto |

**The only difference in `release.yml` is the `on:` block.** The semver
derivation, the `release-main` lock, and the artifact build stay byte-identical.
Do not fork the release workflow into two variants.

Heuristic: *would a tag cut on Sunday surprise anyone?* No → maintenance mode.
Yes → active development. Revisit when the roadmap changes; this is a
per-application choice, not a permanent property.

### Optional: Roadmap for ongoing projects

For projects under active development, maintain an optional **`## Roadmap`**
section in the root `README.md` (or `docs/roadmap.md`). This provides clear
visibility into in-flight milestones and sets the exact criteria for when the
project transitions into maintenance mode:

```markdown
## Roadmap

- [x] **Core feature** — short description of what shipped.
- [ ] **Next feature** — in flight, planned before next minor tag.
- [ ] **Final milestone** — criteria to freeze features and cut over to maintenance.
```

**Why keep it in `README.md`?**
- Serves as the single public source of truth for project status (avoiding
  ephemeral or fragmented `TODO.md` / `plan.md` files).
- Makes the transition unambiguous: when all active milestones are checked
  `[x]` and no new features are queued, the project flips to **maintenance mode**
  (enabling the `on.schedule` weekly cron in `bump-version.yml`).

## Why the hard rules exist

- **Rule 3 (cooldown).** Compromised releases are usually detected and yanked
  within hours or days. A 14-day quarantine would have blocked the March 2026
  npm supply-chain attacks outright. The gate must come from the package manager
  because only the resolver knows about transitive versions.
- **Rule 6 (no cron when active).** See the project-mode table above.
- **Rule 4 (Dependabot scope).** Package managers handle their own libraries via
  native commands and cooldown gates. On GitHub repos, Dependabot is retained
  exclusively for `github-actions` because native tools cannot update workflow
  actions.
- **Rule 7 (single-core runners).** Every job that does not build artifacts is
  I/O-bound orchestration; running it on a multi-core runner is waste.
- **Rule 9 (concurrency lock).** Without it, two overlapping release runs race to
  create the same tag.
