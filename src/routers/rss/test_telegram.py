import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as client:
        yield client


def test_channel_jsonfeed(client: TestClient):
    response = client.get("/api/rss/telegram/channel", params={"channels": ["JISFW"]})
    assert response.status_code == 200
    assert response.json()["items"]
