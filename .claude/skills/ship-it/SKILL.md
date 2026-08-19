---
name: ship-it
description: Create a pull request for the session branch and merge it when CI is green. Use when the user says "ship it" or asks to open and merge the work of the session.
---
# Ship it

Create a pull request for the work in this session.
Merge it when CI is green.
Merges are a human decision.
The invocation of this skill is that human approval (see `spec/agents.md`).

## Steps

1. Run `make check`. If it fails, stop and report the failure.
2. Commit the remaining work.
   Push the session branch to `origin`.
3. Create a pull request from the session branch to the default branch.
   Write the title and the body in ASD-STE100 Simplified Technical English.
   State what the session changed, and why.
4. Watch CI on the pull request.
   Subscribe to pull-request activity when a subscription tool is available.
   Do not poll with `sleep`.
5. If a check fails: diagnose the failure, push a fix, and watch again.
6. When all checks are green, squash-merge the pull request and delete the branch.
7. Report the merged pull request URL.

## Rules

- Ship only the session branch.
  Do not merge another pull request.
- Do not force-push.
- If a reviewer requests changes, stop and ask the user.
