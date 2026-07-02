# dotfiles

## Setup

Clone the repo, `cd` into it, then run `just all` to symlink everything, or `just --list` to see individual recipes.

After setting up shell config, add a machine-specific file if one doesn't exist:

```bash
# .bashrc.d/machines/$(hostname -s).sh
```

## Layout

```
.gitconfig                    # Git config
.bashrc_custom                # entry point — sources .bashrc.d/
.bashrc.d/
  00-env.sh                   # universal environment variables
  10-aliases.sh               # universal aliases
  *.sh                        # more universal files, sourced in order
  machines/
    bazzite.sh                # per-machine config, sourced by hostname

.config/
  opencode.jsonc              # opencode config
  zed.jsonc                   # Zed editor settings
  vscode/                     # VS Code settings, keybindings, snippets
  mpv/                        # mpv config (Flatpak)
  easyeffects/                # Easy Effects audio presets (Flatpak)
  fontconfig/                 # Font rendering settings

.justfile                     # setup recipes (symlinks)
.justfile_custom              # general-purpose recipe collection
```
