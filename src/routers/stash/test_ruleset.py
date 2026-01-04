import pytest
import yaml
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope='module')
def client():
    with TestClient(app) as client:
        yield client


def test_adblock_to_stash_ruleset(client: TestClient):
    for url in (
        'https://thhbdd.github.io/Block-pcdn-domains/ban.txt',
        'https://cdn.jsdelivr.net/gh/susetao/PCDNFilter-CHN-@main/PCDNFilter.txt',
    ):
        response = client.get(
            '/api/stash/ruleset/adblock',
            params={'url': url},
        )
        assert response.status_code == 200
        ruleset = yaml.safe_load(response.text)
        assert ruleset.get('payload'), url
