---
name: push
description: "Use when: pushing code to GitHub, updating git, committing changes, PUSH. Stages all changes, commits with a message, and pushes to origin."
---

Stage all changes, create a commit, and push to GitHub (origin).

## Steps

1. Run `git status` to see what changed.
2. Run `git add .` to stage all changes.
3. If there is nothing to commit — report "nothing to push, working tree clean" and stop.
4. Determine a short, descriptive commit message that summarizes the changes (use English or Hebrew depending on the context).
5. Run `git commit -m "<message>"`.
6. Run `git push`.
7. Confirm success by showing the last commit line from `git log --oneline -1`.

## Rules

- Never force-push (`--force`).
- Never amend published commits.
- If push fails with an auth error, tell the user to check credentials and stop — do not retry.
- Keep commit messages concise (under 72 characters).
