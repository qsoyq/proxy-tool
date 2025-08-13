import os
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as client:
        yield client


def test_nga_threads(client: TestClient):
    cid, uid, favor = os.getenv("ngaPassportCid"), os.getenv("ngaPassportUid"), os.getenv("ngaFavor")
    assert cid and uid and favor, "env ngaPassportCid or ngaPassportUid or ngaFavor not exists"
    response = client.get("/api/nga/threads", params={"fid": 708, "favor": favor}, headers={"cid": cid, "uid": uid})
    assert response.status_code == 200


def test_nga_threads_v2(client: TestClient):
    cid, uid, favor = os.getenv("ngaPassportCid"), os.getenv("ngaPassportUid"), os.getenv("ngaFavor")
    assert cid and uid and favor, "env ngaPassportCid or ngaPassportUid or ngaFavor not exists"
    response = client.get(
        "/api/nga/threads/v2", params={"fid": [708], "favor": [favor]}, headers={"cid": cid, "uid": uid}
    )
    assert response.status_code == 200


def test_nga_sections(client: TestClient):
    response = client.get("/api/nga/sections")
    assert response.status_code == 200
