import re
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field
import yaml

class RuleMatch(BaseModel):
    url_regex: Optional[str] = None
    method: Optional[str] = None
    status: Optional[int] = None

class RuleAction(BaseModel):
    rewrite_url: Optional[str] = None
    set_headers: Dict[str, str] = Field(default_factory=dict)
    remove_headers: List[str] = Field(default_factory=list)
    set_request_body: Optional[str] = None
    set_response_body: Optional[str] = None
    mock_response: Optional[Dict[str, Any]] = None

class Rule(BaseModel):
    name: str
    match: RuleMatch
    on: str = Field(default="request", pattern="^(request|response)$")
    action: RuleAction
    enabled: bool = True

class Ruleset(BaseModel):
    rules: List[Rule] = Field(default_factory=list)

    @staticmethod
    def load_from_yaml(path: str) -> "Ruleset":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return Ruleset(**data)

    def dump_yaml(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.dict(), f, sort_keys=False, allow_unicode=True)

def apply_rules(kind: str, url: str, method: str, status: Optional[int], headers: List[Tuple[str,str]], body: bytes, ruleset: Ruleset):
    mocked = None
    hdict = {k.lower(): v for k, v in headers}
    for rule in ruleset.rules:
        if not rule.enabled or rule.on != kind:
            continue
        m = rule.match
        if m.url_regex and not re.search(m.url_regex, url):
            continue
        if m.method and m.method.upper() != method.upper():
            continue
        if m.status is not None and status != m.status:
            continue

        a = rule.action
        if a.rewrite_url and kind == "request":
            url = a.rewrite_url

        for k, v in a.set_headers.items():
            hdict[k.lower()] = v
        for k in a.remove_headers:
            hdict.pop(k.lower(), None)

        if a.set_request_body and kind == "request":
            body = a.set_request_body.encode("utf-8")
        if a.set_response_body and kind == "response":
            body = a.set_response_body.encode("utf-8")

        if a.mock_response and kind == "request":
            mocked = {
                "status": int(a.mock_response.get("status", 200)),
                "headers": [(k, str(v)) for k, v in (a.mock_response.get("headers") or {}).items()],
                "body": (a.mock_response.get("body") or "").encode("utf-8"),
            }
            break

    new_headers = [(k.title(), v) for k, v in hdict.items()]
    return url, new_headers, body, mocked
