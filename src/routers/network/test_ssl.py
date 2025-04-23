import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as client:
        yield client


def test_ssl_certs(client: TestClient):
    hosts = ["p.19940731.xyz"]
    response = client.get("/api/network/ssl/certs", params={"hosts": hosts})
    assert response.status_code == 200
