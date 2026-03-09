from __future__ import annotations
import re
import hashlib

# ─────────────────────────────────────────────
# NORMALISATIE
# ─────────────────────────────────────────────

def normalize_ws(t: str) -> str:
    if not isinstance(t, str):
        return ""
    return re.sub(r"\s+", " ", t).strip()

# ─────────────────────────────────────────────
# REQUIREMENT FILTERS & SIGNALEN
# ─────────────────────────────────────────────

EN_ACTION = r"(shall|must|should|ensure|provide|support|deliver|implement|configure|operate|monitor|comply)"
NL_ACTION = r"(moet|zal|dient te|verplicht|opleveren|ondersteunen|implementeren|configureren|bewaken|voldoen)"
FR_ACTION = r"(doit|devra|devrait|assurer|fournir|mettre en place|configurer|exploiter|surveiller|se conformer)"
ACTION_RE = re.compile(rf"\b({EN_ACTION}|{NL_ACTION}|{FR_ACTION})\b", re.I)

def word_count(t: str) -> int:
    return len(re.findall(r"\w+", t))

def looks_like_header(t: str) -> bool:
    """Korte koppen/labels (titelcase/ALLCAPS, geen werkwoord)."""
    if word_count(t) <= 3 and not ACTION_RE.search(t):
        if t.isupper() or re.match(r"^([A-Z][a-z]+)(\s+[A-Z][a-z]+){0,2}$", t):
            return True
        if re.match(r"^(the\s+)?[A-Z][A-Za-z\-]+(\s+(dept|department|team|category|scope))?$", t.strip(), re.I):
            return True
    return False

def ends_with_punctuation(t: str) -> bool:
    return bool(re.search(r"[.;:?\)]\s*$", t))

def has_action_verb(t: str) -> bool:
    return bool(ACTION_RE.search(t))

# ─────────────────────────────────────────────
# LEGAL/ADRES BOILERPLATE DETECTIE (EN/NL/FR, BE-postcode)
# ─────────────────────────────────────────────

ADDR_SUFFIXES = [
    r"street", r"straat", r"avenue", r"laan", r"weg", r"boulevard", r"plein",
    r"place", r"chauss[ée]e", r"route"
]
ADDR_SUFFIX_RE = re.compile(rf"\b({'|'.join(ADDR_SUFFIXES)})\b", re.I)
BE_POSTAL_RE   = re.compile(r"\b[1-9]\d{3}\b")  # 1000..9999

LEGAL_TOKENS_RE = re.compile(
    r"(registered\s+office\s+at|maatschappelijke\s+zetel|si[èe]ge\s+social|"
    r"\b(vzw/asbl|bv/srl|nv/sa)\b|VAT|BTW|company\s+number|RPR|KBO)",
    re.I
)
ORG_LINE_HINTS_RE = re.compile(
    r"(having\s+its\s+registered\s+office|with\s+registered\s+office|"
    r"statutaire\s+zetel|si[èe]ge\s+statutaire)",
    re.I
)

def looks_like_legal_or_address(t: str) -> bool:
    s = normalize_ws(t)
    if not s:
        return False
    if LEGAL_TOKENS_RE.search(s) or ORG_LINE_HINTS_RE.search(s):
        return True
    if ADDR_SUFFIX_RE.search(s) and BE_POSTAL_RE.search(s):
        return True
    if "belg" in s.lower() and s.count(",") >= 2:
        return True
    if re.match(r"^[A-Z].{0,100},.*(Belgium|België|Belgique)\.?$", s, re.I):
        return True
    return False

# ─────────────────────────────────────────────
# RULE-SCORE (0..1) + STRIKTE POORT
# ─────────────────────────────────────────────

def rule_requirement_score(t: str) -> float:
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
    # Harde straf op legal/adres
    if looks_like_legal_or_address(s):
        score -= 1.0
    return max(0.0, min(1.0, score))

def is_probably_requirement_text(t: str) -> bool:
    if not isinstance(t, str):
        return False
    s = t.strip()
    if len(s) < 25 or word_count(s) < 4:
        return False
    if looks_like_header(s):
        return False
    if looks_like_legal_or_address(s):
        return False
    if not ends_with_punctuation(s) and len(s) < 80:
        return False
    if not has_action_verb(s):
        return False
    return True

# ─────────────────────────────────────────────
# TYPECLASSIFICATIE & ROLDETECTIE
# ─────────────────────────────────────────────

def classify_requirement(text: str, role_hint: str | None = None) -> str:
    txt = text.lower()
    if "risk" in txt:
        return "RISK"
    if "scope" in txt:
        if "out" in txt:
            return "SCOPE_OUT"
        if "in" in txt:
            return "SCOPE_IN"
        return "SCOPE_OTHER"
    if role_hint == "SOW":
        if any(x in txt for x in ["deliver", "implement", "provide", "configure", "support"]):
            return "FR"
    if any(x in txt for x in ["security", "sla", "continuity", "performance", "availability", "privacy", "encrypt"]):
        return "NFR"
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

# ─────────────────────────────────────────────
# GOVERNANCE CUES & ID
# ─────────────────────────────────────────────

GOV_CUES_RE = re.compile(
    r"(sla|service\s+level|kpi|incident|problem|change|"
    r"security|access\s+control|monitor(ing)?|continuity|"
    r"audit|compliance|risk|availability|capacity|response\s*time)",
    re.I
)

def is_governance_candidate(t: str) -> bool:
    s = normalize_ws(t)
    return bool(GOV_CUES_RE.search(s))

def hash_id(text: str) -> str:
    digest = hashlib.md5(text.encode("utf-8")).hexdigest().upper()[:10]
    return f"REQ-{digest}"