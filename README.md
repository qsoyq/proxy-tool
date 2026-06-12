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

### rssapi dependency release automation

`rssapi` is pinned in `pyproject.toml` as a GitHub dependency under `[tool.uv.sources]`. Updates are release-driven, not scheduled: the `rssapi` repository should trigger `.github/workflows/update-rssapi.yml` in this repository when it publishes a release such as `0.4.6`.

The proxy-tool workflow expects a specific `rssapi` release version input. When invoked, it updates the `rssapi` revision, bumps the proxy-tool patch version, runs `uv sync --all-extras --dev` to refresh `uv.lock`, runs tests, and opens a review PR.

Generated rssapi update PRs currently use the branch marker `ci/update-rssapi-<version>`. `.github/workflows/release-rssapi-update.yml` uses that marker after merge to decide whether it should create the matching proxy-tool GitHub Release and call the image build workflow. If this marker changes, update both workflows together. A future improvement could replace the branch-name marker with a more explicit mechanism such as a dedicated PR label, but that requires the release workflow to fetch and verify PR labels before creating a release.

`.github/workflows/release-image.yml` still runs for manually published GitHub Releases. It is also reusable through `workflow_call` so the rssapi post-merge workflow can build the image immediately after creating the release. Keep release creation on `GITHUB_TOKEN` plus the direct `workflow_call` path, or guard carefully against duplicate image builds if release creation later moves to a token that also triggers `release.published` workflows.

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
