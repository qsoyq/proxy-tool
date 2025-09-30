import yaml
from typing import cast
from utils.v2fly.geosite import get_domains_by_geosite, RecordEnum


class NameserverPolicyGeositeOverride:
    def __init__(self, name: str, *, dns: str = "system", attribute: str | None = None):
        self.name = name
        self._dns = dns
        self._attribute = attribute

    async def to_yaml(self) -> str:
        items = await get_domains_by_geosite(self.name)
        policy: dict[str, str] = {}
        name = self.name
        if self._attribute:
            name = f"{name}@{self._attribute}"
        body = {
            "name": f"nameserver-policy-geosite-{name}",
            "desc": "基于 geosite 动态生成的 nameserver-policy 覆写策略",
            "icon": "https://stash.wiki/favicon.ico",
            "category": "dns",
            "dns": {"nameserver-policy": policy},
        }
        for item in items:
            if self._attribute is not None and item._attribute != self._attribute:
                continue
            item._value = cast(str, item._value)

            match item._type:
                case RecordEnum.full:
                    policy[item._value] = self._dns
                case RecordEnum.domain:
                    policy[f"+.{item._value}"] = self._dns
                case RecordEnum.regexp:
                    policy[item._value] = self._dns
        return cast(str, yaml.safe_dump(body, width=9999, allow_unicode=True))
