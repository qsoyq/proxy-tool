from enum import Enum
from functools import lru_cache
import httpx
from pydantic import BaseModel, Field, HttpUrl
import time
import jwt

APNS_HOST_NAME = "api.push.apple.com"

# https://raw.githubusercontent.com/Finb/bark-server/master/deploy/AuthKey_LH4T9V5U4R_5U8LBRXG3A.p8
BARK_TOKEN_PRIVATE_KEY = """
-----BEGIN PRIVATE KEY-----
MIGTAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBHkwdwIBAQQg4vtC3g5L5HgKGJ2+
T1eA0tOivREvEAY2g+juRXJkYL2gCgYIKoZIzj0DAQehRANCAASmOs3JkSyoGEWZ
sUGxFs/4pw1rIlSV2IC19M8u3G5kq36upOwyFWj9Gi3Ejc9d3sC7+SHRqXrEAJow
8/7tRpV+
-----END PRIVATE KEY-----
""".strip()


class JWTPayload(BaseModel):
    token: str
    timestamp: int


@lru_cache(maxsize=128)
def generate_jwt(team_id, token_private_key, auth_key_id) -> JWTPayload:
    jwt_issue_time = int(time.time())
    authentication_token = jwt.encode(
        {"iss": team_id, "iat": jwt_issue_time},
        algorithm="ES256",
        key=token_private_key,
        headers={"kid": auth_key_id},
    )
    return JWTPayload(token=authentication_token, timestamp=jwt_issue_time)


class ApplePushLevel(str, Enum):
    active = "active"
    timeSensitive = "timeSensitive"
    passive = "passive"
    critical = "critical"


class AppleAPNSAlertPayload(BaseModel):
    title: str | None
    subtitle: str | None
    body: str | None


class AppleAPNSMessage(BaseModel):
    """[Create the JSON payload](https://developer.apple.com/documentation/usernotifications/generating-a-remote-notification#Create-the-JSON-payload)"""

    alert: str | AppleAPNSAlertPayload
    category: str | None
    sound: str | None = Field(
        None,
        description="[unnotificationsound](https://developer.apple.com/documentation/usernotifications/unnotificationsound)",
    )
    mutable_content: int = Field(1, alias="mutable-content")  # type: ignore
    interruption_level: ApplePushLevel = Field(
        ApplePushLevel.passive,
        alias="interruption-level",  # type: ignore
        description="[unnotificationinterruptionlevel](https://developer.apple.com/documentation/usernotifications/unnotificationinterruptionlevel)",
    )


class ApplePushExtParams(BaseModel):
    icon: HttpUrl | None
    url: HttpUrl | None
    group: str = Field("Default")


class ApplePushAuthParams(BaseModel):
    team_id: str = Field("5U8LBRXG3A")
    auth_key_id: str = Field("LH4T9V5U4R")
    topic: str = Field("me.fin.bark")
    token_private_key: str = Field(BARK_TOKEN_PRIVATE_KEY)


class ApplePushMessage(ApplePushExtParams, ApplePushAuthParams):
    """[generating_a_remote_notification](https://developer.apple.com/documentation/usernotifications/setting_up_a_remote_notification_server/generating_a_remote_notification)

    [appleapsnativemessage](https://learn.microsoft.com/zh-cn/javascript/api/@azure/notification-hubs/appleapsnativemessage?view=azure-node-latest)

    [Create the JSON payload](https://developer.apple.com/documentation/usernotifications/generating-a-remote-notification#Create-the-JSON-payload)

    部分默认参数取自 bark
    """

    device_token: str = Field(...)
    aps: AppleAPNSMessage

    def push(self) -> httpx.Response:
        url = f"https://{APNS_HOST_NAME}/3/device/{self.device_token}"
        jwt = generate_jwt(self.team_id, self.token_private_key, self.auth_key_id)
        # 如果有条件，最好改进脚本缓存此 Token。Token 30分钟内复用同一个，每过30分钟重新生成
        # 苹果文档指明 TOKEN 生成间隔最短20分钟，TOKEN 有效期最长60分钟
        # 但经我不负责任的简单测试可以短时间内正常生成
        # 上述内容来自 bark-server 文档
        if int(time.time()) - jwt.timestamp >= 1800:
            generate_jwt.cache_clear()
            jwt = generate_jwt(self.team_id, self.token_private_key, self.auth_key_id)

        headers = {
            "apns-topic": self.topic,
            "apns-push-type": "alert",
            "authorization": f"bearer {jwt.token}",
        }

        ext = ApplePushExtParams(**self.dict()).dict(exclude_none=True)
        payload = {"aps": self.aps.dict(exclude_none=True, by_alias=True)}
        payload.update(ext)
        resp = httpx.Client(http2=True).post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp
