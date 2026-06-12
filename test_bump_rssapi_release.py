from pathlib import Path

import pytest

from scripts.bump_rssapi_release import bump_patch, parse_semver, update_pyproject_content


PYPROJECT = """[project]
name = "proxy-tool"
version = "0.7.6"
dependencies = [
    "rssapi",
]

[tool.uv.sources]
rssapi = { git = "https://github.com/qsoyq/rssapi.git", rev = "0.4.5" }
"""


def test_update_pyproject_content_bumps_rssapi_and_project_patch() -> None:
    updated_content, result = update_pyproject_content(PYPROJECT, "0.4.6")

    assert result.updated is True
    assert result.current_rssapi_version == "0.4.5"
    assert result.target_rssapi_version == "0.4.6"
    assert result.previous_project_version == "0.7.6"
    assert result.project_version == "0.7.7"
    assert 'version = "0.7.7"' in updated_content
    assert 'rssapi = { git = "https://github.com/qsoyq/rssapi.git", rev = "0.4.6" }' in updated_content


def test_update_pyproject_content_does_not_change_current_version() -> None:
    updated_content, result = update_pyproject_content(PYPROJECT, "0.4.5")

    assert result.updated is False
    assert result.project_version == "0.7.6"
    assert updated_content == PYPROJECT


def test_update_pyproject_content_does_not_downgrade() -> None:
    updated_content, result = update_pyproject_content(PYPROJECT, "0.4.4")

    assert result.updated is False
    assert result.project_version == "0.7.6"
    assert updated_content == PYPROJECT


def test_update_pyproject_content_normalizes_v_prefixed_target_version() -> None:
    updated_content, result = update_pyproject_content(PYPROJECT, "v0.4.6")

    assert result.updated is True
    assert result.target_rssapi_version == "0.4.6"
    assert 'rssapi = { git = "https://github.com/qsoyq/rssapi.git", rev = "0.4.6" }' in updated_content


def test_parse_semver_accepts_optional_v_prefix() -> None:
    assert parse_semver("v0.4.6") == (0, 4, 6)


def test_bump_patch_increments_patch_version() -> None:
    assert bump_patch("0.7.6") == "0.7.7"


@pytest.mark.parametrize("version", ["latest", "0.4", "0.4.5.1"])
def test_parse_semver_rejects_unsupported_versions(version: str) -> None:
    with pytest.raises(ValueError, match="Unsupported semantic version"):
        parse_semver(version)


def test_script_path_exists() -> None:
    assert Path("scripts/bump_rssapi_release.py").exists()
