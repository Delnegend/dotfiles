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
Dependabot-specific. Two signals: the `dependencies` label (upgrade PRs) and
the `release/` branch prefix (release PRs opened by `release.yml`).

```yaml
name: Auto-merge dependencies and releases

on:
  pull_request:
    branches: [main]

permissions:
  contents: write
  pull-requests: write

jobs:
  automerge:
    if: contains(github.event.pull_request.labels.*.name, 'dependencies') || startsWith(github.event.pull_request.head.ref, 'release/')
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

The unified release workflow. Supports three execution targets:
1. **`new-tag`** *(Default / Weekly Cron)* — calculates next SemVer from commits,
   verifies CI is green, updates the package manifest via `just bump`, and opens
   a release PR. Auto-merge (section C) rebases it once checks are green;
   then `tag` builds and publishes. Never pushes to `main` directly, because
   branch protection blocks it. Manifest-less repos (Go: `just bump` is a
   no-op echo, versions live in git tags) skip the PR: `new-tag` tags HEAD
   directly and publishes.
2. **`tag`** — tags the merged release commit (or rebuilds an existing tag
   when `ref` is given) and publishes.
3. **`commit`** — test build against a commit (uploads Actions artifacts only, no release).

### Mode-dependent trigger

- **Maintenance mode:** scheduled weekly cron (`0 0 * * 0`, defaults to `new-tag`) + `workflow_dispatch`.
- **Active development:** `workflow_dispatch` only (no `on.schedule`).

```yaml
name: Release / Build Artifacts

on:
  workflow_dispatch:
    inputs:
      target:
        description: "Release mode / build target"
        required: true
        type: choice
        default: "new-tag"
        options:
          - new-tag  # CI gate -> bump -> open release PR (merge, then run tag)
          - tag      # Tag merged release commit (or rebuild ref) -> build & publish
          - commit   # Test build a commit -> Actions artifacts only (no release)
      ref:
        description: "Custom tag or commit SHA (optional, defaults to latest)"
        required: false
        type: string
  # Maintenance mode adds:
  # schedule:
  #   - cron: '0 0 * * 0' # Weekly: Sunday 00:00 UTC (defaults to target: new-tag)

concurrency:
  group: release-main
  cancel-in-progress: false

permissions:
  contents: write
  pull-requests: write

jobs:
  prepare:
    name: Prepare / Bump Version
    runs-on: ubuntu-latest   # Full runner for compiler/toolchain headroom during `just check`
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
      # Insert any language setup needed by `just check` (e.g. setup-go, setup-node)

      # -----------------------------------------------------------------------
      # Mode 1: new-tag (semver -> CI gate -> bump -> open release PR for review)
      # -----------------------------------------------------------------------
      - name: Calculate Next SemVer
        if: (inputs.target || 'new-tag') == 'new-tag'
        id: semver
        uses: ietf-tools/semver-action@v1
        with:
          token: ${{ github.token }}
          fallbackTag: v0.0.0
          noNewCommitBehavior: silent
          noVersionBumpBehavior: patch

      - name: CI Gate (verify code is green before bumping)
        if: (inputs.target || 'new-tag') == 'new-tag' && steps.semver.outputs.bump != 'none'
        # Single repo: runs `just check`
        # Forgejo+twin: dispatches CI to twin and waits (see hosts.md)
        run: just check

      - name: Bump package manager version
        if: (inputs.target || 'new-tag') == 'new-tag' && steps.semver.outputs.bump != 'none'
        env:
          NEXT_STRICT: ${{ steps.semver.outputs.nextStrict }}
        run: |
          set -euo pipefail
          # Package-manager agnostic: delegates to `just bump` (see ecosystems.md)
          just bump "$NEXT_STRICT"

      - name: Commit and open release PR
        if: (inputs.target || 'new-tag') == 'new-tag' && steps.semver.outputs.bump != 'none'
        id: release-pr
        env:
          NEXT_TAG: ${{ steps.semver.outputs.next }}
          GH_TOKEN: ${{ github.token }}
        run: |
          set -euo pipefail
          git config user.name "github-actions[bot]"
          git config user.email "actions@users.noreply.github.com"

          # Stage all modified tracked files (manifests and lockfiles)
          git add -u
          git diff --staged --quiet && { echo "::error::bump produced no change in package files"; exit 1; }
          git commit -m "chore(release): ${NEXT_TAG}"

          # Branch protection blocks a direct push to main, so open a PR.
          # The owner merges it (status checks run on the PR), then re-runs
          # the workflow with target=tag to tag and publish.
          BRANCH="release/${NEXT_TAG}"
          git checkout -b "$BRANCH"
          git push -u origin "$BRANCH"

          echo "branch=$BRANCH" >> "$GITHUB_OUTPUT"
          gh pr create --title "chore(release): ${NEXT_TAG}" \
            --body "Automated version bump to \`${NEXT_TAG}\`. Merge this PR, then run the release workflow with \`target=tag\` to build and publish." \
            --head "$BRANCH" --base main
        # Forgejo: replace the push + gh pr create with native AGit
        # (see hosts.md): git push origin HEAD:refs/for/main
        # -o topic="release/${NEXT_TAG}" -o force-push=false

      # -----------------------------------------------------------------------
      # Resolve outputs for Job 2 (build)
      # -----------------------------------------------------------------------
      - name: Resolve outputs
        id: resolve
        run: |
          set -euo pipefail
          TARGET="${{ inputs.target || 'new-tag' }}"
          INPUT_REF="${{ inputs.ref || '' }}"

          # new-tag only opens the release PR (branch protection blocks a
          # direct push to main). Merge the PR, then re-run with target=tag.
          if [ "$TARGET" = "new-tag" ]; then
            echo "skip=true" >> "$GITHUB_OUTPUT"
            BUMP="${{ steps.semver.outputs.bump }}"
            if [ "$BUMP" = "none" ]; then
              echo "No version bump needed (current: ${{ steps.semver.outputs.current }})."
            else
              echo "Release PR opened; merge it, then re-run with target=tag to build and publish."
            fi
            exit 0

          elif [ "$TARGET" = "tag" ]; then
            if [ -n "$INPUT_REF" ]; then
              # Re-run for an existing tag: build and publish it.
              TAG="$INPUT_REF"
            else
              # Normal path: tag the merged release commit. The version comes
              # from the manifest on main, which the release PR just bumped.
              # Adapt the grep to the ecosystem (see ecosystems.md for
              # manifest paths: Cargo.toml, package.json, pyproject.toml).
              MANIFEST_VER="..."  # e.g. $(grep -m1 '^version = ' Cargo.toml | cut -d'"' -f2)
              [ -n "$MANIFEST_VER" ] || { echo "::error::No version in manifest"; exit 1; }
              TAG="v$MANIFEST_VER"
              if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
                echo "Tag $TAG already exists; building it."
              else
                git config user.name "github-actions[bot]"
                git config user.email "actions@users.noreply.github.com"
                git tag -a "$TAG" -m "Release $TAG"
                # Tag-only push: allowed by branch protection (which guards branches, not tags).
                git push origin "refs/tags/$TAG"
              fi
            fi
            echo "ref=$TAG" >> "$GITHUB_OUTPUT"
            echo "version=${TAG#v}" >> "$GITHUB_OUTPUT"
            echo "publish=true" >> "$GITHUB_OUTPUT"
            echo "skip=false" >> "$GITHUB_OUTPUT"

          elif [ "$TARGET" = "commit" ]; then
            SHA="${INPUT_REF:-$(git rev-parse HEAD)}"
            echo "ref=$SHA" >> "$GITHUB_OUTPUT"
            echo "version=$SHA" >> "$GITHUB_OUTPUT"
            echo "publish=false" >> "$GITHUB_OUTPUT"
            echo "skip=false" >> "$GITHUB_OUTPUT"
            echo "Running test build against commit $SHA (will not publish release)"
          fi

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

      - name: Upload build artifacts (always kept in Actions run)
        uses: actions/upload-artifact@v4
        with:
          name: build-artifacts-${{ needs.prepare.outputs.ref }}
          path: dist/
          if-no-files-found: ignore

      - name: Publish Consolidated Release
        if: needs.prepare.outputs.publish == 'true'
        uses: softprops/action-gh-release@v3
        with:
          tag_name: ${{ needs.prepare.outputs.ref }}
          generate_release_notes: true
          files: dist/*
```

### Why `new-tag` opens a PR instead of pushing to `main`

The skill's own contract requires branch protection with a required status
check (`Check (just check)`). A workflow run cannot satisfy that check for its
own push — the check runs on the pushed commit, which does not exist yet — so
any `git push origin HEAD:main` from the release job fails with `GH006:
Protected branch update failed`. The release PR goes through the normal gate
(CI runs on the PR, the owner merges), and `target: tag` only pushes a tag,
which branch protection does not guard.

### Artifact build (project-specific)

Insert a build step or matrix in the `build` job, producing exactly what the
project ships — native binaries (commonly Linux x64, Windows x64, macOS arm64),
a package, or nothing but notes. Pass `${{ needs.prepare.outputs.version }}` or
`${{ needs.prepare.outputs.ref }}` to the build command.

`actions/upload-artifact@v4` runs on every build that is not skipped (`new-tag`
always skips the build; it only opens the PR):
- When running `target: tag`, artifacts are uploaded to the Actions run AND published to GitHub Releases.

On a Forgejo+twin project, the Forgejo workflow's `build` job dispatches the
twin's release workflow with `ref: ${{ needs.prepare.outputs.ref }}` rather
than publishing locally.

The template above is notes-only, for a project with no build artifacts.
