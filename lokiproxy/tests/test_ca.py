from lokiproxy.core.ca import ensure_ca, issue_cert_for_host

def test_ca_issue():
    cert, key = ensure_ca()
    cert_pem, key_pem = issue_cert_for_host("example.com", cert, key)
    assert b"BEGIN CERTIFICATE" in cert_pem
    assert b"BEGIN RSA PRIVATE KEY" in key_pem
