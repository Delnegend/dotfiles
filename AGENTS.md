# AGENTS.md

## Key commands

```bash
chezmoi status    # what would change
chezmoi diff      # detailed diff
chezmoi apply -v  # apply (also runs pending run_* scripts)
chezmoi re-add <target>  # pull a destination change back into source
chezmoi execute-template --file <tmpl> --override-data '{"chezmoi":{"os":"linux"}}'  # render the other OS
just --list       # recipes in ~/.justfile (bazzite)
```

## Architecture

- chezmoi source = repo root (`~/.local/share/chezmoi`, no config override). `dot_*`/`private_*` (0600/0700) map to `$HOME`; `.tmpl` renders per-OS via `{{ if eq .chezmoi.os "windows" }}`.
- Remote: `github.com:Delnegend/dotfiles.git` (SSH origin, public repo). Never push without asking.
- `run_once_*` = one-shot setup; `run_onchange_*` re-runs only when a hashed `include`d file changes. Linux-only scripts are `{{ if eq .chezmoi.os "linux" }}`-gated (render empty → skipped on Windows).
- Linux-only and Bazzite-only files are scoped via `.chezmoiignore` (plus `ConditionPathExists=`/`ConditionHost=` in systemd units).
- `dot_justfile.tmpl` is a chezmoi template; escape any literal just `{{ }}` syntax inside it (e.g. `{{ "{{" }}args}}`).
- chezmoi never deletes destination files removed from source; after renaming/removing a managed file, delete the old target by hand.
- Machines: `wsl`, `homelab` (SSH alias `core`), `bazzite`. `dot_bashrc_custom.tmpl` branches on `{{ .chezmoi.hostname }}`; new hosts need a branch there.
- When adding a config file or unit, update `docs/layout.md` too.

## Workflows

- Zed themes: plain `.json` in `dot_config/zed/themes/`, regenerated from upstream `microsoft/vscode` via `just zed-theme-sync`. Recipes call `python3`, which is broken on Windows — run them on Linux.
- Systemd: units live in `dot_config/systemd/user/`; when adding one, also add a hash `include` line in `run_onchange_30-systemd.sh.tmpl` or it won't auto-enable. Use `ConditionPathExists=` for optional binaries.
- Shell: `dot_bashrc_custom.tmpl` (`~/.bashrc_custom`) is the entry point; `run_once_10-bootstrap.sh.tmpl` appends the `source` line to `~/.bashrc` once.
