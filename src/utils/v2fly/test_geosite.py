import asyncio

import pytest
from utils.v2fly.geosite import get_domains_by_geosite, get_domains_by_geosite_library


@pytest.mark.asyncio
async def test_geosite():
    items = await get_domains_by_geosite('google')
    assert items

    filtered = [x for x in items if x._value == 'beacons3.gvt2.com']
    assert len(filtered) == 1, filtered
    assert filtered[0]._type == 'full', filtered
    assert filtered[0]._attribute == 'cn', filtered

    # include:fastlane
    filtered = [x for x in items if x._value == 'fastlane.tools']
    assert len(filtered) == 1, filtered
    assert filtered[0]._type == 'domain', filtered
    assert filtered[0]._attribute is None, filtered

    # test cache
    await asyncio.wait_for(get_domains_by_geosite('google'), 1)


@pytest.mark.asyncio
async def test_geosite_librady_by_url():
    results = await get_domains_by_geosite_library('google')
    assert 'beacons3.gvt2.com' in results
    assert '+.fastlane.tools' in results

    results = await get_domains_by_geosite_library('google', attribute='cn')
    assert 'sup.l.google.com' in results
    assert '+.adsense.com' not in results

    results = await get_domains_by_geosite_library('google', attribute='ads')
    assert '+.sup.l.google.com' not in results
    assert '+.adsense.com' in results

    results = await get_domains_by_geosite_library('google-ads')
    assert '+.sup.l.google.com' not in results
    assert '+.adsense.com' in results

    await asyncio.wait_for(get_domains_by_geosite_library('google'), 1)
