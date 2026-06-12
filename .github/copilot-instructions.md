# Copilot Instructions

This repository is a Python/FastAPI service managed with `uv`.

## Project conventions

- Keep source code under `src/`.
- Match the existing FastAPI router/schema utility patterns.
- Prefer small, focused changes tied to an issue.
- Do not introduce secrets, credentials, or local environment files.

## Verification

Use these commands when relevant:

```bash
make precommit
make mypy
make test
```

## Security

Never print, commit, or infer secrets from `.env` or GitHub Secrets. Deployment credentials belong in GitHub Secrets or the deployment platform's secret store.
