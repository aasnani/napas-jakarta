# Repository guidance

## Git workflow

- Never push directly to `main`.
- Make changes on a `codex/*` feature branch and open a pull request targeting `main`.
- Do not merge the pull request unless the user explicitly asks for it.

## Current application state

Read [APP_STATE.md](APP_STATE.md) before changing product scope, data sources,
deployment topology, security boundaries, or observability. Update it in the
same change when those areas materially change.

## Nested guidance

- [web/AGENTS.md](web/AGENTS.md) contains additional instructions for the Next.js workspace.
