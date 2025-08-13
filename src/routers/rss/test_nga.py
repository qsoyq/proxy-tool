import time
import os
import pytest
from fastapi.testclient import TestClient
from main import app

FIRST_DELAY = True


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="function", autouse=True)
def delay(request):
    marker = request.node.get_closest_marker("nga_delay")
    if marker:
        global FIRST_DELAY
        if FIRST_DELAY is True:
            FIRST_DELAY = False
        else:
            _wait = 5
            test_name = request.node.name
            print(f"\n'{test_name}' is marked as nga_delay. Pausing for {_wait} seconds...")
            time.sleep(_wait)

    yield


@pytest.mark.nga_delay
def test_favor_jsonfeed(client: TestClient):
    cid, uid, favor = os.getenv("ngaPassportCid"), os.getenv("ngaPassportUid"), os.getenv("ngaFavor")
    assert cid and uid and favor, "env ngaPassportCid or ngaPassportUid or ngaFavor not exists"
    params = {"cid": cid, "uid": uid}

    response = client.get(f"/api/rss/nga/favor/{favor}", params=params)
    assert response.status_code == 200
    body = response.json()
    assert body["items"], response.text
    for item in body["items"]:
        assert item.get("author"), item
        assert item.get("content_html"), item


@pytest.mark.nga_delay
def test_threads_jsonfeed(client: TestClient):
    cid, uid, favor = os.getenv("ngaPassportCid"), os.getenv("ngaPassportUid"), os.getenv("ngaFavor")
    assert cid and uid and favor, "env ngaPassportCid or ngaPassportUid or ngaFavor not exists"

    response = client.get("/api/rss/nga/threads", params={"fids": [708], "cid": cid, "uid": uid})
    assert response.status_code == 200
    body = response.json()
    assert body["items"], response.text
    for item in body["items"]:
        assert item.get("author"), item
        assert item.get("content_html"), item
