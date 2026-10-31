# Secrets

Secrets never live in this repo — each machine carries its own secret files.

- **MemPalace token (omp.sh and OpenCode):** set `MEMPALACE_MCP_HTTP_TOKEN=<token>`
  in `~/.omp/agent/.env` and restrict it with `chmod 600 ~/.omp/agent/.env`.
  Obtain the token securely from the homelab's SOPS-encrypted
  `layers/4-workloads/apps/mempalace/secrets.enc.yaml`; do not commit it.
  Both agents connect to `https://mempalace.delnegend.com/mcp` over Tailscale.
  `omp` loads the file at startup; `~/.bashrc_custom` exports it for OpenCode.
  Set `X-MemPalace-Wing` in each client's MemPalace server settings to select
  the wing used for recall and explicit saves; the header is not access control.
  Coding agents save only selected facts explicitly; they do not automatically
  save whole conversations. Never save credentials or other secrets.
- Guards: `.gitignore` excludes `.env`/`private_.env`; `.chezmoiignore` prevents
  `chezmoi apply` from overwriting `~/.omp/agent/.env`.
- New hosts: after `chezmoi apply`, add the token to that local file and start a
  new shell before starting OpenCode. Restart an existing OpenCode background
  service from that shell so it inherits the token. Tailscale must be connected.
