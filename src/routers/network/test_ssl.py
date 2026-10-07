from datetime import datetime, timedelta, timezone

import pytest
import ssl_checker
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient
from main import app
from OpenSSL.crypto import X509
from schemas.network.ssl import SSLCertSchema


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as client:
        yield client


def test_ssl_certs(client: TestClient):
    hosts = ["p.19940731.xyz", "www.baidu.com", "www.youtube.com"]
    response = client.get("/api/network/ssl/certs", params={"hosts": hosts})
    assert response.status_code == 200


def test_ssl_checker_parses_certificate_extensions():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
        .sign(key, hashes.SHA256())
    )
    context = ssl_checker.SSLChecker().get_cert_info("localhost", X509.from_cryptography(certificate), "127.0.0.1")
    result = SSLCertSchema.model_validate({**context, "tcp_port": 443})
    assert result.host == "localhost"
    assert result.issued_to == "localhost"
    assert result.cert_sans == "DNS:localhost"
    assert result.cert_valid


@pytest.mark.skip(reason="Depends on external hosts and can time out during SSL shutdown")
def test_ssl_certs_v2(client: TestClient):
    hosts = ["p.19940731.xyz", "www.baidu.com", "www.youtube.com"]
    response = client.get("/api/network/ssl/certs/v2", params={"hosts": hosts})
    assert response.status_code == 200
