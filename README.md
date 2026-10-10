<div align="center">

# dotfiles

**One command restores this whole desk — shell, editor, tools, and fonts — on a fresh Linux box or a Windows machine, exactly as it is here.**

</div>

---

## Quick Start

```bash
# 1. On a new machine, name it
#    add a `case` branch in `dot_bashrc_custom` matching `$(hostname -s)`

# 2. Bootstrap
sh -c "$(curl -fsLS https://get.chezmoi.io)" -- -b "$HOME/.local/bin" init --apply Delnegend

# 3. Verify
chezmoi status    # what would change — expect clean
```

## Highlights

- **One source of truth for every setting** — shell, git, tmux, KDE, fonts, systemd units, udev rules, editor and agent configs, all as templates that render per OS.
- **Secrets pull their weight** — SSH keys, signing keys and agent tokens stay on the machine (nothing sensitive is ever committed).
- **One-shot setup, quiet maintenance** — `run_once_*` scripts set the machine up; `run_onchange_*` scripts re-run only when their inputs change.
- **Machine-aware by default** — `wsl`, `homelab` (`core`), `bazzite` and new hosts each get their own branch instead of commented-out blocks.

## Documentation

- **[Setup](docs/setup.md)** — prerequisites, bootstrap per OS, daily use, adding files.
- **[Secrets](docs/secrets.md)** — the agent token handoff and the guards that keep it local.
- **[Layout](docs/layout.md)** — every managed file, its destination, and the setup scripts.

## License

[MIT](LICENSE)
