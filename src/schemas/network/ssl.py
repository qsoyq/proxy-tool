from pydantic import BaseModel, Field


class SSLCertSchema(BaseModel):
    host: str
    resolved_ip: str
    issued_to: str
    issued_o: str
    issuer_c: object | None = Field(None)
    issuer_o: str
    issuer_ou: object | None = Field(None)
    issuer_cn: str
    cert_sn: str
    cert_sha1: str
    cert_alg: str
    cert_ver: int
    cert_sans: str
    cert_exp: bool
    cert_valid: bool
    valid_from: str
    valid_till: str
    validity_days: int
    days_left: int
    valid_days_to_expire: int
    tcp_port: int


class SSLCertsResSchema(BaseModel):
    li: list[SSLCertSchema | None]
