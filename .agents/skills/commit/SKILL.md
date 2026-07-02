---
name: commit
description: Stage files or selective line changes non-interactively based on a short description, write a detailed conventional commit message with backticked keywords, and commit them.
---

# Commit Skill

Use this skill when staging and committing a subset of changes from the working tree based on a user's description.

## Trigger

The user invokes this skill with `/commit` (or `lets do it`, `go ahead`, etc. in reply to your diff summary). Treat this as a direct instruction — proceed immediately without asking for confirmation.

## Workflow

The user invokes this skill in one of two ways. Branch accordingly:

### Path A — Commit already-staged changes

Use when the user says simply `/commit` or `/commit the current staged changes` (no description of what to include).

1. **Verify staged changes** — Run `git diff --cached` and `git status` to confirm the index is not empty and contains only intended changes.
2. **Skip to Generate Commit Message** — The staging is already done.
3. **Execute the commit.**

### Path B — Stage changes then commit

Use when the user says `/commit <description>` (e.g. `/commit changes related to adding XYZ`).

#### 1. Identify Target Changes
- Run `git diff` and `git status` to inspect all unstaged changes and untracked files.
- Match the user's short description with specific files or hunks in the diff.

#### 2. Stage Changes Non-Interactively
Do NOT use interactive commands like `git add -p` or `git add -i`. Instead, use the following non-interactive strategies:
- **Full File Staging:** If all changes in a file are related, stage it directly using `git add <file>`.
- **Selective Line/Hunk Staging:** If only some lines/hunks in a file are related:
  1. Create a backup of the modified file to a temporary path under `/tmp/opencode/` (e.g., `/tmp/opencode/backup_file`).
  2. Edit the workspace file to temporarily revert or exclude the unrelated changes.
  3. Run `git add <file>` to stage only the desired changes.
  4. Copy the backup file back to the workspace to restore the remaining unstaged changes.

### 3. Generate Commit Message
Write a structured commit message in the Conventional Commits style (`feat(...)`, `refactor(...)`, `fix(...)`, `docs(...)`, `chore(...)`, `style(...)`).

**General Backticking Rule:**
Rigorously apply backticks (\`) around all code-like elements, including:
- **Filenames, paths, and folders:** e.g., \`backup-fs.sh\`, \`Dockerfile\`, \`layers/5-workloads/\`, \`ingress.tpl.yaml\`
- **CLI tools and commands:** e.g., \`kubectl\`, \`rclone\`, \`tar\`, \`zstd\`, \`age\`, \`rclone delete\`
- **Configuration fields and code keywords:** e.g., \`authelia-forward-auth\`, \`generic_oauth\`, \`ClusterIP\`, \`redirectRegex\`, \`storageClassName\`
- **App and workload names:** e.g., \`pocket-id\`, \`tinyauth\`, \`grafana\`, \`headlamp\`, \`memos\`

Format:
```
<type>(<scope>): <short description>

- <detailed bullet point 1>
- <detailed bullet point 2>
```

### 4. Execute the Commit
- Verify `git status` to ensure only the intended files are staged.
- Run `git commit -m "<message>"` to commit the staged changes.

### 5. Clean Up Temporary Files
- Remove `/tmp/opencode/` directory and all its contents: `rm -rf /tmp/opencode/`
- This prevents stale backup files from leaking into future sessions.

### 6. Keep Responses Concise and Detailed
- Keep response explanations and status updates concise but precise.
- Do not hide the changes: list the exact files staged/committed and summarize key modifications clearly without omitting details.
- Avoid unnecessary conversational filler, preambles, and postambles.
