# proxy-tool

`proxy-tool` is a Python/FastAPI service that exposes small proxy, conversion, feed, notification, and utility endpoints. It is maintained as a personal API toolbox and deployed through GitHub Actions.

## Tech stack

- Python 3.10+; CI currently uses Python 3.12 for dependency compatibility
- FastAPI / Uvicorn / Hypercorn
- `uv` for dependency and lockfile management
- Ruff, mypy, pytest, and pre-commit for local quality checks
- Docker for containerized deployment

## Local setup

```bash
uv sync
```

Run the application locally with the module entrypoint used by the project:

```bash
PYTHONPATH=./src uv run python src/main.py
```

Or run an ASGI server directly if you need custom host/port options:

```bash
PYTHONPATH=./src uv run uvicorn main:app --reload
```

## Common commands

```bash
make precommit  # install and run pre-commit hooks
make mypy       # run type checking
make test       # run pytest with PYTHONPATH=./src
make format     # run pre-commit and mypy
```

## Build

Build the Docker image locally:

```bash
docker build -t proxy-tool:local .
```

Run with Docker Compose:

```bash
docker compose up --build
```

## Release and deployment

- Publishing a GitHub release triggers `.github/workflows/release-image.yml`, which builds and pushes Docker image tags for the release tag and `latest`.
- Pushing to the `render` branch triggers `.github/workflows/render.yml`, which deploys to the production Render service.
- Production workflows use the `production` GitHub Environment. Repository admins should configure required reviewers for that environment before relying on it as an approval gate.

## Rollback

- Docker image rollback: redeploy a previously known-good release image tag.
- Render deployment rollback: restore the previous Render deployment or revert the `render` branch to the last known-good commit.
- Code rollback: revert the offending PR and rerun the deployment workflow.

## Branch and PR strategy

- `main` is the default branch.
- Use short-lived branches named `<type>/<issue-id>-<short-desc>`, for example `fix/123-cache-timeout`.
- Open an issue for non-trivial work and link the PR with `Closes #<issue-id>`.
- PRs should pass CI and receive review before merging.

## Documentation

- Contribution guide: [CONTRIBUTING.md](CONTRIBUTING.md)
- Security policy: [SECURITY.md](SECURITY.md)
- Release notes and runbooks: [docs/release/](docs/release/)
- Architecture decisions: [docs/decisions/](docs/decisions/)
- Postmortems: [docs/postmortems/](docs/postmortems/)

## Command Line Dependencies

```shell
uv tool install git+https://github.com/qsoyq/twitter-cli.git@develop
```

## Notes

### macOS

```zsh
export DYLD_LIBRARY_PATH="/opt/homebrew/opt/cairo/lib:$DYLD_LIBRARY_PATH"
```

## Maintainer

- Owner: [@qsoyq](https://github.com/qsoyq)
