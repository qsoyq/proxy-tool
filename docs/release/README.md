# Release and Deployment

## Release image

Publishing a GitHub release triggers `.github/workflows/release-image.yml`.

The workflow:

1. Checks out the release commit.
2. Logs in to Docker Hub with GitHub Secrets.
3. Builds and pushes `${{ secrets.IMAGE }}:<release-tag>` and `${{ secrets.IMAGE }}:latest`.

## Render production deployment

Pushing to the `render` branch triggers `.github/workflows/render.yml`.

The workflow deploys to Render with `MY_RENDER_SERVICE_ID` and `MY_RENDER_API_KEY` from GitHub Secrets.

## Production environment gate

Both production workflows declare `environment: production`. A repository administrator should configure the GitHub `production` environment with required reviewers so production changes require approval before secrets are exposed or deployment starts.

## Rollback

- Revert the PR or deployment commit if the change is code-related.
- Redeploy the previous known-good Docker image tag if the image release is bad.
- Restore the previous Render deployment or reset the `render` branch to the previous known-good commit if the Render deployment is bad.

## Platform-side checks

The following settings must be confirmed in GitHub UI or with `gh api` because they are not fully visible from local repository files:

- Branch Protection or Repository Rulesets for `main`.
- Required CI status checks.
- Required reviewer count and CODEOWNERS enforcement.
- Required reviewers for the `production` environment.
- Secret scanning, Push protection, Dependabot alerts, and Code scanning.
