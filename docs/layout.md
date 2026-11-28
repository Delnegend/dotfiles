# Layout

```
~/.local/share/chezmoi/          # repo root = default chezmoi sourceDir (no config override)

# Files (dot_ → ~/., private_ → 0600/0700, .tmpl → Go template)
dot_gitconfig.tmpl            # → ~/.gitconfig (OS-conditional: Windows gh.exe vs Linux brew gh)
private_dot_ssh/              # → ~/.ssh/ (0700)
  private_config.tmpl         #   unified SSH config (homelab + github + git.delnegend + bazzite)
  core@homelab.pub, delnegend@*.pub, twin@github.pub  # public keys
dot_config/
  private_git/allowed_signers # → ~/.config/git/allowed_signers
  zed/                      # → ~/.config/zed/ (bazzite + Windows only)
    settings.base.json        # static settings (ignored as a home target)
    modify_private_settings.json # → ~/.config/zed/settings.json (0600; keeps ACP model/effort/mode from the live file)
    themes/                   # → ~/.config/zed/themes/
  fontconfig/fonts.conf       # → ~/.config/fontconfig/fonts.conf (bazzite-only)
  private_kdeglobals          # → ~/.config/kdeglobals (private 0600, bazzite-only)
  private_kwinrc              # → ~/.config/kwinrc (private 0600, bazzite-only)
  private_plasma-org.kde.plasma.desktop-appletsrc  # → panel/widgets/wallpaper (private 0600, bazzite-only)
  private_plasmashellrc       # → ~/.config/plasmashellrc (private 0600, bazzite-only)
  private_konsolerc           # → ~/.config/konsolerc (private 0600, bazzite-only)
  private_gtk-3.0/private_settings.ini, private_gtk-4.0/private_settings.ini  # → GTK theme (private 0600, bazzite-only)
  private_kglobalshortcutsrc  # → keyboard shortcuts (private 0600, bazzite-only)
  environment.d/              # → ~/.config/environment.d/ (kde-dark.conf on bazzite, ssh.conf.tmpl on Linux)
  systemd/user/*              # → ~/.config/systemd/user/ (Linux)
  opencode/opencode.json.tmpl # → ~/.config/opencode/opencode.json (providers, MCP servers + MemPalace)
  opencode/AGENTS.md.tmpl     # → ~/.config/opencode/AGENTS.md (shared agent reply guidance)
  opencode/private_cli.json   # → ~/.config/opencode/cli.json (0600, TUI theme, diffs, sidebar, verbosity)
  opencode/mempalace/index.ts # → ~/.config/opencode/mempalace/ (automatic MemPalace recall plugin)
  opencode/models-discovery/index.ts # → ~/.config/opencode/models-discovery/ (discovers compatible providers)
  mempalace/mempalace-recall.ts # → ~/.config/mempalace/ (shared coding-wing recall hook for Claude Code and agy)
dot_bashrc_custom.tmpl        # → ~/.bashrc_custom (sourced from ~/.bashrc, per-host template)
dot_tmux.conf                 # → ~/.tmux.conf (Linux; tmux installed via brew bootstrap)
dot_claude/                   # → ~/.claude/ (shared guidance, MemPalace and Zero G key helper)
dot_agents/                   # → ~/.agents (skills)
dot_gemini/AGENTS.md.tmpl     # → ~/.gemini/AGENTS.md (shared agent reply guidance)
dot_gemini/antigravity-cli/   # → ~/.gemini/antigravity-cli/
  modify_private_settings.json #   → ~/.gemini/antigravity-cli/settings.json (0600; ensures mcp(mempalace/*) allow rule, preserves local settings)
dot_gemini/config/            # → ~/.gemini/config/ (Antigravity shared config and hooks: Zero G observation via zero-g-agy-integration on Linux, and MemPalace)
  modify_private_config.json  #   → ~/.gemini/config/config.json (0600; ensures mcp(mempalace/*) allow rule in shared/ACP scope, preserves local settings)
  mcp_config.json.tmpl        #   → ~/.gemini/config/mcp_config.json (invokes Bun directly on the rendered bridge path)
  hooks.json.tmpl             #   → ~/.gemini/config/hooks.json (renders MemPalace recall path; gates Linux-only Zero G observation hook)
  mempalace-bridge.ts         #   Bun MCP bridge reading the token from env or ~/.config/ai-agents/secrets.env
                              #   recall hook lives in ~/.config/mempalace/, shared with Claude Code
dot_local/share/              # → ~/.local/share/ (bazzite-only Steam proxy & WinBox launchers + icon)
scripts/executable_l4d2-download.py # → ~/scripts/l4d2-download.py (bazzite-only; Steam Workshop maps into local L4D2 addons)
scripts/executable_ssd-health.py # → ~/scripts/ssd-health.py (bazzite-only; SMART health report, run by `just ssd-health`)
scripts/executable_disk-cleanup.sh # → ~/scripts/disk-cleanup.sh (bazzite-only; weekly cleanup run by systemd/user/disk-cleanup.timer)
dot_omp/private_agent/        # → ~/.omp/agent/ (0700)
  config.base.yml             #   static oh-my-pi config; modelRoles come from the live file
  modify_private_config.yml   #   → ~/.omp/agent/config.yml (0600; preserves modelRoles from the live file)
  models.yml                  #   custom OpenAI-compatible providers (Zero G, Anthropic pass-through)
  APPEND_SYSTEM.md.tmpl       #   shared reply guidance appended to the built-in prompt
  mcp.json.tmpl               #   MCP servers (integrated-browser-mcp, playwright, mikrotik, MemPalace)
  extensions/mempalace.ts     #   automatic MemPalace recall extension
dot_justfile.tmpl             # → ~/.justfile (bazzite-only recipes + zed-theme-*)
dot_var/app/...               # → ~/.var/app/... (Flatpak mpv/easyeffects, bazzite-only)
# Setup scripts (Linux-gated via {{ if eq .chezmoi.os "linux" }})
run_once_10-bootstrap.sh.tmpl # Homebrew + base packages + ~/.bashrc wiring
run_once_20-zed-symlink.ps1.tmpl # Windows: junction %APPDATA%/Zed → ~/.config/zed
run_onchange_20-fonts.sh.tmpl # Iosevka + JetBrains Mono Nerd Fonts + Noto Color Emoji + fc-cache
run_onchange_30-systemd.sh.tmpl # daemon-reload + enable units (scoped by ConditionPathExists/ConditionHost in units)
run_onchange_40-kde.sh.tmpl   # flatpak overrides for BreezeDark
run_onchange_50-udev.sh.tmpl  # 99-disable-ncq-s4510.rules → /etc/udev (sudo)
run_onchange_60-modprobe.sh.tmpl # hid_apple.conf → /etc/modprobe.d (sudo)
run_onchange_70-journald.sh.tmpl # 50-retention.conf (7-day journal) → /etc/systemd/journald.conf.d (sudo)
.chezmoitemplates/agent-guidance.md # shared source for omp, OpenCode, agy and Claude Code guidance

# Repo-only (ignored via .chezmoiignore, never applied)
README.md  AGENTS.md  LICENSE  .gitignore  docs/  scripts/zero-g-discovery.test.ts  sync-zed-vscode-theme.py
```
