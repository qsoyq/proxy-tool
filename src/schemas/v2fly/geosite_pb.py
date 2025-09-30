"""
https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat
"""

from enum import IntEnum
import proto


class DomainTypeEnum(IntEnum):
    Domain_Plain = 0
    Domain_Regex = 1
    Domain_RootDomain = 2
    Domain_Full = 3


class Domain_Attribute(proto.Message):
    key = proto.Field(proto.STRING, number=1)
    bool_value = proto.Field(proto.BOOL, number=2, oneof="typed_value")
    int_value = proto.Field(proto.INT64, number=3, oneof="typed_value")


class Domain(proto.Message):
    type = proto.Field(proto.INT32, number=1)
    value = proto.Field(proto.STRING, number=2)
    attribute = proto.RepeatedField(Domain_Attribute, number=3)


class GeoSite(proto.Message):
    country_code = proto.Field(proto.STRING, number=1)
    domain = proto.RepeatedField(Domain, number=2)
    resource_hash = proto.RepeatedField(proto.BYTES, number=3)
    code = proto.Field(proto.STRING, number=4)
    file_path = proto.Field(proto.STRING, number=5)


class GeoSiteList(proto.Message):
    entry = proto.RepeatedField(GeoSite, number=1)
