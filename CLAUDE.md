# CLAUDE.md

This file gives Claude Code project context for `proxy-tool`.

## Project background

`proxy-tool` is a Python/FastAPI service that provides small proxy, conversion, feed, notification, and utility endpoints.

## Tech stack

- Python 3.10+; CI currently uses Python 3.12 for dependency compatibility
- FastAPI / Uvicorn / Hypercorn
- `uv` for dependency management
- Ruff, mypy, pytest, and pre-commit
- Docker and GitHub Actions for deployment automation

## Common commands

```bash
uv sync
make precommit
make mypy
make test
docker build -t proxy-tool:local .
```

## Testing

Run tests with:

```bash
make test
```

The Makefile sets `PYTHONPATH=./src` for pytest.

## Change guidance

- Keep changes focused on the linked issue.
- Match existing naming, module layout, and FastAPI router patterns.
- Do not mix unrelated refactors into feature or bug-fix PRs.
- Document release or rollback changes under `docs/release/` when relevant.

## Do not modify without explicit approval

- Production deployment credentials or secret names.
- GitHub Environment names used by deployment workflows.
- Public endpoint behavior unrelated to the current issue.
- Lockfiles or dependency versions unless the issue requires it.

## Security requirements

- Do not read, print, or commit `.env` contents.
- Do not commit tokens, API keys, private keys, service-account files, or production configuration.
- Keep deployment credentials in GitHub Secrets or the deployment platform secret store.
- If a suspected secret is found in tracked files, report the path and risk without repeating the secret value.
