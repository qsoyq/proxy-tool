import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope='module')
def client():
    with TestClient(app) as client:
        yield client


def test_live_room_list(client: TestClient):
    response = client.get('/api/bilibili/live/room/list', params={'rooms': [30167396]})
    assert response.status_code == 200


def test_live_room(client: TestClient):
    response = client.get('/api/bilibili/live/room/30167396')
    assert response.status_code == 200
