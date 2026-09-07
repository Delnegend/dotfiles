# AGENTS.md

## Key commands

```bash
chezmoi status    # what would change
chezmoi diff      # detailed diff
chezmoi apply -v  # apply
just              # choose recipes interactively (reads ~/.justfile)
just --list       # see individual recipes
just brew-dump    # regenerate ~/Brewfile from installed packages
```

## Architecture

- chezmoi-managed: repo root (`~/.local/share/chezmoi`) is the default `sourceDir` (no config override); `dot_*`/`private_*` map to `$HOME`, `.tmpl` renders per-OS via `{{ if eq .chezmoi.os "windows" }}`
- `run_once_*` = one-shot setup (Homebrew, `~/.bashrc` wiring); `run_onchange_*` = re-runs when hashed `include`d files change; all Linux-only scripts are gated with `{{ if eq .chezmoi.os "linux" }}`
- `dot_justfile` (`~/.justfile`) = general-purpose recipes only — never symlink/setup logic (that's chezmoi's job)
- When adding a new config file or unit, update the Layout section in `README.md` too

## JSON config convention

Zed themes are stored as plain `.json` in `dot_config/zed/themes/` (converted from upstream `microsoft/vscode` via `sync-zed-vscode-theme.py`, run `just zed-theme-sync` after VSCode updates):

```
dot_config/zed/themes/foo.json  →  ~/.config/zed/themes/foo.json
```

## Shell config

- `dot_bashrc_custom` (`~/.bashrc_custom`) is the shell entry point — all shell config lives there (per-machine `case` at the top, then env, aliases, container, tool init, auto-update)
- `run_once_10-bootstrap.sh.tmpl` appends `source ~/.bashrc_custom` to `~/.bashrc` once (and migrates the old `cfg-system` path)

## Flatpak config paths

Flatpak apps store config in `~/.var/app/<app-id>/config/<app-name>/`, managed as plain chezmoi files:

```
dot_var/app/io.mpv.Mpv/config/mpv/  →  ~/.var/app/io.mpv.Mpv/config/mpv/
```

## Systemd user units

- Unit files live in `dot_config/systemd/user/` → `~/.config/systemd/user/`
- `run_onchange_30-systemd.sh.tmpl` runs `daemon-reload` then enables units; add new units there (hash `include` line) so changes re-trigger
- Use `ConditionPathExists=` for optional executables (e.g., AppImages) so the unit is skipped, not failed, when the binary is missing

## Brewfile

- `dot_Brewfile` (`~/Brewfile`) is the source of truth; do not edit by hand, run `just brew-dump` to update it
