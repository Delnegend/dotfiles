# AGENTS.md

## Key commands

```bash
chezmoi status    # what would change
chezmoi diff      # detailed diff
chezmoi apply -v  # apply (also runs pending run_* scripts)
chezmoi re-add <target>  # pull a destination change back into source (needed after just brew-dump)
chezmoi execute-template --file <tmpl> --override-data '{"chezmoi":{"os":"linux"}}'  # render the other OS
just --list       # recipes in ~/.justfile
```

## Architecture

- chezmoi source = repo root (`~/.local/share/chezmoi`, no config override). `dot_*`/`private_*` (0600/0700) map to `$HOME`; `.tmpl` renders per-OS via `{{ if eq .chezmoi.os "windows" }}`.
- No git remote by design (repo deleted on GitHub; sensitive docs live in `~/Desktop/docs`, history purged). Never add a remote or push without asking.
- `run_once_*` = one-shot setup; `run_onchange_*` re-runs only when a hashed `include`d file changes. Linux-only scripts are `{{ if eq .chezmoi.os "linux" }}`-gated (render empty → skipped on Windows).
- Linux-only files (systemd units, fontconfig, flatpak `dot_var/`, `dot_Brewfile`, `dot_bashrc_custom`) also land on Windows — harmless by design, don't "fix" with ignores.
- `dot_justfile` must stay a plain file: just's own `{{ }}` syntax collides with chezmoi templating, so it can never become `.tmpl`. Recipe paths hardcode `~/.local/share/chezmoi`.
- chezmoi never deletes destination files removed from source — after renaming/removing a managed file, delete the old target by hand.
- Machines: `wsl`, `homelab` (SSH alias `core`), `bazzite`. `dot_bashrc_custom` branches on `$(hostname -s)`; new hosts need a branch there.
- When adding a config file or unit, update the Layout section in `README.md` too.

## Workflows

- Brewfile: `just brew-dump` writes `~/Brewfile` (destination side), then `chezmoi re-add ~/Brewfile` updates `dot_Brewfile`. Never hand-edit either side directly.
- Zed themes: plain `.json` in `dot_config/zed/themes/`, regenerated from upstream `microsoft/vscode` via `just zed-theme-sync`. Recipes call `python3`, which is broken on Windows — run them on Linux.
- Systemd: units live in `dot_config/systemd/user/`; when adding one, also add a hash `include` line in `run_onchange_30-systemd.sh.tmpl` or it won't auto-enable. Use `ConditionPathExists=` for optional binaries. (`dotfiles-pull.*` is inert while there is no remote.)
- Shell: `dot_bashrc_custom` (`~/.bashrc_custom`) is the entry point; `run_once_10-bootstrap.sh.tmpl` appends the `source` line to `~/.bashrc` once.
