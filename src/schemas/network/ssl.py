from pydantic import BaseModel, Field


class SSLCertSchema(BaseModel):
    host: str
    tcp_port: int
    resolved_ip: str | None = Field(None)
    issued_to: str
    issued_o: str | None = Field(None)
    issuer_c: str | None = Field(None)
    issuer_o: str | None = Field(None)
    issuer_ou: str | None = Field(None)
    issuer_cn: str | None = Field(None)
    cert_sn: str | None = Field(None)
    cert_sha1: str | None = Field(None)
    cert_alg: str | None = Field(None)
    cert_ver: int
    cert_sans: str | None = Field(None)
    cert_exp: bool
    cert_valid: bool
    valid_from: str | None = Field(None)
    valid_till: str | None = Field(None)
    validity_days: int
    valid_days_to_expire: int
    days_left: int | None = Field(None, deprecated=True)


class SSLCertsResSchema(BaseModel):
    li: list[SSLCertSchema | None]
