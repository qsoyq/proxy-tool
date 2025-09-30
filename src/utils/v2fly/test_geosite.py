import asyncio
import pytest
from utils.v2fly.geosite import get_domains_by_geosite


@pytest.mark.asyncio
async def test_geosite():
    items = await get_domains_by_geosite("google")
    assert items

    filtered = [x for x in items if x._value == "beacons3.gvt2.com"]
    assert len(filtered) == 1, filtered
    assert filtered[0]._type == "full", filtered
    assert filtered[0]._attribute == "cn", filtered

    # include:fastlane
    filtered = [x for x in items if x._value == "fastlane.tools"]
    assert len(filtered) == 1, filtered
    assert filtered[0]._type == "domain", filtered
    assert filtered[0]._attribute is None, filtered

    # test cache
    await asyncio.wait_for(get_domains_by_geosite("google"), 1)
