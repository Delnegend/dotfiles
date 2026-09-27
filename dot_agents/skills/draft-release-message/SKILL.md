---
name: draft-release-message
description: Draft a plain-markdown release message from the commits between the previous release tag and the latest tag. Use after a release is tagged or when the user says draft-release-message.
---

# Draft Release Message

Write release notes for non-technical users: what the update does for them, not how it works.

## Trigger

The user invokes this skill with `/draft-release-message` (or `draft the release notes`, `write the changelog`, etc.). Run inside the project checkout — it needs `git` and the release tags.

## Workflow

1. **Sync** — `git pull --rebase` then `git fetch --tags --quiet`, so the local checkout includes the bump commit and current tags.
2. **Find the range** — two newest release tags: `git tag -l 'v[0-9]*.[0-9]*.[0-9]*' --sort=-v:refname | head -n2`. Range is `<previous>..<latest>` (the release is already tagged; HEAD may contain newer, unreleased work). If only one tag exists, use the full history up to it.
3. **List subjects** — `git log --pretty=format:%s <previous>..<latest>`. Drop `chore(release):` bumps, CI-only (`ci:`, `ci(...)`), and docs-only changes unless they affect users.
4. **Translate** — each remaining commit becomes one plain-language bullet: user outcome first. No file names, symbol names, flags, or protocol internals. Group under `## What's new` / `## Fixes` only as needed; skip empty groups.
5. **Keep it short** — 3–7 bullets max, one line each. No preamble, no footer, no links.

## Output

Plain markdown, nothing else:

```md
## What's new

- ...

## Fixes

- ...
```
