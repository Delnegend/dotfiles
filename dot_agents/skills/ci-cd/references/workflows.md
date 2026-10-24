# Workflow templates

Four workflow templates plus Dependabot for GitHub Actions. Path and runner label
follow the host (see `hosts.md`); the substance does not change.

## A. Dependency upgrade job (`deps.yml`)

Runs daily via the shared `reusable-deps-update.yml` workflow, opening one PR
with the upgraded manifest and lockfile behind the 14-day publish quarantine.
Toolchains are opt-in (`cargo`, `bun`, `bun-dir`).

### GitHub Actions (reusable workflow)

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
    uses: Delnegend/actions/.github/workflows/reusable-deps-update.yml@<pin-sha> # v1
    with:
      cargo: true # opt in: cargo, bun, bun-dir
```

### Forgejo (Native AGit)

On native Forgejo instances, use **AGit** (`refs/for/main`) to open or update the
PR directly over Git transport — zero extra CLI tools (`gh`/`fj`) and zero extra
tokens needed:

```yaml
name: Dependency updates

on:
  schedule:
    - cron: '0 2 * * *'
  workflow_dispatch:

jobs:
  update:
    runs-on: alpine
    steps:
      - uses: actions/checkout@v7
      # ... run package manager update with cooldown ...
      - name: Open upgrade PR (Forgejo AGit)
        if: steps.diff.outputs.changed == 'true'
        run: |
          git config user.name "actions[bot]"
          git config user.email "actions@git.local"
          git checkout -B deps/automatic
          git add -u
          git commit -m "chore(deps): upgrade dependencies" \
            -m "Automated daily upgrade. Versions published less than 14 days ago were filtered out by the package manager."
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
source is private on Forgejo while the twin on GitHub holds no source code.
The `check` job fetches source using `Delnegend/actions/twin-checkout`, and
the `scan` job calls the shared `scan.yml` bundle with `forgejo: true`:

```yaml
jobs:
  check:
    name: Check (just check)
    runs-on: ubuntu-latest
    steps:
      - name: Fetch source from Forgejo
        uses: Delnegend/actions/twin-checkout@<pin-sha> # v1
        with:
          token: ${{ secrets.FORGEJO }}
          ref: ${{ inputs.ref || 'main' }}

      # ... language setup (e.g. rust-toolchain, setup-just) ...

      - name: Run checks
        run: just check

  scan:
    name: Scan
    uses: Delnegend/actions/.github/workflows/scan.yml@<pin-sha> # v1
    with:
      ref: ${{ inputs.ref || 'main' }}
      forgejo: true
    secrets:
      forgejo_token: ${{ secrets.FORGEJO }}
    permissions:
      contents: read
```

## C. Auto-merge (`auto-merge.yml`)

### GitHub Actions (reusable workflow)

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
    uses: Delnegend/actions/.github/workflows/reusable-auto-merge.yml@<pin-sha> # v1
```

### Forgejo

`fj` has **no `--auto` flag** (see `hosts.md`). Either enable auto-merge in the Forgejo UI, or gate with `fj pr status --wait`:

```bash
fj pr status "$PR_NUM" -H "$FORGEJO_HOST" --wait
fj pr merge "$PR_NUM" -H "$FORGEJO_HOST" --method rebase --delete
```

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
`just version set` is a no-op echo) skip the bump/commit and tag HEAD directly.

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
      # Insert any language setup needed by `just version set` (e.g. setup-go, setup-node)

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
```

### D2. Container release workflow (`release.yml`)

For repositories that publish a container image to GitHub Container Registry (GHCR):

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
        description: "Preview only: print each action without mutating."
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
  gate:
    name: Gate (all of CI)
    uses: ./.github/workflows/ci.yml

  prepare:
    name: Prepare (bump, tag, push)
    needs: gate
    runs-on: ubuntu-latest
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
          fetch-depth: 0
      - uses: extractions/setup-just@v4

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
    runs-on: ubuntu-latest
    permissions:
      packages: write
    steps:
      - uses: actions/checkout@v7
        with:
          ref: ${{ needs.prepare.outputs.ref }}

      - name: Build and push image
        uses: Delnegend/actions/docker-build-push@<pin-sha> # v1
        with:
          version: ${{ needs.prepare.outputs.version }}
          publish: ${{ needs.prepare.outputs.publish }}

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
          container: true
          version: ${{ needs.prepare.outputs.version }}
```

### D3. Hybrid releases (binaries + container image)

For projects shipping both release archives and a container image, package binaries with `package-artifact`, build the image with `docker-build-push`, then pass `container: true` and `download: "true"` to `publish-release`:

```yaml
  publish:
    name: Publish Consolidated Release
    needs: [prepare, build-binaries, build-container]
    if: needs.prepare.outputs.skip != 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: Delnegend/actions/publish-release@<pin-sha> # v1
        with:
          ref: ${{ needs.prepare.outputs.ref }}
          publish: ${{ needs.prepare.outputs.publish }}
          container: true
          download: "true"
          version: ${{ needs.prepare.outputs.version }}
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
