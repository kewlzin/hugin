from lokiproxy.core.rules import Ruleset, apply_rules

def test_mock_response():
    rs = Ruleset(rules=[{
        "name": "mock",
        "on": "request",
        "match": {"url_regex": "example\\.com"},
        "action": {"mock_response": {"status": 200, "headers": {"X-Test": "1"}, "body": "ok"}},
        "enabled": True,
    }])
    url, hdrs, body, mocked = apply_rules("request", "http://example.com", "GET", None, [], b"", rs)
    assert mocked and mocked["status"] == 200
