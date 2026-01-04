import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope='module')
def client():
    with TestClient(app) as client:
        yield client


def test_ping(client: TestClient):
    response = client.get('/api/apple/itunes/appstore/apps', params={'term': 'wechat'})
    assert response.status_code == 200
    assert response.json()['data']
