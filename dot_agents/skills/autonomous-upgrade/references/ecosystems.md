# Ecosystems: the 14-day cooldown

The quarantine window is enforced by the **package manager's own config**, not
by a bot. That matters: only the resolver sees transitive versions, so a
hand-rolled date filter on direct dependencies leaves the real attack surface
uncovered.

## At a glance

| Ecosystem | Upgrade command | Where the cooldown lives |
|---|---|---|
| **Bun** | `bun update` | `bunfig.toml` → `[install] minimumReleaseAge = 1209600` (seconds) |
| **Cargo** ≥1.100 | `cargo update` | `.cargo/config.toml` → `[registry] global-min-publish-age = "14 days"` |
| **npm** | `npx npm-check-updates -u -t minor` | no config file — pass `--cooldown 14d` on the command line |
| **pnpm** | `pnpm update` | `pnpm-workspace.yaml` → `minimumReleaseAge: 20160` (**minutes**) |
| **Go** | `go get -u ./...` | **no native gate** — skip autonomous bumps |
| **uv / pip** | `uv lock --upgrade` | **no native gate** — skip autonomous bumps |

## The units trap

Getting the unit wrong **silently disables the cooldown** — no error, just an
unquarantined supply chain.

| Tool | Unit | 14 days |
|---|---|---|
| Bun | seconds | `1209600` |
| pnpm | minutes | `20160` |
| Cargo | duration string | `"14 days"` |
| npm-check-updates | unit-suffixed string | `14d` |

Verify the resolved value after writing it.

## Bun

```toml
[install]
# Supply chain security: quarantine any package version for 14 days (1209600s)
minimumReleaseAge = 1209600
# Optional: trusted packages exempt from the age gate
minimumReleaseAgeExcludes = ["@types/node", "typescript"]
```

The gate filters direct **and transitive** dependencies. When it blocks a
version, Bun runs a stability check and may prefer an older, more mature
version.

## Cargo

Stabilized in **Cargo 1.100** (2026-08-28) — stable channel, no `-Z`, no
nightly toolchain. Two keys, and **both matter**:

- `[registry] global-min-publish-age` — the window. Accepts an integer plus
  `seconds`/`minutes`/`hours`/`days`/`weeks`/`months`, or `"0"` for no limit.
  **Default is `"0"`**, so this must be set explicitly.
- `[resolver] incompatible-publish-age` — what to do with a too-new version.
  Defaults to `"deny"` (skip it unless already in `Cargo.lock`), which is what
  you want. `"allow"` disables the quarantine entirely.

```toml
[registry]
# Supply chain security: quarantine any crate version for 14 days.
# Stable since Cargo 1.100. Requires a registry that publishes `pubtime`.
global-min-publish-age = "14 days"

[resolver]
# "deny" (the default) skips too-new versions unless already in Cargo.lock.
# Do NOT set this to "allow" — that disables the cooldown.
incompatible-publish-age = "deny"
```

Force a critical security fix through on demand, without editing the config:

```bash
CARGO_RESOLVER_INCOMPATIBLE_PUBLISH_AGE=allow cargo update -p <crate>
```

**`cargo update`, not `cargo upgrade`.** The cooldown lives in the resolver, so
it governs `cargo update`. `cargo upgrade` (cargo-edit) rewrites `Cargo.toml`
version requirements and is **not** covered by the gate.

Cargo warns on older toolchains (`warning: ignoring
registry.global-min-publish-age without -Zmin-publish-age`), which means the
cooldown is *not* applying — a runner below 1.100 upgrades unprotected.

## npm

No config file, so the threshold and target are CLI flags:

```bash
npx npm-check-updates -u -t minor --cooldown 14d
```

`-t minor` restricts updates to patch and minor versions, keeping breaking
major upgrades out of autonomous daily PRs (Rule 5). When used with `--cooldown`,
it upgrades to the highest minor/patch version that has passed quarantine.

## pnpm

```yaml
# pnpm-workspace.yaml
minimumReleaseAge: 20160   # minutes — 14 days
```

## Ecosystems with no native gate

Go and uv/pip have no built-in age filter. Options, in order of preference:

1. Skip autonomous dependency bumps for that project entirely.
2. Renovate, which has a cross-ecosystem `minimumReleaseAge` — but adds a
   service to the stack.
3. A hand-rolled script (discouraged: misses transitive versions).

Do not quietly ship a no-op cooldown. If an ecosystem has no native gate, say
so and let the owner choose.

## Package-manager-agnostic version bumping (`just bump`)

To keep the `bump-version` workflow independent of manifest formats (`Cargo.toml`,
`package.json`, `pyproject.toml`, etc.), repos define a `bump` recipe in their
root `justfile`:

```bash
just bump <version>    # e.g. just bump 1.2.3 (without the 'v' prefix)
```

The workflow executes `just bump "$NEXT_STRICT"`, then stages all modified
tracked files (`git add -u`). It doesn't need to know which files were edited.

### Recipes per ecosystem

| Ecosystem | Manifest file(s) | `justfile` recipe |
|---|---|---|
| **Bun / Node** | `package.json`, lockfile | `bump version:`<br>`    npm version --no-git-tag-version {{version}}` |
| **Cargo (single crate)** | `Cargo.toml`, `Cargo.lock` | `bump version:`<br>`    cargo set-version {{version}}`<br>*(or `sed -i -E '0,/^version = ".*"/s//version = "{{version}}"/' Cargo.toml && cargo check`)* |
| **Cargo (workspace)** | `Cargo.toml`, `Cargo.lock` | `bump version:`<br>`    sed -i -E '0,/^version = ".*"/s//version = "{{version}}"/' Cargo.toml`<br>`    sed -i -E '/name = "<crate-prefix>/ { n; s/version = ".*"/version = "{{version}}"/; }' Cargo.lock` |
| **Python (uv)** | `pyproject.toml` | `bump version:`<br>`    uv version {{version}}` |
| **Python (poetry)** | `pyproject.toml` | `bump version:`<br>`    poetry version {{version}}` |
| **Go** | Git tags only (or constant) | `bump version:`<br>`    @echo "Go versions are tracked via git tags"`<br>*(or update constant in `internal/version/version.go`)* |

The workflow runs `git diff --staged --quiet` immediately after the recipe. If
`just bump` failed to modify any file, the workflow halts with an error rather
than pushing a commit that claims a version bump without touching anything.
