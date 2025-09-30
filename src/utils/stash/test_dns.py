import yaml
import pytest
from utils.stash.dns import NameserverPolicyGeositeOverride


@pytest.mark.asyncio
async def test_nameserver_policy_override():
    override = NameserverPolicyGeositeOverride("google")
    content = await override.to_yaml()
    print(content)
    data = yaml.safe_load(content)
    assert isinstance(data, dict), content
    assert "name" in data
    assert "desc" in data
    assert "icon" in data
    assert "category" in data
    assert "dns" in data
    assert "nameserver-policy" in data["dns"]


@pytest.mark.asyncio
async def test_nameserver_policy_with_attributes_override():
    override = NameserverPolicyGeositeOverride("google", attribute="ads")
    content = await override.to_yaml()
    print(content)
    data = yaml.safe_load(content)
    assert isinstance(data, dict), content
    assert "name" in data
    assert "desc" in data
    assert "icon" in data
    assert "category" in data
    assert "dns" in data
    assert "nameserver-policy" in data["dns"]

    assert "+.2mdn.net" in data["dns"]["nameserver-policy"]  # ads
    assert "+.google.cn" not in data["dns"]["nameserver-policy"]  # cn

    override = NameserverPolicyGeositeOverride("google", attribute="cn")
    content = await override.to_yaml()
    print(content)
    data = yaml.safe_load(content)
    assert isinstance(data, dict), content

    assert "+.2mdn.net" not in data["dns"]["nameserver-policy"]  # ads
    assert "+.google.cn" in data["dns"]["nameserver-policy"]  # cn
