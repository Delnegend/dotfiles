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
| PR creation | `gh pr create` | Native AGit (`git push origin HEAD:refs/for/<branch>`) |
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

### PR creation on Forgejo: Native AGit (`refs/for/<branch>`)

Rather than installing CLI tools (`tea`/`fj`) and managing tokens on the runner,
Forgejo natively supports the **AGit protocol**. Pushing to the virtual namespace
`refs/for/<target-branch>` commands Forgejo to create or update a Pull Request
directly over Git transport:

```bash
git push origin HEAD:refs/for/main \
  -o topic="deps/automatic" \
  -o force-push=true \
  -o title="chore(deps): upgrade dependencies" \
  -o description="Automated daily upgrade."
```

Why AGit is the standard for Forgejo:
1. **Zero runner dependencies:** Plain `git` is the only tool needed. Works on
   any minimal container image (Alpine, scratch-based) with no extra packages.
2. **Zero token / permission bugs:** Runs over the standard Git credentials already
   configured by checkout (`persist_credentials: true`). Bypasses Forgejo issue
   #13739 where the REST API rejects automatic tokens on private/internal repos.
3. **Automatic updates:** Pushing again with the same `-o topic="..."` and
   `-o force-push=true` updates the existing open PR cleanly instead of creating duplicates.

### Optional: The Forgejo CLI (`fj`)

`fj` (`forgejo-contrib/forgejo-cli`) is only needed if a workflow explicitly
requires CLI operations (like querying status or manual reviews):
- Credentials must be seeded first via `fj auth add-token "${{ github.token }}" -H <host>`.
- `fj pr merge` has no `--auto` flag (use native auto-merge settings in the Forgejo UI, or gate with `fj pr status --wait`).

## Twin-repository pattern

Some projects are private on Forgejo but run CI on a public GitHub mirror
(free runners). The Forgejo repo is the sole source of truth; the twin is
regenerated from it on every dispatch.

### GitHub needs only a repo and a token

1. **Create an empty repo** on GitHub with the same name (only the owner
   differs). The first dispatch populates `.github/` from the source.
2. **Create one fine-grained PAT** (Contents + Actions read/write), store it
   as `GH_ACTIONS` on the Forgejo repo. Never commit the PAT.

Nothing else is ever done on GitHub: no file edits, no branches, no tags. A
wrong-looking twin is fixed with a source-repo change plus a dispatch.

- The source repo carries `.forgejo/workflows/` (triggers) and
  `.github/workflows/` (the twin's workflows, authored here; only `.github/`
  is synced, `LICENSE`/`README` are kept; repos without `.github/` skip).
- The twin builds release artifacts (GitHub Releases, GHCR) and runs the
  Docker-based security scans (Gitleaks, Semgrep, Trivy, OSV-Scanner); Forgejo
  owns triggering and the tag. Forgejo prefers `.forgejo/workflows/`, so the
  twin's workflows never run there.
- Dispatch via `repository_dispatch` (PAT stored as above). Ask the owner
  which side owns which step; a mirror existing does not mean it builds.
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

When a tag exists on Forgejo but the twin release never completed, **re-run
`release` with `target: tag` and the existing tag. Do not run `target: new-tag`** —
that would create a second tag for a version that was already released.

### Observe the twin with `gh` — read-only, never write

The twin is inspected from the Forgejo-side checkout with the `gh` CLI (any
read token works; the `GH_ACTIONS` PAT is fine). These are the only twin-side
operations the skill ever performs:

```bash
gh run list --repo <twin> --limit 5                      # recent runs + verdicts
gh run view <run-id> --repo <twin>                        # per-job pass/fail
gh run view --repo <twin> --job <job-id> --log            # failing step output
gh run rerun --failed --repo <twin> <run-id>              # retry transient failures
```

`gh run rerun` is the single sanctioned write: it re-executes an existing run
without touching the twin's git state. Anything that would change the twin's
files, branches, or tags is done on Forgejo and synced over — never pushed
directly.

> Live reference: `github.com/Vessel9457/emsui-agent` — a working twin.
> Its `.github/workflows/` (authored in the Forgejo source's `.github/`,
> synced by the dispatch step) shows the scan-job layout, `fj_repo` wiring,
> and `nosemgrep`/SHA-pin conventions in production. Read it with `gh api
> repos/Vessel9457/emsui-agent/contents/.github/workflows --jq` or a shallow
> clone when grounding a new twin setup.

**Name no specific account in generated output.** The GitHub account hosting a twin is the owner's
private arrangement and must never appear in committed workflow files, generated
docs, or summaries. Refer to it as "the GitHub twin" and let the owner supply
`owner/repo` at apply time. (The curated reference above is skill content, not
generated output — it stays.)

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
  "allow_deletions": false
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
