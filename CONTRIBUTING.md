# Contributing

Thanks for contributing to `proxy-tool`.

## Development flow

1. Open or pick an issue before starting non-trivial work.
2. Create a branch from `main` using `<type>/<issue-id>-<short-desc>`, for example `fix/123-cache-timeout`.
3. Keep each pull request focused on one goal.
4. Use Conventional Commits: `<type>: <short summary>`.
5. Link commits with `Refs #<issue-id>` and let the PR body close the issue with `Closes #<issue-id>` when appropriate.

## Local setup

```bash
uv sync
```

## Checks before opening a PR

```bash
make precommit
make mypy
make test
```

If a check fails because of an existing unrelated issue, document the failure and scope boundary in the PR.

## Security and secrets

- Do not commit `.env`, tokens, passwords, API keys, private keys, or production configuration.
- Use GitHub Secrets or deployment-provider secret storage for runtime credentials.
- Report vulnerabilities using the process in `SECURITY.md`.

## Review expectations

- Explain the user-visible or operational impact.
- Include verification steps and relevant logs.
- Document risks, rollback plan, and AI assistance if used.
