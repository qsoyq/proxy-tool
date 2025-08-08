from pydantic import BaseModel, Field


class DNSDescription:
    Name = "域名"
    Type = "解析类型,1 表示 A 记录,2 表示 NS 记录,5 表示 CNAME 记录,6 表示 MX 记录,15 表示 PTR 记录,等等"
    Class = "解析记录的类别。1 表示互联网。"
    TTL = "解析记录的生存时间(TTL)。TTL 以秒为单位,指示解析记录在缓存中的有效时间。"
    RData = "解析记录的数据。对于 A 记录, RData 是 IP 地址。对于 NS 记录, RData 是域名服务器的名称。对于 CNAME 记录, RData 是别名的名称。对于 MX 记录, RData 是邮件交换机的名称和优先级。对于 PTR 记录, RData 是指针记录指向的域名。"


class DoHResDescription:
    Status = "查询状态。0 表示查询成功，其他值表示查询失败。"
    TC = "截断标志。如果该标志设置为 true, 则表示响应被截断了。"
    RD = "递归标志。如果该标志设置为 true, 则表示服务器进行了递归查询。"
    RA = "授权回答标志。如果该标志设置为 true, 则表示服务器是该域名的权威服务器。"
    AD = "非授权回答标志。如果该标志设置为 true, 则表示服务器不是该域名的权威服务器。"
    CD = "检查禁用标志。如果该标志设置为 true, 则表示客户端不应缓存该响应。"


class DNSQuestion(BaseModel):
    name: str = Field(..., description=DNSDescription.Name)
    type: int = Field(..., description=DNSDescription.Type)
    class_: int | None = Field(None, description=DNSDescription.Class, alias="class")


class DNSAnswer(BaseModel):
    name: str = Field(..., description=DNSDescription.Name)
    type: int = Field(..., description=DNSDescription.Type)
    TTL: int = Field(..., description=DNSDescription.TTL)
    data: str = Field(..., description=DNSDescription.RData)
    # Class: int|None = Field(None, description=DNSDescription.Class)


class DoHResponse(BaseModel):
    Status: int = Field(..., description=DoHResDescription.Status)
    TC: int = Field(..., description=DoHResDescription.TC)
    RD: int = Field(..., description=DoHResDescription.RD)
    RA: int = Field(..., description=DoHResDescription.RA)
    AD: int = Field(..., description=DoHResDescription.AD)
    CD: int = Field(..., description=DoHResDescription.CD)

    Question: list[DNSQuestion] | DNSQuestion
    Answer: list[DNSAnswer] | DNSAnswer | None = None
    Authority: list[DNSAnswer] | None = None
    Additional: list | None = None
