# Workflow templates

Four workflow templates plus Dependabot for GitHub Actions. Path and runner label
follow the host (see `hosts.md`); the substance does not change.

## A. Dependency upgrade job

Runs daily, opens one PR with the upgraded manifest and lockfile. The cooldown
has already filtered out too-new versions, so the PR only carries versions that
passed quarantine. **No-op when nothing changed** — the common case.

Substitute the three Bun-specific lines for your ecosystem (see
`ecosystems.md`).

```yaml
name: Dependency updates

on:
  schedule:
    - cron: '0 2 * * *' # Daily 02:00 UTC
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

concurrency:
  group: deps-main
  cancel-in-progress: false

jobs:
  update:
    name: Upgrade dependencies
    runs-on: ubuntu-slim
    steps:
      - uses: actions/checkout@v7

      # Bun example. Swap the setup/update steps per ecosystem:
      #   Cargo → dtolnay/rust-toolchain@stable, the enforcement check below
      #            (uncomment), then `cargo update` gated on its output with
      #            `if: steps.cargo-cooldown.outputs.enforced == 'true'`
      #            (reads .cargo/config.toml)
      #   npm   → actions/setup-node@v4, then
      #            `npx npm-check-updates -u -t minor --cooldown 14d && npm install`
      - uses: oven-sh/setup-bun@v2

      - name: Upgrade (cooldown enforced by bunfig.toml)
        run: bun update

      # Cargo repos only: uncomment. `registry.global-min-publish-age` is
      # stable from Cargo 1.100, and an older toolchain ignores the key
      # silently. Upgrading anyway would pull versions with no quarantine at
      # all, so skip instead of shipping that.
      # - name: Check that Cargo can enforce the cooldown
      #   id: cargo-cooldown
      #   shell: bash
      #   run: |
      #     set -euo pipefail
      #     version="$(cargo --version | awk '{print $2}')"
      #     major="${version%%.*}"
      #     minor="${version#*.}"; minor="${minor%%.*}"
      #     if [ "$major" -eq 1 ] && [ "$minor" -lt 100 ]; then
      #       echo "enforced=false" >> "$GITHUB_OUTPUT"
      #       echo "::warning::cargo ${version} ignores registry.global-min-publish-age (stable from 1.100) — no Cargo upgrade was made, so nothing lands without the 14-day quarantine"
      #     else
      #       echo "enforced=true" >> "$GITHUB_OUTPUT"
      #     fi

      - name: Detect whether anything changed
        id: diff
        shell: bash
        run: |
          if git diff --quiet; then
            echo "changed=false" >> "$GITHUB_OUTPUT"
          else
            echo "changed=true" >> "$GITHUB_OUTPUT"
          fi

      - name: Ensure the dependencies label exists
        if: steps.diff.outputs.changed == 'true'
        env:
          GH_TOKEN: ${{ github.token }}
        run: gh label create dependencies --force --color 0366d6 --description "Dependency updates"

      - name: Open upgrade PR
        if: steps.diff.outputs.changed == 'true'
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          set -euo pipefail
          git config user.name  "github-actions[bot]"
          git config user.email "actions@users.noreply.github.com"
          git checkout -B deps/automatic
          git add -u
          git commit -m "chore(deps): upgrade dependencies"
          git push --force origin deps/automatic
          # Update-or-create: the push above already updated the open PR when
          # one exists, so only create when there is nothing to update.
          # (The auto-merge workflow keys on the `dependencies` label.)
          if gh pr view deps/automatic --json number >/dev/null 2>&1; then
            echo "the push updated the existing upgrade PR"
          else
            gh pr create --base main --head deps/automatic \
              --title "chore(deps): upgrade dependencies" \
              --label dependencies \
              --body "Automated daily upgrade. Versions published less than 14 days ago were filtered out by the package manager."
          fi
```

**Forgejo:** use native **AGit** (`refs/for/main`). Forgejo opens or updates
the Pull Request directly over Git transport — **zero CLI tools (`gh`/`fj`)
and zero extra tokens needed**:

```yaml
      - name: Open upgrade PR (Forgejo AGit)
        if: steps.diff.outputs.changed == 'true'
        run: |
          git config user.name "actions[bot]"
          git config user.email "actions@git.local"
          git checkout -B deps/automatic
          git add -u
          git commit -m "chore(deps): upgrade dependencies" \
            -m "Automated daily upgrade. Versions published less than 14 days ago were filtered out by the package manager."
          # AGit: pushes to virtual refs/for/main; Forgejo creates or updates the PR automatically
          git push origin HEAD:refs/for/main \
            -o topic="deps/automatic" \
            -o force-push=true
```
Keep the `chore(deps):` commit prefix so the release workflow's Conventional
Commits scan reads a patch bump.


### Dependabot for GitHub Actions (`github.com` repos only)

For repositories hosted on GitHub, Dependabot is retained **exclusively** for
updating GitHub Actions versions in `.github/workflows/`. It is never configured
for language dependencies (which are handled by the native job above).

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "02:00"
    labels:
      - "dependencies"
    commit-message:
      prefix: "chore(deps)"
```

Because it uses the `dependencies` label and `chore(deps):` commit prefix,
these PRs are automatically verified by `ci.yml` and merged by `auto-merge.yml`.
## B. CI gate

One `just check`, no build matrix. Runner label follows the host
(`ubuntu-latest` on GitHub, a self-hosted equivalent on Forgejo).

```yaml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
  workflow_dispatch:
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  check:
    name: Check (just check)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: extractions/setup-just@v4
      # Insert any language setup needed by `just check` here (e.g. setup-go, setup-node)
      - name: Run verification
        run: just check

  scan:
    name: Scan
    uses: Delnegend/actions/.github/workflows/scan.yml@<pin-sha> # v1
    permissions:
      contents: read
```

Replace `<pin-sha>` with the full commit SHA that the scan workflow's `v1`
resolves to, so the pin is immutable like every other action here.

The scans come from the shared workflow rather than inline `docker run` jobs:
Gitleaks, actionlint, Semgrep, Trivy and OSV-Scanner, each its own job so they
run in parallel. Hand-rolling them per project is what let them drift apart.
Every scan runs with one shared configuration: Trivy always uses the full
`vuln,misconfig,secret` set, and a root `osv-scanner.toml` is picked up
automatically as the OSV quarantine — no inputs needed. The only input is
`exclude`, a space-separated opt-out (e.g. `exclude: osv`) for the rare case
a scan genuinely does not apply. Repos without a lockfile need nothing: the
OSV job detects that and skips with a notice.

The job `name:` on `check` must match the branch protection context exactly.

### B2. CI gate for Forgejo+twin repos (checks + security scans in parallel)

Single-host repos use template B as-is. When the repo has a GitHub twin, the
CI workflow (authored in the source repo's `.github/workflows/`, synced into
the twin by the dispatch action) runs `just check` **plus the security scans in
parallel**. Security scanning is GitHub-runners-only: the scans need Docker
images and registry egress that self-hosted Forgejo runners typically lack.

The `check` job first fetches the source from Forgejo at `inputs.ref`. The
scan jobs need no such step — they read the twin's own checkout, so template B's
`scan` job is copied across unchanged:

```yaml
jobs:
  check:
    name: Check (just check)
    runs-on: ubuntu-latest
    steps:
      # ... fetch source, language setup ...
      - name: Run checks
        run: just check

  scan: # copied verbatim from template B
```

## C. Auto-merge

Exits in <10 seconds; no polling. No `fetch-metadata` step — that was
Dependabot-specific. The `dependencies` label is the signal.

```yaml
name: Auto-merge dependencies

on:
  pull_request:
    branches: [main]

permissions:
  contents: write
  pull-requests: write

jobs:
  automerge:
    if: contains(github.event.pull_request.labels.*.name, 'dependencies')
    runs-on: ubuntu-slim
    steps:
      - name: Enable auto-merge and rebase
        run: gh pr merge --auto --rebase "$PR_URL"
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GH_TOKEN: ${{ github.token }}
```

**Forgejo:** `fj` has **no `--auto` flag** (see `hosts.md`), so
`gh pr merge --auto --rebase` has no direct translation. Two options:

- Set auto-merge in the Forgejo instance UI, then the workflow only needs to
  label the PR `dependencies`.
- Or gate explicitly in the job. `fj pr status --wait` blocks until all checks
  finish, then merge:

  ```bash
  fj pr status "$PR_NUM" -H "$FORGEJO_HOST" --wait
  fj pr merge "$PR_NUM" -H "$FORGEJO_HOST" --method rebase --delete
  ```

Auto-merge only fires once `Check (just check)` is green on the PR head.

## D. Release / Build Artifacts (`release.yml`)

Solo-dev maintenance flow: one run, zero clicks on the happy path. The cron
(or a manual run) gates on all of CI, then bumps, tags, pushes, builds, and
ships. No release PR, no second run, no PAT.

Branch protection keeps the safety rails (no force-push, no deletion, linear
history) but requires no status checks, so the bot pushes the bump straight
to `main`. The gate job is stronger than any PR rule: it calls all of
`ci.yml` via `workflow_call`, so every check must pass before anything ships.

Two inputs only, one dispatch guide — **empty = ship, SHA = test, tag = rebuild**:
`ref` empty ships a new version; a commit SHA test-builds it (artifacts upload,
nothing publishes); a tag rebuilds and publishes it. `dry-run` previews any of
the three without changing anything. A repo with no tags yet anchors `v0.0.0`
at HEAD on the first real run, so the semver comparison has a base; a dry run
on a tagless repo stops with a clear message instead. Manifest-less repos (Go:
`just bump` is a no-op echo) skip the bump/commit and tag HEAD directly.

### Mode-dependent trigger

- **Maintenance mode:** scheduled weekly cron (`0 0 * * 0`) + `workflow_dispatch`.
- **Active development:** `workflow_dispatch` only (no `on.schedule`).

```yaml
name: Release / Build Artifacts

on:
  workflow_dispatch:
    inputs:
      ref:
        description: "Empty = ship a new version. SHA = test-build it (no publish). Tag = rebuild it."
        required: false
        type: string
      dry-run:
        description: "Preview only: print each action (gate, bump, tag, build, publish) without doing any of it."
        required: false
        type: boolean
        default: false
  # Maintenance mode adds:
  # schedule:
  #   - cron: '0 0 * * 0' # Weekly: Sunday 00:00 UTC

concurrency:
  group: release-main
  cancel-in-progress: false

permissions:
  contents: write

jobs:
  # Every CI job must pass before anything ships.
  gate:
    name: Gate (all of CI)
    uses: ./.github/workflows/ci.yml

  prepare:
    name: Prepare (bump, tag, push)
    needs: gate
    runs-on: ubuntu-latest   # Full runner for compiler/toolchain headroom
    timeout-minutes: 30
    outputs:
      ref: ${{ steps.resolve.outputs.ref }}
      version: ${{ steps.resolve.outputs.version }}
      publish: ${{ steps.resolve.outputs.publish }}
      skip: ${{ steps.resolve.outputs.skip }}
    steps:
      - uses: actions/checkout@v7
        with:
          token: ${{ github.token }}
          persist_credentials: true
          fetch-depth: 0   # Full git history for tags, commits, and semver-action
      - uses: extractions/setup-just@v4
      # Insert any language setup needed by `just bump` (e.g. setup-go, setup-node)

      # The repo needs one existing `v*` tag before this workflow can run: see
      # checklist item 4 in decisions.md. Confirm it at setup time, not here.

      - name: Calculate Next SemVer
        id: semver
        uses: ietf-tools/semver-action@v1
        with:
          token: ${{ github.token }}
          fallbackTag: v0.0.0
          noNewCommitBehavior: silent
          noVersionBumpBehavior: patch

      - name: Bump, tag, and push
        id: resolve
        # Replace <pin-sha> with the full commit SHA that `v1` resolves to, so
        # the workflow pins an immutable ref like every other action here.
        uses: Delnegend/actions/resolve-release@<pin-sha> # v1
        with:
          ref: ${{ inputs.ref }}
          dry-run: ${{ inputs.dry-run }}
          gate-sha: ${{ github.sha }}
          semver-bump: ${{ steps.semver.outputs.bump }}
          semver-current: ${{ steps.semver.outputs.current }}
          semver-next: ${{ steps.semver.outputs.next }}
          semver-next-strict: ${{ steps.semver.outputs.nextStrict }}

  build:
    name: Build & Release Artifacts
    needs: prepare
    if: needs.prepare.outputs.skip != 'true'
    runs-on: ubuntu-slim   # or matrix runners for multi-platform binaries
    steps:
      - uses: actions/checkout@v7
        with:
          ref: ${{ needs.prepare.outputs.ref }}
          fetch-depth: 0

      # -----------------------------------------------------------------------
      # Project-specific build step (binaries, packages, container images).
      # Binaries go through package-artifact (one archive per target, named
      # `<name>-<version>-<target>.<ext>`, always into `dist/`); container
      # images go through docker-build-push (linux/amd64, registry cache).
      # -----------------------------------------------------------------------

      - name: Package artifact
        uses: Delnegend/actions/package-artifact@<pin-sha> # v1
        with:
          name: <project>
          version: ${{ needs.prepare.outputs.version }}
          target: <target-triple>
          source: <path-to-binary>

  publish:
    name: Publish Consolidated Release
    needs: [prepare, build]
    if: needs.prepare.outputs.skip != 'true'
    runs-on: ubuntu-latest
    steps:
      - name: Publish release
        uses: Delnegend/actions/publish-release@<pin-sha> # v1
        with:
          ref: ${{ needs.prepare.outputs.ref }}
          publish: ${{ needs.prepare.outputs.publish }}
          # Container repos add image + version so the body is a pull snippet:
          #   image: ghcr.io/<owner>/<repo>
          #   version: ${{ needs.prepare.outputs.version }}
```

### Artifact build (project-specific)

Insert a build step or matrix in the `build` job, producing exactly what the
project ships — native binaries (commonly Linux x64, Windows x64, macOS arm64),
a container image, or nothing but notes. Pass `${{ needs.prepare.outputs.version }}`
or `${{ needs.prepare.outputs.ref }}` to the build command.

`package-artifact` uploads each archive to the Actions run under its release
name; `publish-release` downloads them and publishes the GitHub release. Both
run on every build that is not skipped (skipped only when semver finds nothing
releasable, or on a dry run). The release body is templated in
`publish-release`, never hand-written in the caller — install instructions
belong in the repo's docs.

On a Forgejo+twin project, the Forgejo workflow's `build` job dispatches the
twin's release workflow with `ref: ${{ needs.prepare.outputs.ref }}` rather
than publishing locally.
