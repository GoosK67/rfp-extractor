import re
import hashlib

# ─────────────────────────────────────────────
# CLEANUP
# ─────────────────────────────────────────────

def normalize_ws(t: str) -> str:
    if not isinstance(t, str):
        return ""
    return re.sub(r"\s+", " ", t).strip()


# ─────────────────────────────────────────────
# REQUIREMENT FILTERING
# ─────────────────────────────────────────────

EN_ACTION = r"(shall|must|should|ensure|provide|support|deliver|implement|configure|operate|monitor|comply)"
NL_ACTION = r"(moet|zal|dient te|verplicht|opleveren|ondersteunen|implementeren|configureren|bewaken|voldoen)"
FR_ACTION = r"(doit|devra|devrait|assurer|fournir|mettre en place|configurer|exploiter|surveiller|se conformer)"

ACTION_RE = re.compile(rf"\b({EN_ACTION}|{NL_ACTION}|{FR_ACTION})\b", re.I)

def word_count(t: str) -> int:
    return len(re.findall(r"\w+", t))

def looks_like_header(t: str) -> bool:
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

def is_probably_requirement_text(t: str) -> bool:
    if not isinstance(t, str):
        return False
    s = t.strip()
    if len(s) < 25 or word_count(s) < 4:
        return False
    if looks_like_header(s):
        return False
    if not ends_with_punctuation(s) and len(s) < 80:
        return False
    if not has_action_verb(s):
        return False
    return True


# ─────────────────────────────────────────────
# TYPE CLASSIFICATION
# ─────────────────────────────────────────────

def classify_requirement(text: str) -> str:
    txt = text.lower()
    if "risk" in txt:
        return "RISK"
    if "scope" in txt:
        if "out" in txt:
            return "SCOPE_OUT"
        if "in" in txt:
            return "SCOPE_IN"
        return "SCOPE_OTHER"
    if any(x in txt for x in ["security", "sla", "continuity", "performance", "availability"]):
        return "NFR"
    if any(x in txt for x in ["provide", "implement", "deliver", "support", "configure"]):
        return "FR"
    return "BR"


# ─────────────────────────────────────────────
# GOVERNANCE MAPPING + EXPLANATION + CONFIDENCE
# ─────────────────────────────────────────────

COBIT_MAP = {
    "APO09": ["service level", "sla", "governance", "reporting"],
    "APO13": ["security", "risk", "protection"],
    "DSS01": ["operations", "monitoring", "run", "availability"],
    "DSS02": ["incident", "support", "servicedesk"]
}

ITIL_MAP = {
    "Incident Management": ["incident", "ticket", "servicedesk"],
    "Change Enablement": ["change", "release"],
    "Service Level Management": ["sla", "service level", "kpi"]
}

ISO_MAP = {
    "A.12 Operations Security": ["operation", "monitor", "security"],
    "A.17 Business Continuity": ["continuity", "resilience"],
    "A.9 Access Control": ["access", "identity", "permission"]
}

def map_keywords(text: str, mapping_dict: dict) -> list:
    hits = []
    lower = text.lower()
    for key, kw_list in mapping_dict.items():
        for kw in kw_list:
            if kw in lower:
                hits.append(key)
                break
    return hits


def governance_mapping(text: str):
    cobit_hits = map_keywords(text, COBIT_MAP)
    itil_hits = map_keywords(text, ITIL_MAP)
    iso_hits = map_keywords(text, ISO_MAP)

    explanation_parts = []
    confidence = 0.0
    buckets = 0

    if cobit_hits:
        explanation_parts.append(
            f"COBIT: matched {', '.join(cobit_hits)} due to governance/operations keywords."
        )
        confidence += 0.6
        buckets += 1

    if itil_hits:
        explanation_parts.append(
            f"ITIL: matched {', '.join(itil_hits)} because text contains ITIL‑related terms."
        )
        confidence += 0.6
        buckets += 1

    if iso_hits:
        explanation_parts.append(
            f"ISO27001: matched {', '.join(iso_hits)} as text references security/continuity/access‑control concepts."
        )
        confidence += 0.6
        buckets += 1

    explanation = " ".join(explanation_parts)
    final_conf = round(confidence / buckets, 2) if buckets > 0 else 0.0

    return {
        "cobit": ", ".join(cobit_hits),
        "itil": ", ".join(itil_hits),
        "iso": ", ".join(iso_hits),
        "explanation": explanation,
        "confidence": final_conf
    }


# ─────────────────────────────────────────────
# ID GENERATION
# ─────────────────────────────────────────────

def generate_req_id(text: str) -> str:
    digest = hashlib.md5(text.encode("utf-8")).hexdigest().upper()[:10]
    return f"REQ-{digest}"