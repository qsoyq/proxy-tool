import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as client:
        yield client


def test_github_releases(client: TestClient):
    path = "/api/rss/github/releases/repos/NSRingo/WeatherKit"
    resp = client.get(path)
    assert resp.status_code == 200, resp.text
