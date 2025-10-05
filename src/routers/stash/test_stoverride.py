import pytest
import yaml
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as client:
        yield client


def test_github_rate_limit(client: TestClient):
    response = client.get("/api/stash/stoverride/tiles/github/rate-limit")
    assert response.status_code == 200


def test_override_NSRingo_WeatherKit(client: TestClient):
    response = client.get("/api/stash/stoverride/NSRingo/WeatherKit")
    assert response.status_code == 200


def test_override_loon(client: TestClient):
    response = client.get(
        "/api/stash/stoverride/loon", params={"url": "https://kelee.one/Tool/Loon/Lpx/YouTube_remove_ads.lpx"}
    )
    assert response.status_code == 200

    response = client.get(
        "/api/stash/stoverride/loon",
        params={"url": "https://kelee.one/Tool/Loon/Lpx/YouTube_remove_ads.lpx", "scriptArguments": ["badcase"]},
    )
    assert response.status_code == 422, response.text

    response = client.get(
        "/api/stash/stoverride/loon",
        params={
            "url": "https://kelee.one/Tool/Loon/Lpx/YouTube_remove_ads.lpx",
            "scriptArguments": ["a1=tt", "a2=text"],
        },
    )
    assert response.status_code == 200, response.text


def test_nameserver_policy_by_geosite(client: TestClient):
    response = client.get("/api/stash/stoverride/geosite/nameserver-policy/apple")
    assert response.status_code == 200
    data = yaml.safe_load(response.text)
    assert data["dns"]["nameserver-policy"], data


def test_ruleset_by_geosite(client: TestClient):
    response = client.get("/api/stash/stoverride/geosite/ruleset/apple")
    assert response.status_code == 200
    data = yaml.safe_load(response.text)
    assert data and data["payload"], data
