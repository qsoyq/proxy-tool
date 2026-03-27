import pytest
from fastapi.testclient import TestClient
from main import app
from routers.network.dns.doh import _query_doh_json, _query_doh_wireformat


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as client:
        yield client


CLOUDFLARE_DOH = "https://1.1.1.1/dns-query"
ADGUARD_DOH = "https://dns.adguard-dns.com/dns-query"
TEST_DOMAIN = "example.com"


def _assert_doh_result(data: dict):
    """校验 DoH 结果的通用结构。"""
    assert data["Status"] == 0
    for flag in ("TC", "RD", "RA", "AD", "CD"):
        assert flag in data
        assert isinstance(data[flag], int)

    assert isinstance(data["Question"], list)
    assert len(data["Question"]) >= 1
    q = data["Question"][0]
    assert "name" in q
    assert q["type"] == 1

    assert isinstance(data["Answer"], list)
    assert len(data["Answer"]) >= 1
    for ans in data["Answer"]:
        assert "name" in ans
        assert ans["type"] == 1
        assert isinstance(ans["TTL"], int)
        assert "data" in ans


class TestQueryDohJson:
    def test_cloudflare_returns_result(self):
        data = _query_doh_json(CLOUDFLARE_DOH, TEST_DOMAIN)
        assert data is not None
        _assert_doh_result(data)

    def test_adguard_returns_none(self):
        data = _query_doh_json(ADGUARD_DOH, TEST_DOMAIN)
        assert data is None


class TestQueryDohWireformat:
    def test_cloudflare(self):
        data = _query_doh_wireformat(CLOUDFLARE_DOH, TEST_DOMAIN)
        _assert_doh_result(data)

    def test_adguard(self):
        data = _query_doh_wireformat(ADGUARD_DOH, TEST_DOMAIN)
        _assert_doh_result(data)


DOH_ENDPOINT = "/api/network/dns/doh"


class TestDohEndpoint:
    def test_default_doh(self, client: TestClient):
        resp = client.get(DOH_ENDPOINT, params={"name": TEST_DOMAIN})
        assert resp.status_code == 200
        _assert_doh_result(resp.json())

    def test_cloudflare_doh(self, client: TestClient):
        resp = client.get(DOH_ENDPOINT, params={"url": CLOUDFLARE_DOH, "name": TEST_DOMAIN})
        assert resp.status_code == 200
        _assert_doh_result(resp.json())

    def test_adguard_doh(self, client: TestClient):
        resp = client.get(DOH_ENDPOINT, params={"url": ADGUARD_DOH, "name": TEST_DOMAIN})
        assert resp.status_code == 200
        _assert_doh_result(resp.json())

    def test_response_matches_schema(self, client: TestClient):
        resp = client.get(DOH_ENDPOINT, params={"url": CLOUDFLARE_DOH, "name": TEST_DOMAIN})
        assert resp.status_code == 200
        data = resp.json()
        assert "Question" in data
        assert "Answer" in data
        assert "Status" in data

    def test_method_json(self, client: TestClient):
        resp = client.get(DOH_ENDPOINT, params={"url": CLOUDFLARE_DOH, "name": TEST_DOMAIN, "method": "json"})
        assert resp.status_code == 200
        _assert_doh_result(resp.json())

    def test_method_wireformat(self, client: TestClient):
        resp = client.get(DOH_ENDPOINT, params={"url": CLOUDFLARE_DOH, "name": TEST_DOMAIN, "method": "wireformat"})
        assert resp.status_code == 200
        _assert_doh_result(resp.json())

    def test_method_wireformat_adguard(self, client: TestClient):
        resp = client.get(DOH_ENDPOINT, params={"url": ADGUARD_DOH, "name": TEST_DOMAIN, "method": "wireformat"})
        assert resp.status_code == 200
        _assert_doh_result(resp.json())

    def test_method_json_unsupported_returns_error(self, client: TestClient):
        resp = client.get(DOH_ENDPOINT, params={"url": ADGUARD_DOH, "name": TEST_DOMAIN, "method": "json"})
        assert resp.status_code == 400

    def test_method_auto_fallback(self, client: TestClient):
        resp = client.get(DOH_ENDPOINT, params={"url": ADGUARD_DOH, "name": TEST_DOMAIN, "method": "auto"})
        assert resp.status_code == 200
        _assert_doh_result(resp.json())
