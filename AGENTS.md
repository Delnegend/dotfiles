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

- `.bashrc_custom` is the shell entry point — it sources all `[0-9]*.sh` files in `.bashrc.d/` in order
- Files in `.bashrc.d/` are sourced alphabetically → use numeric prefixes for ordering: `00-env.sh`, `10-aliases.sh`, etc.
- Per-machine config lives in `.bashrc.d/machines/<hostname>.sh` (sourced by hostname, not numeric prefix)
- Both `.bashrc_custom` and `.bashrc.d/` are symlinked from the repo

## Flatpak config paths

Flatpak apps store config in `~/.var/app/<app-id>/config/<app-name>/`. When symlinking these:
- Always `mkdir -p` the parent directory first (the recipe does this)
- Symlink the whole config directory, not individual files (e.g., `.config/mpv/` → `~/.var/app/io.mpv.Mpv/config/mpv`)

## Brewfile

- Managed by a pre-commit hook at `.git/hooks/pre-commit` — it auto-dumps `brew bundle dump` and stages `Brewfile` before each commit
- Do not edit `Brewfile` by hand; run `just brew-dump` to update it
