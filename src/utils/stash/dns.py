from typing import cast

import yaml

from utils.v2fly.geosite import get_domains_by_geosite_library


class NameserverPolicyGeositeOverride:
    def __init__(
        self,
        name: str,
        *,
        dns: str = 'system',
        attribute: str | None = None,
        geosite_url: str = 'https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat',
    ):
        self.name = name
        self._dns = dns
        self._attribute = attribute
        self._geosite_url = geosite_url

    async def to_yaml(self) -> str:
        domains = await get_domains_by_geosite_library(
            self.name, attribute=self._attribute, geosite_url=self._geosite_url
        )
        policy: dict[str, str] = {}
        policy = {domain: self._dns for domain in domains}
        name = self.name
        if self._attribute:
            name = f'{name}@{self._attribute}'
        body = {
            'name': f'nameserver-policy-geosite-{name}',
            'desc': '基于 geosite 动态生成的 nameserver-policy 覆写策略',
            'icon': 'https://stash.wiki/favicon.ico',
            'category': 'dns',
            'dns': {'nameserver-policy': policy},
        }

        return cast(str, yaml.safe_dump(body, width=9999, allow_unicode=True, sort_keys=False))
