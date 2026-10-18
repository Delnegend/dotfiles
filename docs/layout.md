# Layout

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
  kdeglobals                  # → ~/.config/kdeglobals (private 0600, bazzite-only)
  kwinrc                      # → ~/.config/kwinrc (private 0600, bazzite-only)
  plasma-org.kde.plasma.desktop-appletsrc  # → panel/widgets/wallpaper (private 0600, bazzite-only)
  plasmashellrc               # → ~/.config/plasmashellrc (private 0600, bazzite-only)
  konsolerc                   # → ~/.config/konsolerc (private 0600, bazzite-only)
  gtk-3.0/settings.ini, gtk-4.0/settings.ini  # → GTK theme (private 0600, bazzite-only)
  kglobalshortcutsrc          # → keyboard shortcuts (private 0600, bazzite-only)
  environment.d/              # → ~/.config/environment.d/ (kde-dark.conf, ssh.conf.tmpl)
  systemd/user/*              # → ~/.config/systemd/user/ (Linux)
  opencode/opencode.json.tmpl # → ~/.config/opencode/opencode.json (MCP servers + Hindsight plugin)
dot_bashrc_custom.tmpl        # → ~/.bashrc_custom (sourced from ~/.bashrc, per-host template)
dot_tmux.conf                 # → ~/.tmux.conf (Linux; tmux installed via brew bootstrap)
dot_Brewfile                  # → ~/Brewfile (Linux)
dot_agents/                   # → ~/.agents (skills)
dot_omp/private_agent/        # → ~/.omp/agent/ (0700)
  private_config.yml          #   oh-my-pi config (secrets via ${ENV} indirection)
  APPEND_SYSTEM.md             #   standing reply rules (plain language, conclusion first); appends to the built-in prompt
  mcp.json.tmpl               #   MCP servers (playwright, mikrotik)
dot_hindsight/                # → ~/.hindsight/
  coding-agent.json           #   Hindsight server config (self-hosted endpoint + coding bank)
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
