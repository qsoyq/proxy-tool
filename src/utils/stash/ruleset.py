from typing import cast

import yaml
from schemas.v2fly.geosite_pb import DomainTypeEnum
from utils.v2fly.geosite import get_geosite_library_by_url


class RulesetGeositeOverride:
    def __init__(
        self,
        name: str,
        *,
        attribute: str | None = None,
        geosite_url: str = 'https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat',
    ):
        self.name = name
        self._attribute = attribute
        self._geosite_url = geosite_url

    async def get_payloads(self) -> list[str]:
        name = self.name
        attribute = self._attribute
        geosite_list = await get_geosite_library_by_url(self._geosite_url)
        assert geosite_list.entry
        payloads = []
        for entry in geosite_list.entry:
            if entry.country_code != name.upper():
                continue
            for domain in entry.domain:
                if attribute is None or (domain.attribute and domain.attribute[0].key == attribute):
                    match domain.type:
                        case DomainTypeEnum.Domain_Full:
                            payloads.append(domain.value)
                        case DomainTypeEnum.Domain_RootDomain:
                            payloads.append(f'+.{domain.value}')
                        case DomainTypeEnum.Domain_Regex:
                            ...
        return payloads

    async def to_yaml(self) -> str:
        payloads = await self.get_payloads()
        body = {'payload': payloads}
        return cast(str, yaml.safe_dump(body, width=9999, allow_unicode=True, sort_keys=False))
