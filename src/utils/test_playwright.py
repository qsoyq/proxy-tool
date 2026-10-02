import pytest
from utils.playwright import _browser_platform, _browser_user_agent


@pytest.mark.parametrize(
    ("runtime_platform", "expected_platform"),
    [
        ("darwin", "Macintosh; Intel Mac OS X 10_15_7"),
        ("linux", "X11; Linux x86_64"),
        ("win32", "Windows NT 10.0; Win64; x64"),
    ],
)
def test_browser_platform_matches_runtime(runtime_platform: str, expected_platform: str) -> None:
    assert _browser_platform(runtime_platform) == expected_platform


@pytest.mark.parametrize(
    ("browser_version", "expected_browser"),
    [("145.0.7632.0", "Chrome/145.0.0.0"), ("149.0.7632.6", "Chrome/149.0.0.0")],
)
def test_browser_user_agent_matches_runtime_and_browser_version(browser_version: str, expected_browser: str) -> None:
    user_agent = _browser_user_agent(browser_version, "linux")

    assert "X11; Linux x86_64" in user_agent
    assert expected_browser in user_agent
    assert "HeadlessChrome" not in user_agent
