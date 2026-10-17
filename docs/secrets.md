# Secrets

Secrets never live in this repo — each machine carries its own secret files.

- **Hindsight API key (oh-my-pi and OpenCode memory):** put `HINDSIGHT_API_TOKEN=<token>` in
  `~/.omp/agent/.env` (mode `600`).
  - `omp` auto-loads `~/.omp/agent/.env` at startup (load order: process env → project `.env` → agent `.env` → `~/.omp/.env` → `~/.env`, only unset keys are filled) and maps it via `apiToken: "${HINDSIGHT_API_TOKEN}"`.
  - `~/.bashrc_custom` exports `~/.omp/agent/.env` into the shell environment so OpenCode's Hindsight plugin (`@vectorize-io/hindsight-coding-agents`) inherits `HINDSIGHT_API_TOKEN`.
  - Both tools connect to `https://hindsight.delnegend.com` and share the static `"coding"` memory bank configured in `~/.hindsight/coding-agent.json` and `~/.omp/agent/config.yml`.
- Guards: `.gitignore` excludes `.env`/`private_.env` from ever being
  committed; `.chezmoiignore` lists `.omp/agent/.env` so `chezmoi apply`
  cannot overwrite the local file.
- New hosts: `dotfiles-pull.timer` syncs only the repo — create
  `~/.omp/agent/.env` by hand after `chezmoi apply`, or Hindsight auth
  silently falls back to unset.
