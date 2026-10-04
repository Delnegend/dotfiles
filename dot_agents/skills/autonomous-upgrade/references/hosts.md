# Hosts: GitHub, Forgejo, and the twin pattern

**Never assume a repository is on github.com.** The host changes every path,
runner label, token, and CLI in this skill. Determine it first.

```bash
git remote -v                                  # authoritative host
git config --get remote.origin.url
ls -d .github/workflows .forgejo/workflows 2>/dev/null   # existing CI location
```

## Classify

| Signal | Host | Action location |
|---|---|---|
| `origin` is `github.com` | GitHub | `.github/workflows/` |
| `origin` is self-hosted (e.g. `git.<domain>`) | Forgejo | `.forgejo/workflows/` |
| Self-hosted origin **and** a GitHub mirror the owner names | Forgejo is the source of truth | `.forgejo/workflows/`; artifact builds dispatch to the GitHub twin |

State the finding to the owner before proceeding: which host, where workflows
go, and whether a twin is involved.

## GitHub vs Forgejo

Forgejo Actions is Actions-compatible — same `on:` / `jobs:` / `steps:` syntax.
The differences that actually bite:

| | GitHub | Forgejo (self-hosted) |
|---|---|---|
| Workflow dir | `.github/workflows/` | `.forgejo/workflows/` |
| Slim runner | `ubuntu-slim` | whatever self-hosted label exists (e.g. `alpine`) |
| Full runner | `ubuntu-latest` | owner's equivalent |
| PR CLI | `gh pr ...` | `fj pr ...` (forgejo-contrib CLI) |
| Settings UI | Settings → Actions | Settings → Actions (different labels) |
| PR/secret permission | "Allow GitHub Actions to create and approve pull requests" | "Allow pull requests and security alerts" |
| Dependabot | `.github/dependabot.yml` (`github-actions` only) | none (not supported) |

Never write `ubuntu-slim` into a Forgejo workflow unless that label is actually
registered on the instance — the job will sit queued forever.

`actions/checkout` and `actions/setup-*` may need to be swapped for
`<forgejo-host>/actions/checkout@vN` if the runner cannot reach github.com.

On GitHub, `.github/dependabot.yml` is maintained solely for
`package-ecosystem: "github-actions"` to bump workflow action versions.
Dependabot is never configured for code dependencies.

### Minimal runner images have no Node

A lean self-hosted runner label (`alpine`, and many small container images)
typically ships only `gh`/`jq`/`git`/`curl`/`bash`. **Every `using: node24`
or `using: node20` action fails there** — including `actions/checkout`,
`actions/setup-*`, and Forgejo's own mirror at
`data.forgejo.org/actions/checkout`. The job dies at the first step with a
missing-runtime error, which reads like a network problem but is not.

Two fixes, in order of preference:

1. Point `uses:` at a **shell-only** composite action (plain `bash` + `git`).
   One is often already maintained in a shared actions repo.
2. Run the job on a runner that has Node, and keep the shell-only action
   anyway to drop the clone from github.com entirely.

Before writing any Forgejo workflow, check what the runner image actually has:
`docker run --rm <runner-image> sh -c 'command -v node git jq'`.

### `persist_credentials: true` when the job pushes

A workflow that commits or pushes must pass `persist_credentials: true` to
checkout. Without it the token is stripped after checkout and the push fails
with an authentication error that looks like a permissions problem.

```yaml
      - name: Checkout source
        uses: <host>/actions/checkout@v2
        with:
          token: ${{ github.token }}
          persist_credentials: true
          fetch-depth: 0        # semver-action needs full history
```

### The Forgejo CLI is `fj`

`fj` is the CLI from `forgejo-contrib/forgejo-cli` — the `gh`-equivalent for
Forgejo. Install it on the runner (prebuilt binaries for Linux x86_64/aarch64
and Windows are on the releases tab) or via `cargo install forgejo-cli`.

Two facts that shape how you write Forgejo steps:

1. **`fj` reads no token from the environment.** It stores credentials in its
   own keys file, so CI must seed it first with
   `fj auth add-token "$TOKEN" -H <forgejo-host>` (the token may also be piped
   on stdin). Store the token as a Forgejo secret; never commit it.
2. **`fj pr merge` has no `--auto` flag.** Methods are
   `merge`, `rebase`, `rebase-merge`, `squash`, `manual`; there is no
   auto-merge-on-green equivalent of `gh pr merge --auto`. For a Forgejo
   project, either set auto-merge in the instance UI, or use
   `fj pr merge --method rebase --delete` gated behind a
   `fj pr status` CI check in the same job. Do not write a `--auto` flag that
   does not exist.

Install and version-check in the workflow with `fj version` (currently v0.6.x)
so a silent upgrade cannot change the CLI surface under you.

`fj` also needs the host on every call (`-H <forgejo-host>`); it has no
repository auto-detection that survives a detached CI checkout.

## Twin-repository pattern

Some projects are private on the internal Forgejo but published as a public
GitHub mirror. The **twin is where release artifacts are built and published**
(GitHub Releases, GHCR), while the Forgejo repo owns CI triggering and the tag.

- Forgejo repo → computes the version, gates on CI, commits, tags, pushes.
- Then dispatches the twin's build workflow and waits for it.
- Wire the two with a Forgejo workflow dispatching a `repository_dispatch`
 event, using a fine-grained PAT stored as a **Forgejo secret**. Never commit
 the PAT.
- Ask the owner which side owns which step. Do not infer it from the remote
 alone — a mirror existing does not mean it builds artifacts.

### `repository_dispatch`, not `workflow_dispatch`

Dispatch across repos with a `repository_dispatch` event whose
`event_type` is the twin's **workflow name**. Two traps:

- **Set `event:` explicitly.** `GITHUB_WORKFLOW` is a read-only default
 variable and a step-level `env:` cannot override it. Pass the name as a
 workflow `input`.
- **`workflow_dispatch` cannot target another repository.** Use
 `repository_dispatch` for the twin, and reserve `workflow_dispatch` for
 humans triggering a workflow on its own repo.

Always pass `ref:` for a release dispatch so the twin builds the tag it was
asked to, not whatever `main` happens to be. To run a test build against a commit
without publishing a release, dispatch with `target: "commit"` (e.g. in the
payload or inputs) so the twin uploads build artifacts to the Actions run and
skips publishing. Set `timeout-minutes` on every job that blocks on another
runner — the default is 6 hours and a hung twin dispatch holds the Forgejo runner
for all of it.

### Ordering: tag and commit atomically

Push the commit and the tag in **one** `git push`:

```bash
git push origin HEAD:main "refs/tags/${NEXT_TAG}"
```

Two pushes can land the commit without its tag (or vice versa) if the second
fails, leaving `main` permanently ahead of the last tag and the next version
calculation wrong. Guard both failure modes first:

```bash
git diff --staged --quiet && { echo "::error::bump produced no change"; exit 1; }
git rev-parse -q --verify "refs/tags/${NEXT_TAG}" >/dev/null \
  && { echo "::error::tag ${NEXT_TAG} already exists"; exit 1; }
```

### `pull_request` + a twin = a secret-exfiltration path

A `pull_request` trigger runs with **no secrets** on the fork's code, which is
safe on GitHub. Dispatching that event to a twin **does** fan untrusted code
into a secret-bearing run on the other side, where the twin's own trigger rules
do apply. On a private repo where forks are unlikely this is accepted; if the
repo is public, gate the dispatch on `github.event.pull_request.head.repo.full_name
== github.repository` or drop the `pull_request` trigger. Record the decision —
it is a security tradeoff, not an oversight.

### Repair path after a partial release

When a tag exists on Forgejo but the twin release never completed, **re-run the
twin's release workflow with the existing tag. Do not re-run the version bump** —
a second bump creates a new tag for a version that was already released. Make
the release workflow accept an optional tag input (defaulting to the newest tag)
so this repair is a button rather than a code change.

**Name no specific account.** The GitHub account hosting a twin is the owner's
private arrangement and must never appear in committed workflow files, generated
docs, or summaries. Refer to it as "the GitHub twin" and let the owner supply
`owner/repo` at apply time.

## Branch protection

On **GitHub**, with `gh` (needs repo admin):

```bash
# Enable auto-merge and rebase-only merges
gh repo edit <owner>/<repo> \
  --enable-auto-merge \
  --enable-rebase-merge \
  --delete-branch-on-merge

# Apply branch protection: strict 'Check (just check)' gate and linear history
gh api -X PUT "repos/<owner>/<repo>/branches/main/protection" \
  -H "Accept: application/vnd.github+json" \
  --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Check (just check)"
    ]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "allow_auto_merge": true
}
EOF
```

On **Forgejo**, there is no `gh` equivalent. Use **Settings → Branches → Branch
protection rules**, or:

```
POST /api/v1/repos/{owner}/{repo}/branch_protections
```

The context name must match the job's `name:` exactly — `"Check (just check)"`.

**Settings check.** On GitHub, Settings → Actions → General → Workflow
permissions must have *"Allow GitHub Actions to create and approve pull
requests"* checked. On Forgejo, Settings → Actions → General → *"Allow pull
requests and security alerts"* must be enabled, or the `fj pr create` in the
upgrade job fails.
