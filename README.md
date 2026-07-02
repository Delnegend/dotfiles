# dotfiles

## Bootstrap

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Delnegend/dotfiles/main/scripts/bootstrap.sh)
```

This installs Homebrew, clones the repo to `~/dotfiles`, and adds a `source ~/dotfiles/.bashrc_custom` line to `~/.bashrc` to load custom shell config.

Then run `just all` from `~/dotfiles` to symlink everything else, or `just --list` to see individual recipes.

After setting up shell config, add a machine-specific file if one doesn't exist:

```bash
# ~/dotfiles/.bashrc.d/machines/$(hostname -s).sh
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

.justfile                     # setup recipes for this dotfiles repo (symlinks, fonts)
.justfile_custom              # general-purpose recipes for the host OS (backups, transcoding, system utils)
```
