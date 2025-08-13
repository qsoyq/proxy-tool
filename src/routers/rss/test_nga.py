import os
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as client:
        yield client


def test_threads_jsonfeed(client: TestClient):
    cid, uid, favor = os.getenv("ngaPassportCid"), os.getenv("ngaPassportUid"), os.getenv("ngaFavor")
    assert cid and uid and favor, "env ngaPassportCid or ngaPassportUid or ngaFavor not exists"

    response = client.get("/api/rss/nga/threads", params={"fids": [708], "cid": cid, "uid": uid})
    assert response.status_code == 200
    assert response.json()["items"]


def test_favor_jsonfeed(client: TestClient):
    cid, uid, favor = os.getenv("ngaPassportCid"), os.getenv("ngaPassportUid"), os.getenv("ngaFavor")
    assert cid and uid and favor, "env ngaPassportCid or ngaPassportUid or ngaFavor not exists"
    params = {"cid": cid, "uid": uid}
    response = client.get(f"/api/rss/nga/favor/{favor}", params=params)
    assert response.status_code == 200
    assert response.json()["items"]
