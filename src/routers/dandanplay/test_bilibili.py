import random

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as client:
        yield client


def test_match(client: TestClient):
    response = client.post("/api/dandanplay/bilibili/api/v2/match")
    assert response.status_code == 200, response.text


def test_comment(client: TestClient):
    episodeId = random.randint(1, 9999999)
    response = client.get(f"/api/dandanplay/bilibili/api/v2/comment/{episodeId}")
    assert response.status_code == 200, response.text
