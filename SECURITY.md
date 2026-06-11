# Security Policy

## Supported versions

Security fixes are applied to the default branch and released with the next normal or hotfix release.

## Reporting a vulnerability

Please report suspected vulnerabilities privately to the repository owner instead of opening a public issue.

Include:

- Affected endpoint, workflow, or dependency.
- Reproduction steps or proof of impact.
- Whether credentials, tokens, or user data may be exposed.
- Suggested mitigation if known.

The maintainer will acknowledge the report, assess impact, and coordinate a fix before public disclosure.

## Secret handling

- Never commit `.env`, API tokens, passwords, private keys, service-account files, or production credentials.
- Rotate any credential that may have been committed or printed in logs.
- Keep deployment credentials in GitHub Secrets or the deployment platform's secret store.
