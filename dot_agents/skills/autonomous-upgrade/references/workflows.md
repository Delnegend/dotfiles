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
      #   Cargo → dtolnay/rust-toolchain@stable (needs ≥1.100 for the cooldown),
      #            then `cargo update` (reads .cargo/config.toml)
      #   npm   → actions/setup-node@v4, then
      #            `npx npm-check-updates -u -t minor --cooldown 14d && npm install`
      - uses: oven-sh/setup-bun@v2
        with:
          bun-version: latest

      - name: Upgrade (cooldown enforced by bunfig.toml)
        run: bun update

      - name: Detect whether anything changed
        id: diff
        run: |
          if git diff --quiet; then
            echo "changed=false" >> "$GITHUB_OUTPUT"
          else
            echo "changed=true" >> "$GITHUB_OUTPUT"
          fi

      - name: Open upgrade PR
        if: steps.diff.outputs.changed == 'true'
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "actions@users.noreply.github.com"
          git checkout -B deps/automatic
          git add -u
          git commit -m "chore(deps): upgrade dependencies"
          git push --force origin deps/automatic
          gh pr create --fill --base main --head deps/automatic \
            --title "chore(deps): upgrade dependencies" \
            --body "Automated daily upgrade. Versions published less than 14 days ago were filtered out by the package manager."
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
```

The job `name:` must match the branch protection context exactly.

### B2. CI gate for Forgejo+twin repos (checks + security scans in parallel)

Single-host repos use template B as-is. When the repo has a GitHub twin, the
CI workflow (authored in the source repo's `.github/workflows/`, synced into
the twin by the dispatch action) runs `just check` **plus the four security
scans as parallel jobs** — each fetches the source from Forgejo at
`inputs.ref` first. Security scanning is GitHub-runners-only: the scan jobs
need Docker images and registry egress that self-hosted Forgejo runners
typically lack.

```yaml
jobs:
  check:
    name: Check (just check)
    runs-on: ubuntu-latest
    steps:
      # ... fetch source, language setup ...
      - name: Run checks
        run: just check

  secret-scan: # Gitleaks — full history (fetch-depth: 0)
  sast-scan: # Semgrep OSS --config=auto --error
  trivy-scan: # Trivy fs, HIGH+CRITICAL only, --exit-code 1
  osv-scan: # OSV-Scanner --recursive
  # Each scan job: fetch source from Forgejo at inputs.ref, then one docker run.
  # Self-owned action refs carry `# nosemgrep`; third-party refs are SHA-pinned.
  # No ${{ }} interpolation inside run: blocks (env: first).
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
the three without changing anything. Manifest-less repos (Go: `just bump` is a
no-op echo) skip the bump/commit and tag HEAD directly.

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
        env:
          INPUT_REF: ${{ inputs.ref }}
          DRY_RUN: ${{ inputs.dry-run }}
          GATE_SHA: ${{ github.sha }}
          BUMP: ${{ steps.semver.outputs.bump }}
          CURRENT: ${{ steps.semver.outputs.current }}
          NEXT: ${{ steps.semver.outputs.next }}
          NEXT_STRICT: ${{ steps.semver.outputs.nextStrict }}
        run: |
          set -euo pipefail
          # TOCTOU guard: the gate ran on GATE_SHA. If main moved since,
          # the checkout below is ungated code — refuse to ship it.
          # (Ref paths pin their own commit, so they skip this check.)
          if [ -z "$INPUT_REF" ]; then
            HEAD_SHA="$(git rev-parse HEAD)"
            if [ "$HEAD_SHA" != "$GATE_SHA" ]; then
              echo "::error::main moved during the gate ($GATE_SHA -> $HEAD_SHA); re-run to gate the new HEAD."
              exit 1
            fi
          fi
          # Dispatch guide: empty = ship, SHA = test, tag = rebuild.
          # Dry-run first: a preview must never mutate, on any path.
          if [ "$DRY_RUN" = "true" ]; then
            if echo "$INPUT_REF" | grep -qE '^[0-9a-f]{7,64}$'; then
              echo "[dry-run] would test-build commit $INPUT_REF (no publish)"
            elif [ -z "$INPUT_REF" ]; then
              echo "[dry-run] would bump to $NEXT_STRICT, tag $NEXT, push, build, and publish"
            elif echo "$INPUT_REF" | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+$'; then
              echo "[dry-run] would rebuild tag $INPUT_REF and publish it"
            else
              echo "::error::ref must be empty, a commit SHA (7-64 hex), or a version tag (vX.Y.Z); got '$INPUT_REF'."
              exit 1
            fi
            echo "skip=true" >> "$GITHUB_OUTPUT"
            exit 0
          fi
          # SHA test-build: 7-64 hex only (short SHAs misroute or collide).
          if echo "$INPUT_REF" | grep -qE '^[0-9a-f]{7,64}$'; then
            echo "Test build against commit $INPUT_REF (will not publish)."
            { echo "ref=$INPUT_REF"; echo "version=$INPUT_REF"; echo "publish=false"; echo "skip=false"; } >> "$GITHUB_OUTPUT"
            exit 0
          fi
          # Tag rebuild: strict format, must already exist.
          if [ -n "$INPUT_REF" ]; then
            echo "$INPUT_REF" | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+$' || { echo "::error::ref must be a commit SHA or a version tag (vX.Y.Z); got '$INPUT_REF'."; exit 1; }
            git rev-parse -q --verify "refs/tags/$INPUT_REF" >/dev/null || { echo "::error::tag $INPUT_REF does not exist."; exit 1; }
            echo "Rebuilding existing tag $INPUT_REF."
            { echo "ref=$INPUT_REF"; echo "version=${INPUT_REF#v}"; echo "publish=true"; echo "skip=false"; } >> "$GITHUB_OUTPUT"
            exit 0
          fi
          # Recovery before the BUMP=none exit: a previous run may have pushed
          # the bump commit but died before tagging. semver sees only the
          # non-conventional chore(release) commit and reports none — but the
          # manifest is ahead of the latest tag, so there IS work to do.
          # Adapt to the ecosystem (see ecosystems.md for manifest paths).
          LATEST_TAG="$(git tag -l 'v[0-9]*.[0-9]*.[0-9]*' --sort=-v:refname | head -n1 || true)"
          MANIFEST_VER="..."  # e.g. $(grep -m1 '^version = ' Cargo.toml | cut -d'"' -f2)
          if [ -n "$LATEST_TAG" ] && [ "v$MANIFEST_VER" != "$LATEST_TAG" ] && [ "$(printf '%s\n%s\n' "v$MANIFEST_VER" "$LATEST_TAG" | sort -V | head -n1)" = "$LATEST_TAG" ]; then
            echo "Manifest ($MANIFEST_VER) is ahead of latest tag ($LATEST_TAG); tagging the stranded commit."
            git config user.name "github-actions[bot]"
            git config user.email "actions@users.noreply.github.com"
            TAG="v$MANIFEST_VER"
            git tag -a "$TAG" -m "Release $TAG"
            git push origin "refs/tags/$TAG"
            { echo "ref=$TAG"; echo "version=$MANIFEST_VER"; echo "publish=true"; echo "skip=false"; } >> "$GITHUB_OUTPUT"
            exit 0
          fi
          # Nothing releasable since the last tag: clean exit, no noise.
          if [ "$BUMP" = "none" ]; then
            echo "No version bump needed (current: ${CURRENT:-none})."
            echo "skip=true" >> "$GITHUB_OUTPUT"
            exit 0
          fi
          # Refuse to re-ship: NEXT must sort after the latest tag.
          if [ -n "$LATEST_TAG" ]; then
            if [ "$NEXT" = "$LATEST_TAG" ] || [ "$(printf '%s\n%s\n' "$NEXT" "$LATEST_TAG" | sort -V | head -n1)" = "$NEXT" ]; then
              echo "::error::Calculated $NEXT is not ahead of latest tag $LATEST_TAG; nothing new to ship."
              exit 1
            fi
          fi
          git config user.name "github-actions[bot]"
          git config user.email "actions@users.noreply.github.com"
          # Package-manager agnostic: delegates to `just bump` (see ecosystems.md).
          # Manifest-less repos (Go) skip this: no file to bump, tag HEAD directly.
          just bump "$NEXT_STRICT"
          git add -u
          git diff --staged --quiet && { echo "::error::bump produced no change in package files"; exit 1; }
          git commit -m "chore(release): ${NEXT}"
          # Push the commit first: if the tag push fails, the next run
          # recovers via the manifest-ahead check above.
          git push origin HEAD:main
          git rev-parse -q --verify "refs/tags/${NEXT}" >/dev/null && { echo "::error::tag ${NEXT} already exists"; exit 1; }
          git tag -a "${NEXT}" -m "Release ${NEXT}"
          git push origin "refs/tags/${NEXT}"
          { echo "ref=$NEXT"; echo "version=$NEXT_STRICT"; echo "publish=true"; echo "skip=false"; } >> "$GITHUB_OUTPUT"

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
      # Project-specific build step (binaries, packages, container images)
      # Produces files in dist/ (or your artifact directory)
      # -----------------------------------------------------------------------

      - name: Upload build artifacts (always kept in Actions run, including SHA test-builds)
        uses: actions/upload-artifact@v4
        with:
          name: build-artifacts-${{ needs.prepare.outputs.ref }}
          path: dist/
          if-no-files-found: ignore

      - name: Publish Consolidated Release
        # SHA test-builds set publish=false: artifacts upload above, nothing ships.
        # Container repos also gate login + push: push ${{ publish == 'true' }}, load ${{ publish != 'true' }}.
        if: needs.prepare.outputs.publish == 'true'
        uses: softprops/action-gh-release@v3
        with:
          tag_name: ${{ needs.prepare.outputs.ref }}
          generate_release_notes: true
          files: dist/*
```

### Artifact build (project-specific)

Insert a build step or matrix in the `build` job, producing exactly what the
project ships — native binaries (commonly Linux x64, Windows x64, macOS arm64),
a package, or nothing but notes. Pass `${{ needs.prepare.outputs.version }}` or
`${{ needs.prepare.outputs.ref }}` to the build command.

`actions/upload-artifact@v4` runs on every build that is not skipped (skipped
only when semver finds nothing releasable, or on a dry run):
- Every build uploads to the Actions run AND publishes to GitHub Releases.

On a Forgejo+twin project, the Forgejo workflow's `build` job dispatches the
twin's release workflow with `ref: ${{ needs.prepare.outputs.ref }}` rather
than publishing locally.

The template above is notes-only, for a project with no build artifacts.
