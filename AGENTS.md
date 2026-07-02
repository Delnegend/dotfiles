# AGENTS.md

## Key commands

```bash
just all          # symlink all configs at once
just --list       # see individual recipes
just brew-dump    # regenerate Brewfile from installed packages
```

## Architecture

- Symlink-based: repo files are the source of truth, symlinked into `~` or `~/.config/`
- Use `justfile_directory()` in just recipes, never hardcode repo paths
- `.justfile` = setup/symlink recipes; `.justfile_custom` = general-purpose recipes

## JSON config convention

Config files in `.config/` use `.jsonc` extension in the repo but are symlinked as `.json` to match what apps expect:

```
.config/zed.jsonc         →  ~/.config/zed/settings.json
.config/vscode/settings.jsonc  →  ~/.config/Code/User/settings.json
```

When adding a new JSON-with-comments config file, follow this pattern.

## Shell config

- `.bashrc_custom` is the shell entry point — it sources all `[0-9]*.sh` files in `~/dotfiles/.bashrc.d/` in order
- Files in `.bashrc.d/` are sourced alphabetically → use numeric prefixes for ordering: `00-env.sh`, `10-aliases.sh`, etc.
- Per-machine config lives in `~/dotfiles/.bashrc.d/machines/<hostname>.sh` (sourced by hostname, not numeric prefix)
- `.bashrc_custom` is sourced from `~/dotfiles/.bashrc_custom` via a one-liner appended to `~/.bashrc`; no symlinks needed

## Flatpak config paths

Flatpak apps store config in `~/.var/app/<app-id>/config/<app-name>/`. When symlinking these:
- Always `mkdir -p` the parent directory first (the recipe does this)
- Symlink the whole config directory, not individual files (e.g., `.config/mpv/` → `~/.var/app/io.mpv.Mpv/config/mpv`)

## Brewfile

- Do not edit `Brewfile` by hand; run `just brew-dump` to update it
