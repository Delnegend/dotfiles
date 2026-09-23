# dotfiles

## Bootstrap (chezmoi)

> **Managed with [chezmoi](https://www.chezmoi.io/)** — the repo lives at the default source directory `~/.local/share/chezmoi` (no `sourceDir` override needed). `dot_*`/`private_*` map to `$HOME`, `.tmpl` files render per-OS, `run_*` scripts handle setup. The repo is public.

### Prerequisites

- **chezmoi** `>=2.40` — install via the one-liner below if not yet present
- **Git** (+ OpenSSH on Windows)

### Linux

Ensure SSH agent forwarding is active (`ssh -A`) or your SSH key is added (`ssh-add`):

If chezmoi is not yet installed, bootstrap with:
```bash
sh -c "$(curl -fsLS https://get.chezmoi.io)" -- -b "$HOME/.local/bin" init --apply Delnegend
```

The `-b "$HOME/.local/bin"` is required: the installer's default `bin/` is relative to the current directory, so running the one-liner from e.g. `/workspaces/<project>` would install chezmoi there instead of under `$HOME`. `~/.local/bin` is on `PATH` by default on Debian/Ubuntu devcontainers.

Otherwise:
```bash
chezmoi init --apply Delnegend
# clones to ~/.local/share/chezmoi and applies;
# run_once/run_onchange scripts handle Homebrew, fonts, systemd, flatpak, udev automatically
```

For a new machine, add a `case` branch in `dot_bashrc_custom` matching `$(hostname -s)` _or_ extend `dot_config/environment.d/ssh.conf.tmpl`.

### Windows

1. Install:
    ```powershell
    winget install Git.Git twpayne.chezmoi -e
    ```

2. Clone and apply:
    ```powershell
    chezmoi init --apply Delnegend
    ```

3. Verify:
    ```powershell
    chezmoi status            # should be clean
    chezmoi diff              # should be empty
    ssh -T github.com         # should print "Hi Delnegend! ..."
    ```

Daily use:

```powershell
chezmoi status          # what would change
chezmoi diff            # detailed diff
chezmoi apply -v        # apply
chezmoi edit ~/.gitconfig  # edit tracked file (writes back to dot_gitconfig.tmpl)
chezmoi add ~/.config/newapp/config  # add new file to repo
```

## Secrets

Secrets never live in this repo — each machine carries its own secret files.

- **Hindsight API key (oh-my-pi memory):** put `HINDSIGHT_API_TOKEN=<token>` in `~/.omp/agent/.env` (mode `600`). The managed config `dot_omp/private_agent/private_config.yml` only references it as `apiToken: ${HINDSIGHT_API_TOKEN}`; `omp` auto-loads the agent `.env` at startup (load order: process env → project `.env` → agent `.env` → `~/.omp/.env` → `~/.env`, only unset keys are filled).
- Guards: `.gitignore` excludes `.env`/`private_.env` from ever being committed; `.chezmoiignore` lists `.omp/agent/.env` so `chezmoi apply` cannot overwrite the local file.
- New hosts: `dotfiles-pull.timer` syncs only the repo — create `~/.omp/agent/.env` by hand after `chezmoi apply`, or Hindsight auth silently falls back to unset.

## Layout

```
~/.local/share/chezmoi/          # repo root = default chezmoi sourceDir (no config override)

# Files (dot_ → ~/., private_ → 0600/0700, .tmpl → Go template)
dot_gitconfig.tmpl            # → ~/.gitconfig (OS-conditional: Windows gh.exe vs Linux brew gh)
private_dot_ssh/              # → ~/.ssh/ (0700)
  private_config.tmpl         #   unified SSH config (core + github + git.delnegend)
  core@homelab.pub, delnegend@*.pub  #   public keys
dot_config/
  private_git/allowed_signers # → ~/.config/git/allowed_signers
  fontconfig/fonts.conf       # → ~/.config/fontconfig/fonts.conf (Linux)
  kdeglobals                  # → ~/.config/kdeglobals
  environment.d/              # → ~/.config/environment.d/ (kde-dark.conf, ssh.conf.tmpl)
  systemd/user/*              # → ~/.config/systemd/user/ (Linux)
dot_bashrc_custom             # → ~/.bashrc_custom (sourced from ~/.bashrc, per-host case)
dot_Brewfile                  # → ~/Brewfile (Linux)
dot_agents/                   # → ~/.agents (skills)
dot_omp/private_agent/        # → ~/.omp/agent/ (0700)
  private_config.yml          #   oh-my-pi config (secrets via ${ENV} indirection)
  mcp.json.tmpl               #   per-host MCP servers (bazzite: mikrotik, memory)
dot_justfile                  # → ~/.justfile (general-purpose recipes + brew-dump)
dot_var/app/...               # → ~/.var/app/... (Flatpak mpv/easyeffects, Linux)

# Setup scripts (Linux-gated via {{ if eq .chezmoi.os "linux" }})
run_once_10-bootstrap.sh.tmpl # Homebrew + base packages + ~/.bashrc wiring
run_onchange_20-fonts.sh.tmpl # Iosevka + Noto Color Emoji + fc-cache
run_onchange_30-systemd.sh.tmpl # daemon-reload + enable units (scoped by ConditionPathExists/ConditionHost in units)
run_onchange_40-kde.sh.tmpl   # flatpak overrides for BreezeDark
run_onchange_50-udev.sh.tmpl  # 99-disable-ncq-s4510.rules → /etc/udev (sudo)

# Repo-only (ignored via .chezmoiignore, never applied)
README.md  AGENTS.md  LICENSE
```

## License

MIT — see [LICENSE](LICENSE).
