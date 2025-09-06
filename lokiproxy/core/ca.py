import pathlib
import datetime
from typing import Tuple
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption

DEFAULT_DIR = pathlib.Path.home() / ".lokiproxy"
CA_CERT_PATH = DEFAULT_DIR / "ca.pem"
CA_KEY_PATH = DEFAULT_DIR / "ca.key"

def ensure_ca(common_name: str = "HuginProxy Local Test CA") -> Tuple[x509.Certificate, rsa.RSAPrivateKey]:
    DEFAULT_DIR.mkdir(parents=True, exist_ok=True)
    if CA_CERT_PATH.exists() and CA_KEY_PATH.exists():
        with open(CA_KEY_PATH, "rb") as f:
            key = serialization.load_pem_private_key(f.read(), password=None)
        with open(CA_CERT_PATH, "rb") as f:
            cert = x509.load_pem_x509_certificate(f.read())
        return cert, key

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow() - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(x509.KeyUsage(digital_signature=True, key_cert_sign=True, crl_sign=True,
                                     key_encipherment=False, data_encipherment=False,
                                     content_commitment=False, key_agreement=False, encipher_only=False, decipher_only=False), critical=True)
        .sign(key, hashes.SHA256())
    )
    with open(CA_KEY_PATH, "wb") as f:
        f.write(key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()))
    with open(CA_CERT_PATH, "wb") as f:
        f.write(cert.public_bytes(Encoding.PEM))
    return cert, key

def issue_cert_for_host(hostname: str, ca_cert: x509.Certificate, ca_key: rsa.RSAPrivateKey) -> Tuple[bytes, bytes]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname)])
    san = x509.SubjectAlternativeName([x509.DNSName(hostname)])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow() - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=825))
        .add_extension(san, critical=False)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(Encoding.PEM)
    key_pem = key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
    return cert_pem, key_pem
