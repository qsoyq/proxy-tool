import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as client:
        yield client


def test_json(client: TestClient):
    response = client.post("/api/basic/whoami")
    assert response.status_code == 200

    response = client.post("/api/basic/whoami", json={"key": "val"})
    assert response.status_code == 200
    assert response.json()["json"] == {"key": "val"}
