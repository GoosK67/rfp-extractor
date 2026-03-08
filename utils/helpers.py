
import re
import hashlib
from pathlib import Path
import json

_SHELL_PATTERNS_CACHE = None

def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())

def is_heading(text: str) -> bool:
    # Heuristic: short all-caps or starts with numbered outline
    if not text:
        return False
    t = text.strip()
    if len(t) < 3:
        return False
    if t.isupper():
        return True
    if re.match(r"^(\d+\.)+\s+\S+", t):  # 1. / 1.2.3 style
        return True
    if re.match(r"^(Chapter|Hoofdstuk|Section|Sectie)\s+\d+", t, flags=re.I):
        return True
    return False

def classify_requirement(text: str) -> str | None:
    '''Very lightweight classifier returning 'BR', 'FR', 'NFR' or None.'''
    t = (text or "").lower()
    if len(t) < 12:
        return None
    # NFR first (quality attributes, security, performance)
    nfr_kw = [
        "availability", "performance", "latency", "throughput", "security",
        "encrypt", "privacy", "gdpr", "sla", "resilience", "capacity", "backup",
        "restore", "audit", "monitoring", "response time", "rto", "rpo"
    ]
    if any(k in t for k in nfr_kw):
        return 'NFR'
    # FR (capabilities, actions)
    fr_kw = [
        "shall", "must", "should", "provide", "support", "integrate", "implement",
        "deliver", "configure", "authenticate", "authorize", "export", "import"
    ]
    if any(k in t for k in fr_kw):
        return 'FR'
    # BR (business intent)
    br_kw = [
        "business", "stakeholder", "governance", "policy", "budget", "kpi", "benefit",
        "objective", "strategy", "compliance", "risk"
    ]
    if any(k in t for k in br_kw):
        return 'BR'
    return None

def _load_shell_patterns() -> list[str]:
    global _SHELL_PATTERNS_CACHE
    if _SHELL_PATTERNS_CACHE is not None:
        return _SHELL_PATTERNS_CACHE
    default = [
        r"^external service provider .* shall be:?$",
        r"^the (supplier|provider) shall:?$",
        r"^the tenderer shall:?$",
        r"^requirements?:$",
        r"^scope:?$",
        r"^out of scope:?$",
        r"^to be (defined|determined)[:.]?$",
        r"^n/?a$",
        r"^tbd$",
        r"^shall be:?$",
    ]
    p = Path(__file__).parent / 'patterns_shell.json'
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
            pats = data.get('patterns', [])
            if isinstance(pats, list) and all(isinstance(x, str) for x in pats):
                _SHELL_PATTERNS_CACHE = pats or default
                return _SHELL_PATTERNS_CACHE
        except Exception:
            pass
    _SHELL_PATTERNS_CACHE = default
    return _SHELL_PATTERNS_CACHE

def is_shell_requirement(text: str) -> bool:
    t = normalize_ws(text).lower()
    pats = _load_shell_patterns()
    return any(re.match(p, t) for p in pats)

def generate_req_id(text: str, source: str) -> str:
    base = f"{normalize_ws(text)}|{source}".encode('utf-8')
    h = hashlib.sha1(base).hexdigest()[:10]
    return f"REQ-{h.upper()}"
