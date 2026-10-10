# Secrets

Secrets never live in this repo — each machine carries its own secret files.

- **Hindsight API key (oh-my-pi memory):** put `HINDSIGHT_API_TOKEN=<token>` in
  `~/.omp/agent/.env` (mode `600`). The managed config
  `dot_omp/private_agent/private_config.yml` only references it as
  `apiToken: ${HINDSIGHT_API_TOKEN}`; `omp` auto-loads the agent `.env` at
  startup (load order: process env → project `.env` → agent `.env` →
  `~/.omp/.env` → `~/.env`, only unset keys are filled).
- Guards: `.gitignore` excludes `.env`/`private_.env` from ever being
  committed; `.chezmoiignore` lists `.omp/agent/.env` so `chezmoi apply`
  cannot overwrite the local file.
- New hosts: `dotfiles-pull.timer` syncs only the repo — create
  `~/.omp/agent/.env` by hand after `chezmoi apply`, or Hindsight auth
  silently falls back to unset.
