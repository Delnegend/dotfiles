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

## Layout

| File | Maps to | Purpose |
|---|---|---|
| `dot_bashrc_custom` | `~/.bashrc_custom` | Shell entry point; per-host branches on `$(hostname -s)` |
| `dot_gitconfig.tmpl` | `~/.gitconfig` | OS-conditional git config |
| `dot_tmux.conf` | `~/.tmux.conf` | Tmux + system clipboard (Linux) |
| `dot_config/` | `~/.config/` | git signers, fontconfig, KDE, environment, systemd units |
| `dot_agents/` | `~/.agents/` | Agent skills, including the ones that maintain this repo |
| `dot_omp/` | `~/.omp/` | Agent config and model roles |
| `private_dot_ssh/` | `~/.ssh/` (`0700`) | SSH client config and signing keys |
| `dot_Brewfile` | `~/Brewfile` | Package list, refreshed with `just brew-dump` + `chezmoi re-add` |
| `run_once_10-bootstrap.sh.tmpl` | once | Sources `~/.bashrc_custom` from `~/.bashrc` |
| `run_onchange_*.sh.tmpl` | on change | Fonts, systemd, KDE, udev |

System layout changes belong in `AGENTS.md` next to the commands (`chezmoi status` / `diff` / `apply -v`, `just --list`) that verify them.

## License

[MIT](LICENSE)
