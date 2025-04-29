import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as client:
        yield client


def test_github_rate_limit(client: TestClient):
    response = client.get("/api/stash/stoverride/tiles/github/rate-limit")
    assert response.status_code == 200
