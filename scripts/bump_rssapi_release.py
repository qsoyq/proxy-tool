"""Update the pinned rssapi release and bump the project patch version."""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path

PROJECT_VERSION_PATTERN = re.compile(r'(?m)^(version = ")(?P<version>\d+\.\d+\.\d+)(")$')
RSSAPI_SOURCE_PATTERN = re.compile(
    r'(?m)^(?P<prefix>rssapi\s*=\s*\{[^}\n]*\brev\s*=\s*")(?P<rev>[^"]+)(?P<suffix>"[^}\n]*\})$'
)
SEMVER_PATTERN = re.compile(r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")


@dataclass(frozen=True)
class BumpResult:
    current_rssapi_version: str
    target_rssapi_version: str
    previous_project_version: str
    project_version: str
    updated: bool


def parse_semver(version: str) -> tuple[int, int, int]:
    match = SEMVER_PATTERN.fullmatch(version.strip())
    if match is None:
        raise ValueError(f"Unsupported semantic version: {version!r}")
    return (int(match.group("major")), int(match.group("minor")), int(match.group("patch")))


def bump_patch(version: str) -> str:
    major, minor, patch = parse_semver(version)
    return f"{major}.{minor}.{patch + 1}"


def find_project_version(pyproject_content: str) -> str:
    match = PROJECT_VERSION_PATTERN.search(pyproject_content)
    if match is None:
        raise ValueError("Could not find project version in pyproject.toml")
    return match.group("version")


def find_rssapi_version(pyproject_content: str) -> str:
    match = RSSAPI_SOURCE_PATTERN.search(pyproject_content)
    if match is None:
        raise ValueError("Could not find rssapi source revision in pyproject.toml")
    return match.group("rev")


def normalize_semver(version: str) -> str:
    major, minor, patch = parse_semver(version)
    return f"{major}.{minor}.{patch}"


def update_pyproject_content(pyproject_content: str, target_rssapi_version: str) -> tuple[str, BumpResult]:
    target_rssapi_version = normalize_semver(target_rssapi_version)
    current_rssapi_version = find_rssapi_version(pyproject_content)
    previous_project_version = find_project_version(pyproject_content)

    current_semver = parse_semver(current_rssapi_version)
    target_semver = parse_semver(target_rssapi_version)

    if target_semver <= current_semver:
        return pyproject_content, BumpResult(
            current_rssapi_version=current_rssapi_version,
            target_rssapi_version=target_rssapi_version,
            previous_project_version=previous_project_version,
            project_version=previous_project_version,
            updated=False,
        )

    next_project_version = bump_patch(previous_project_version)
    updated_content = PROJECT_VERSION_PATTERN.sub(
        rf"\g<1>{next_project_version}\3",
        pyproject_content,
        count=1,
    )
    updated_content = RSSAPI_SOURCE_PATTERN.sub(
        rf"\g<prefix>{target_rssapi_version}\g<suffix>",
        updated_content,
        count=1,
    )

    return updated_content, BumpResult(
        current_rssapi_version=current_rssapi_version,
        target_rssapi_version=target_rssapi_version,
        previous_project_version=previous_project_version,
        project_version=next_project_version,
        updated=True,
    )


def write_github_outputs(result: BumpResult, output_path: str | None) -> None:
    if not output_path:
        return

    lines = [
        f"updated={str(result.updated).lower()}",
        f"current_version={result.current_rssapi_version}",
        f"target_version={result.target_rssapi_version}",
        f"previous_project_version={result.previous_project_version}",
        f"project_version={result.project_version}",
    ]
    with Path(output_path).open("a", encoding="utf-8") as output_file:
        output_file.write("\n".join(lines))
        output_file.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="Target rssapi GitHub Release tag, for example 0.4.6")
    parser.add_argument("--pyproject", default="pyproject.toml", help="Path to pyproject.toml")
    parser.add_argument("--dry-run", action="store_true", help="Compute changes without writing pyproject.toml")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pyproject_path = Path(args.pyproject)
    pyproject_content = pyproject_path.read_text(encoding="utf-8")
    updated_content, result = update_pyproject_content(pyproject_content, args.version)

    if result.updated and not args.dry_run:
        pyproject_path.write_text(updated_content, encoding="utf-8")

    write_github_outputs(result, os.environ.get("GITHUB_OUTPUT"))

    if result.updated:
        print(
            "Updated rssapi "
            f"{result.current_rssapi_version} -> {result.target_rssapi_version}; "
            f"project version {result.previous_project_version} -> {result.project_version}."
        )
    else:
        print(
            "rssapi is already current or newer "
            f"({result.current_rssapi_version}); target release was {result.target_rssapi_version}."
        )


if __name__ == "__main__":
    main()
