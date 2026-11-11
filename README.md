<div align="center">

# dotfiles

**One command restores this whole desk: shell, editor, tools, and fonts, on a fresh Linux box or a Windows machine, exactly as it is here.**

</div>

---

## Quick Start

```bash
# 1. On a new machine, name it
#    add a host branch in `dot_bashrc_custom.tmpl` matching `{{ .chezmoi.hostname }}`

# 2. Bootstrap
sh -c "$(curl -fsLS https://get.chezmoi.io)" -- -b "$HOME/.local/bin" init --apply Delnegend

# 3. Verify
chezmoi status    # what would change; expect clean
```

## Highlights

- **One source of truth for every setting**: shell, git, tmux, KDE, fonts, systemd units, udev rules, editor and agent configs, all as templates that render per OS.
- **Secrets pull their weight**: SSH keys, signing keys and agent tokens stay on the machine (nothing sensitive is ever committed).
- **One-shot setup, quiet maintenance**: `run_once_*` scripts set the machine up; `run_onchange_*` scripts re-run only when their inputs change.
- **Machine-aware by default**: `wsl`, `homelab` (`core`), `bazzite` and new hosts each get their own branch instead of commented-out blocks.
- **Steam downloads on Bazzite**: the Homebrew `dpi-proxy` service listens on `127.0.0.1:18118` for Steam's web and download connections.
- **OpenCode model discovery**: the local Zero G plugin fetches model limits, supported input types and thinking levels at startup using `ZERO_G_TOKEN`. Where Zero G omits details, it assumes text input and output, tool support, a 200,000-token context window and up to 32,000 output tokens.

## Documentation

- **[Setup](docs/setup.md)**: prerequisites, bootstrap per OS, daily use, adding files.
- **[Secrets](docs/secrets.md)**: the agent token handoff and the guards that keep it local.
- **[Layout](docs/layout.md)**: every managed file, its destination, and the setup scripts.
- **[Sunshine](docs/sunshine.md)**: game stream host setup, KMS capture, and session recovery.

## License

[MIT](LICENSE)
