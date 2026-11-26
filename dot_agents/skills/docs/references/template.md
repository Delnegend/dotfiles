# Project README Template (`common-facade`)

All maintained repositories generate `README.md` and `LICENSE*` from `README.yml`
using [`common-facade`](https://github.com/Delnegend/common-facade), validated in
CI by `Delnegend/actions/.github/workflows/scan.yml`. Keep the generated
`README.md` under 100 lines.

## Primary Template: `README.yml`

````yaml
$schema: "https://raw.githubusercontent.com/Delnegend/common-facade/main/README.schema.json"

name: <Project Name>
repo: Delnegend/<repo>
tagline: "<One clear sentence: what this project does and the outcome it provides. Plain words, no jargon.>"

badges:
  ci: true
  release: true
  license: true
  # Optional custom badges (use badgers.space with corner_radius=0):
  # custom:
  #   - label: Crates.io
  #     image: https://badgers.space/crates/version/<crate>?corner_radius=0&color=ea7233
  #     url: https://crates.io/crates/<crate>

quick_start: |
  ```bash
  # 1. Install (Linux and macOS)
  brew install Delnegend/tap/<formula>

  # 2. Run
  <project> ...
````

Verify with `<project> --version` (CLIs) or `curl --fail http://127.0.0.1:<port>/health` (services).

highlights:

- "**<Outcome 1>**: <Plain-language benefit, e.g. Instant startup under 15ms with low memory footprint.>"
- "**<Outcome 2>**: <Concrete capability, e.g. Zero configuration with sensible production defaults.>"
- "**<Outcome 3>**: <Reliability or ease, e.g. Single static binary with no external runtime dependencies.>"

documentation:
architecture: "<Component boundaries, data flows, and invariants.>"
development: "<Prerequisites, build steps, `just check` gate, and test suite.>"
deployment: "<Install via Homebrew tap, services, logs, upgrades, and [configuration](docs/configuration.md).>"

license:
type: - MIT - APACHE-2.0
holder: "Delnegend"

````

Generate and verify:

```bash
common-facade        # writes README.md and LICENSE* from README.yml
common-facade check  # verifies zero drift (same check CI runs)
````

### Schema Notes

- **Three required `documentation` slots**: `architecture` (`docs/architecture.md`),
  `development` (`docs/development.md`), and `deployment` (`docs/deployment.md`).
  Each slot accepts either a plain description string or an object
  `{ title, path, description }` (useful for libraries linking `docs.rs` or
  `docs/configuration.md`).
- **Linking extra `docs/**/*.md` files**: `scan.yml`'s `docs-references` job
  requires every Markdown file under `docs/` to appear in `README.md`. Link
  extra guides (e.g. `docs/configuration.md`, `docs/cli.md`) inline inside the
  slot descriptions or `quick_start`.
- **License options**:
  - Rust / Go projects default to dual `type: [MIT, APACHE-2.0]` (generates `LICENSE-MIT` and `LICENSE-APACHE`).
  - Single-license repos set `type: [MIT]` (with optional `filename: "LICENSE"`).
  - Internal/private repos set `type: false` (with optional `note:`).
- **Badges**: `common-facade` renders `badgers.space` badges (`corner_radius=0`).
  For non-default CI workflow files or branches, pass `ci: { workflow: "ci.yaml", branch: "main" }`.

---

## Install Ladder

The install step in `quick_start` follows this order; topmost available wins.
Never skip a rung for the sake of variety:

1. **Homebrew tap**: `brew install Delnegend/tap/<formula>`. The primary method
   on Linux and macOS whenever a formula exists.
2. **Latest-release asset**: resolve the asset from the latest release at
   install time (API lookup by filename suffix). Never pin a version in the
   command; a pinned URL rots on the next release.
3. **Source build**: `cargo install`, `go install`, `go build` from a checkout.
   Last resort only, and say so in one clause.

---

## Customization Guidelines

- **CLI tools:** `quick_start` is `brew install Delnegend/tap/<formula>` (or the install ladder fallback), primary command, and `--version` verify.
- **Libraries / SDKs:** `quick_start` shows `cargo add` / `import` plus a minimal runnable example. Set `badges.release: false` if releases are via crates.io with a `custom` `badgers.space/crates/version/...` badge, and override `documentation.architecture` to point to `docs.rs`.
- **Containers / Services:** `quick_start` downloads `compose.yml` (and `.env.example` if needed), runs `docker compose up -d` or `podman compose up -d`, and verifies health/logs.
- **Dotfiles / Non-facade repos:** For repos that do not use `common-facade` (e.g. `dotfiles`, `homebrew-tap`, `Delnegend/actions`), author `README.md` directly using the same 4-section layout (`Quick Start`, `Highlights`, `Documentation`, `License`) and `badgers.space` badges:

```markdown
<div align="center">

# <project-name>

**<One clear sentence: what this project does and the outcome it provides.>**

[![CI](https://badgers.space/github/checks/<owner>/<repo>/main?corner_radius=0&label=build)](https://github.com/<owner>/<repo>/actions)
[![Release](https://badgers.space/github/release/<owner>/<repo>?corner_radius=0&color=ea7233)](https://github.com/<owner>/<repo>/releases)
[![License](https://badgers.space/badge/license/MIT/007ec6?corner_radius=0)](LICENSE)

</div>

---

## Quick Start

...

## Highlights

...

## Documentation

...

## License

...
```
