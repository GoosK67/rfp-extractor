
import re
import hashlib

# Text normalization

def normalize_ws(t: str) -> str:
    if not isinstance(t, str):
        return ""
    return re.sub(r"\s+", " ", t).strip()

# Rule-based signals (0..1)
EN_ACTION = r"(shall|must|should|ensure|provide|support|deliver|implement|configure|operate|monitor|comply)"
NL_ACTION = r"(moet|zal|dient te|verplicht|opleveren|ondersteunen|implementeren|configureren|bewaken|voldoen)"
FR_ACTION = r"(doit|devra|devrait|assurer|fournir|mettre en place|configurer|exploiter|surveiller|se conformer)"
ACTION_RE = re.compile(rf"\b({EN_ACTION}|{NL_ACTION}|{FR_ACTION})\b", re.I)


def word_count(t:str) -> int:
    return len(re.findall(r"\w+", t))


def looks_like_header(t:str) -> bool:
    if word_count(t) <= 3 and not ACTION_RE.search(t):
        if t.isupper() or re.match(r"^([A-Z][a-z]+)(\s+[A-Z][a-z]+){0,2}$", t):
            return True
        if re.match(r"^(the\s+)?[A-Z][A-Za-z\-]+(\s+(dept|department|team|category|scope))?$", t.strip(), re.I):
            return True
    return False


def ends_with_punctuation(t:str) -> bool:
    return bool(re.search(r"[.;:?\)]\s*$", t))


def rule_requirement_score(t:str) -> float:
    # Returns 0..1 score from rule-based filters
    s = t.strip()
    if not s:
        return 0.0
    score = 0.0
    if len(s) >= 25 and word_count(s) >= 4:
        score += 0.4
    if ACTION_RE.search(s):
        score += 0.4
    if ends_with_punctuation(s) or len(s) >= 80:
        score += 0.2
    if looks_like_header(s):
        score -= 0.5
    return max(0.0, min(1.0, score))


def classify_requirement(text:str, role_hint:str|None=None) -> str:
    txt = text.lower()
    # explicit risk/scope
    if "risk" in txt:
        return "RISK"
    if "scope" in txt:
        if "out" in txt:
            return "SCOPE_OUT"
        if "in" in txt:
            return "SCOPE_IN"
        return "SCOPE_OTHER"
    # hint from role
    if role_hint == "SOW":
        if any(x in txt for x in ["deliver", "implement", "provide", "configure", "support"]):
            return "FR"
    # NFR
    if any(x in txt for x in ["security", "sla", "continuity", "performance", "availability", "privacy", "encrypt"]):
        return "NFR"
    # FR vs BR heuristic
    if any(x in txt for x in ["provide", "implement", "deliver", "support", "configure", "monitor", "operate"]):
        return "FR"
    return "BR"


def detect_document_role(sample_text: str, filename: str) -> str:
    f = filename.lower()
    t = (sample_text or "").lower()
    if "annex d" in f or "requirements" in f or "requirement" in t:
        return "REQ_ANNEX"
    if "pricing" in f or "annex c" in f or "rate" in t:
        return "PRICING"
    if "statement of work" in f or "sow" in f:
        return "SOW"
    if "general terms" in f or "gtc" in f or "terms & conditions" in t:
        return "LEGAL"
    if "request for proposal" in t or "rfp" in f:
        return "RFP_MAIN"
    return "GENERIC"


def hash_id(text: str) -> str:
    digest = hashlib.md5(text.encode("utf-8")).hexdigest().upper()[:10]
    return f"REQ-{digest}"
