import time
from typing import cast
import pytest
from fastapi import FastAPI
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


@pytest.mark.skip(reason="Upstream unavailable.")
def test_random_image(client: TestClient):
    app: FastAPI = cast(FastAPI, client.app)
    path = app.url_path_for("random_image")
    resp = client.get(path, follow_redirects=False)
    assert resp.status_code == 307

    resp = client.get(path, follow_redirects=True)
    assert resp.status_code == 200
