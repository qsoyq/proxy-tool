import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope='module')
def client():
    with TestClient(app) as client:
        yield client


def test_ssl_certs(client: TestClient):
    hosts = ['p.19940731.xyz', 'www.baidu.com', 'www.youtube.com']
    response = client.get('/api/network/ssl/certs', params={'hosts': hosts})
    assert response.status_code == 200


def test_ssl_certs_v2(client: TestClient):
    hosts = ['p.19940731.xyz', 'www.baidu.com', 'www.youtube.com']
    response = client.get('/api/network/ssl/certs/v2', params={'hosts': hosts})
    assert response.status_code == 200
