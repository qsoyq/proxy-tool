import asyncio
from typing import cast
from itertools import chain
from enum import Enum

import httpx
from fastapi import HTTPException
from utils.cache import cached, RandomTTLCache


class RecordEnum(str, Enum):
    comment = "comment"
    full = "full"
    regexp = "regexp"
    include = "include"
    domain = "domain"


class Record:
    def __init__(self, line: str):
        line = line.strip()
        self._type = self._value = self._attribute = None
        if line.startswith("#"):
            self._type = RecordEnum.comment.value
            line = line[1:].strip()
        elif line.startswith("full"):
            self._type = RecordEnum.full.value
            line = line.split(":", 1)[1].strip()
        elif line.startswith("regexp"):
            self._type = RecordEnum.regexp.value
            line = line = line.split(":", 1)[1].strip()
        elif line.startswith("include"):
            self._type = RecordEnum.include.value
            line = line = line.split(":", 1)[1].strip()
        else:
            self._type = RecordEnum.domain.value

        if "@" in line:
            self._value, self._attribute = [x.strip() for x in line.split(" ", 1)]
        else:
            self._value = line.strip()

        if self._attribute and self._attribute.startswith("@"):
            self._attribute = self._attribute[1:]

    def __repr__(self) -> str:
        return f"{self._type} - {self._value} - {self._attribute}"


@cached(RandomTTLCache(4096, 43200))
async def fetch_by_name(name):
    url = f"https://raw.githubusercontent.com/v2fly/domain-list-community/master/data/{name}"
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(url)
        if resp.is_error:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        lines = resp.text
    return lines


class GeoSite:
    def __init__(self, name):
        attribute = None
        if "@" in name:
            name, attribute = name.split("@")
        self._name = name
        self._attribute = attribute
        self.data: list[Record] = []

    async def fetch(self):
        lines = await fetch_by_name(self._name)
        for line in lines.split("\n"):
            if not line:
                continue
            self.data.append(Record(line))

    def __iter__(self):
        return chain(self.domains, self.include, self.regexp, self.full)

    @property
    def domains(self) -> list[Record]:
        return [x for x in self.data if x._type == "domain"]

    @property
    def include(self) -> list[Record]:
        return [x for x in self.data if x._type == "include"]

    @property
    def regexp(self) -> list[Record]:
        return [x for x in self.data if x._type == "regexp"]

    @property
    def full(self) -> list[Record]:
        return [x for x in self.data if x._type == "full"]


async def get_domains_by_geosite(name: str, *, include_all: bool = True) -> set[Record]:
    result: set[Record] = set()
    site = GeoSite(name)
    await site.fetch()
    for record in site:
        result.add(record)

    if not include_all:
        return result

    childs: list[Record] = []
    for include in site.include:
        childs.append(include)

    tasks = [get_domains_by_geosite(cast(str, child._value), include_all=include_all) for child in childs]
    items = await asyncio.gather(*tasks)
    for item in items:
        result |= item

    return result
