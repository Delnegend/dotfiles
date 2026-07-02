# dotfiles

## Bootstrap

```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install git-lfs
brew install git-lfs && git lfs install

# Clone the repo
git clone --depth=1 git@github.com:Delnegend/dotfiles.git
cd dotfiles

# Pull LFS objects (needed for fonts and archives)
git lfs pull
```

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

.justfile                     # setup recipes for this dotfiles repo (symlinks, fonts)
.justfile_custom              # general-purpose recipes for the host OS (backups, transcoding, system utils)
```
