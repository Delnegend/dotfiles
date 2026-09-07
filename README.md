# dotfiles

## Bootstrap (chezmoi)

> **Managed with [chezmoi](https://www.chezmoi.io/)** — `~/dotfiles` is the chezmoi source directory (`sourceDir = ~/dotfiles` via `~/.config/chezmoi/chezmoi.toml`). `dot_*`/`private_*` map to `$HOME`, `.tmpl` files render per-OS, `run_*` scripts handle setup.

### Prerequisites

- **chezmoi** `>=2.40` (`winget install twpayne.chezmoi` on Windows, `brew install chezmoi` on Linux)
- **Git** + **Bitwarden Desktop** with **Settings → Enable SSH agent** on (Bitwarden holds the SSH key authorized on GitHub, Authentication Key)

### Linux

Ensure SSH agent forwarding is active (`ssh -A`) or your SSH key is added (`ssh-add`):

```bash
git clone git@github.com:Delnegend/dotfiles.git ~/dotfiles
mkdir -p ~/.config/chezmoi
printf 'sourceDir = "%s/dotfiles"\n' "$HOME" > ~/.config/chezmoi/chezmoi.toml
chezmoi apply -v
# run_once/run_onchange scripts handle Homebrew, fonts, systemd, flatpak, udev automatically
```

For a new machine, add a `case` branch in `dot_bashrc_custom` matching `$(hostname -s)` _or_ extend `dot_config/environment.d/ssh.conf.tmpl`.

### Windows

Prerequisites: [Bitwarden Desktop](https://bitwarden.com/download/) with **Settings → Enable SSH agent** on, [Git for Windows](https://gitforwindows.org/) (`git` + `C:\Windows\System32\OpenSSH\ssh.exe`), and Bitwarden holding an SSH key authorized on GitHub (Authentication Key). Install via winget if needed:

   ```powershell
   winget install Bitwarden.Bitwarden Git.Git twpayne.chezmoi -e
   ```

1. Disable the built-in OpenSSH agent (required for Bitwarden to own the pipe):
   `Services → OpenSSH Authentication Agent → Startup type: Disabled → Apply` (already `Stopped`/`Disabled` on this machine).

2. Clone and apply:

   ```powershell
   git clone git@github.com:Delnegend/dotfiles.git ~/dotfiles  # ~/ is %USERPROFILE% on Git Bash / PowerShell
   New-Item -ItemType Directory -Force -Path ~/.config/chezmoi | Out-Null
   @"
   sourceDir = "$($env:USERPROFILE.Replace('\','/'))/dotfiles"
   "@ | Set-Content ~/.config/chezmoi/chezmoi.toml -Encoding UTF8
   chezmoi apply -v
   ```

   Chezmoi manages `~/.gitconfig` (`dot_gitconfig.tmpl` with OS-conditional `helper`/`program`/`sshCommand`), `~/.ssh/config` (`private_dot_ssh/private_config.tmpl` with `//./pipe/openssh-ssh-agent` on Windows, `${SSH_AUTH_SOCK}` on Linux), and `~/.config/git/allowed_signers`. Existing files with differing content are backed up by chezmoi; `~/.ssh/known_hosts` is left untouched.

3. Verify:

   ```powershell
   chezmoi status                          # should be clean
   chezmoi diff                            # should be empty
   git config --global --list --show-origin
   ssh-add -L                          # should list Bitwarden keys
   ssh -G github.com | Select-String identityagent  # //./pipe/openssh-ssh-agent
   ssh -T git@github.com               # approve in Bitwarden → "Hi Delnegend! ..."
   git ls-remote git@github.com:Delnegend/dotfiles.git  # should print HEAD
   ```

Daily use:

```powershell
chezmoi status          # what would change
chezmoi diff            # detailed diff
chezmoi apply -v        # apply
chezmoi edit ~/.gitconfig  # edit tracked file (writes back to dot_gitconfig.tmpl)
chezmoi add ~/.config/newapp/config  # add new file to repo
```

## Layout

```
~/.config/chezmoi/chezmoi.toml   # chezmoi config: sourceDir = ~/dotfiles

# Files (dot_ → ~/., private_ → 0600/0700, .tmpl → Go template)
dot_gitconfig.tmpl            # → ~/.gitconfig (OS-conditional: Windows gh.exe vs Linux brew gh)
private_dot_ssh/              # → ~/.ssh/ (0700)
  private_config.tmpl         #   unified SSH config (core + github + git.delnegend, IdentityAgent per OS)
  core@homelab.pub, delnegend@*.pub  #   public keys
dot_config/
  private_git/allowed_signers # → ~/.config/git/allowed_signers
  zed/settings.json + themes/ # → ~/.config/zed/
  opencode/opencode.jsonc     # → ~/.config/opencode/opencode.jsonc
  fontconfig/fonts.conf       # → ~/.config/fontconfig/fonts.conf (Linux, harmless on Windows)
  kdeglobals                  # → ~/.config/kdeglobals
  environment.d/              # → ~/.config/environment.d/ (kde-dark.conf, per-host ssh.conf.tmpl)
  systemd/user/*              # → ~/.config/systemd/user/ (Linux)
dot_bashrc_custom             # → ~/.bashrc_custom (sourced from ~/.bashrc, per-host case)
dot_Brewfile                  # → ~/Brewfile (Linux)
dot_agents/                   # → ~/.agents (skills)
dot_justfile                  # → ~/.justfile (general-purpose recipes + brew-dump + zed-theme-*)
dot_var/app/...               # → ~/.var/app/... (Flatpak mpv/easyeffects, Linux)

# Setup scripts (Linux-gated via {{ if eq .chezmoi.os "linux" }})
run_once_10-bootstrap.sh.tmpl # Homebrew + base packages + ~/.bashrc wiring
run_onchange_20-fonts.sh.tmpl # Iosevka + Noto Color Emoji + fc-cache
run_onchange_30-systemd.sh.tmpl # daemon-reload + enable units
run_onchange_40-kde.sh.tmpl   # flatpak overrides for BreezeDark
run_onchange_50-udev.sh.tmpl  # 99-disable-ncq-s4510.rules → /etc/udev (sudo)

# Repo-only (ignored via .chezmoiignore, never applied)
docs/  sync-zed-vscode-theme.py  README.md  AGENTS.md
```
