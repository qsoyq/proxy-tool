import pytest
from fastapi.testclient import TestClient
from main import app

FIRST_DELAY = True


@pytest.fixture(scope='module')
def client():
    with TestClient(app) as client:
        yield client


def test_douyin_user_share_link(client: TestClient):
    text = '7- 长按复制此条消息，打开抖音搜索，查看TA的更多作品。 https://v.douyin.com/X8LSqawyHdg/ 3@8.com :8pm'
    resp = client.get('/api/tool/url/douyin/user/share', params={'text': text})
    assert resp.status_code == 200
    assert resp.text.startswith('https://www.iesdouyin.com/share/user')
