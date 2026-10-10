# Setup

Managed with [chezmoi](https://www.chezmoi.io/). The repo is the default
chezmoi source at `~/.local/share/chezmoi` (no `sourceDir` override):
`dot_*`/`private_*` map to `$HOME`, `.tmpl` files render per-OS, `run_*`
scripts handle setup. It is public.

## Prerequisites

- **chezmoi** `>=2.40` — install via the one-liner below if not yet present.
- **Git** (+ OpenSSH on Windows).

## Linux

Ensure SSH agent forwarding is active (`ssh -A`) or your SSH key is added
(`ssh-add`):

If chezmoi is not yet installed, bootstrap with:

```bash
sh -c "$(curl -fsLS https://get.chezmoi.io)" -- -b "$HOME/.local/bin" init --apply Delnegend
```

The `-b "$HOME/.local/bin"` is required: the installer's default `bin/` is
relative to the current directory, so running the one-liner from e.g.
`/workspaces/<project>` would install chezmoi there instead of under `$HOME`.
`~/.local/bin` is on `PATH` by default on Debian/Ubuntu devcontainers.

Otherwise:

```bash
chezmoi init --apply Delnegend
# clones to ~/.local/share/chezmoi and applies;
# run_once/run_onchange scripts handle Homebrew, fonts, systemd, flatpak, udev automatically
```

For a new machine, add a `case` branch in `dot_bashrc_custom` matching
`$(hostname -s)` *or* extend `dot_config/environment.d/ssh.conf.tmpl`.

## Windows

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

Linux-only files (systemd units, fontconfig, Flatpak `dot_var/`,
`dot_Brewfile`, `dot_bashrc_custom`) also land on Windows — harmless by
design.

## Daily use

```powershell
chezmoi status          # what would change
chezmoi diff            # detailed diff
chezmoi apply -v        # apply
chezmoi edit ~/.gitconfig  # edit tracked file (writes back to dot_gitconfig.tmpl)
chezmoi add ~/.config/newapp/config  # add new file to repo
```
