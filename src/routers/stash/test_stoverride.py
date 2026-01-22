import re
from typing import cast

import pytest
import yaml
from fastapi.testclient import TestClient
from main import app
from routers.stash.stoverride import kv_pair_parse


@pytest.fixture(scope='module')
def client():
    with TestClient(app) as client:
        yield client


def test_github_rate_limit(client: TestClient):
    response = client.get('/api/stash/stoverride/tiles/github/rate-limit')
    assert response.status_code == 200


def test_override_NSRingo_WeatherKit(client: TestClient):
    response = client.get('/api/stash/stoverride/NSRingo/WeatherKit')
    assert response.status_code == 200


def test_override_loon(client: TestClient):
    response = client.get(
        '/api/stash/stoverride/loon', params={'url': 'https://kelee.one/Tool/Loon/Lpx/YouTube_remove_ads.lpx'}
    )
    assert response.status_code == 200

    response = client.get(
        '/api/stash/stoverride/loon',
        params={'url': 'https://kelee.one/Tool/Loon/Lpx/YouTube_remove_ads.lpx', 'scriptArguments': ['badcase']},
    )
    assert response.status_code == 422, response.text

    response = client.get(
        '/api/stash/stoverride/loon',
        params={
            'url': 'https://kelee.one/Tool/Loon/Lpx/YouTube_remove_ads.lpx',
            'scriptArguments': ['a1=tt', 'a2=text'],
        },
    )
    assert response.status_code == 200, response.text


def test_nameserver_policy_by_geosite(client: TestClient):
    response = client.get('/api/stash/stoverride/geosite/nameserver-policy/apple')
    assert response.status_code == 200
    data = yaml.safe_load(response.text)
    assert data['dns']['nameserver-policy'], data


def test_ruleset_by_geosite(client: TestClient):
    response = client.get('/api/stash/stoverride/geosite/ruleset/apple')
    assert response.status_code == 200
    data = yaml.safe_load(response.text)
    assert data and data['payload'], data


def test_kv_pair_parse():
    line = r'http-response ^(?!.*img).*?(abt-kuwo\.tencentmusic\.com|kuwo\.cn)(/vip|/(open)?api)?(/enc.*?signver|/(v\d/)?(pay/app/getConfigInfo|user/vip\?vers|app/startup/config|theme\?op=gd|api/((pay/)?(user/info|payInfo/kwplayer/payMiniBar))|tingshu/index/radio|operate/homePage|sysinfo\?op\=getRePayAndDoPayBox(New)?&useNewHeadShow|recommend/(daily/main|songlist/getRecSonglist)|online/bottomTab/abConfig)|/kuwo/ui/info$|/kuwopay\/personal\/cells|/pay/viptab/index\.html|/kuwopay/vip-tab/(setting|page/cells)|/a\.p($|\?newver\=\d$|.*?op\=(getvip|policy_shortvideo)|.*?ptype\=vip)|/commercia/(userAssets|vip(Tab/myTab/base|/player/getStyleListByModel|/hanger/wear))|/mobi\.s\?f\=kwxs|/music\.pay\?newver\=\d(&allpay\=\d)?$|/basedata\.s|/mgxh\.s\?user) script-path=https://napi.ltd/script/Worker/KuWo.js, requires-body=true, timeout=60, tag=酷我音乐, img-url=https://static.napi.ltd/Image/KuWo.png, argument=[{QS},{authUI}]'
    matched = re.match(r'(http-request|http-response) (\S+) (.*)', line)
    if not matched:
        raise ValueError(f'invalid script line: {line}')

    type_, match_, p3 = matched.groups()
    type_ = type_.replace('http-', '')
    p3 = cast(str, p3)
    print()
    print('>>>>>>>>>>>>>>>>>>>>>>>>>>>')
    print(type_)
    print('>>>>>>>>>>>>>>>>>>>>>>>>>>>')
    print(match_)
    print('>>>>>>>>>>>>>>>>>>>>>>>>>>>')
    print(p3)
    print('>>>>>>>>>>>>>>>>>>>>>>>>>>>')

    kwargs = kv_pair_parse(p3)
    assert 'script-path' in kwargs
