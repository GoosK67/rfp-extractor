# ai/ai_hooks.py
import os
from typing import List, Dict

def enrich_with_ai(requirements: List[Dict]) -> List[Dict]:
    """
    Enricht elk requirement met een korte AI-analyse (samenvatting + eventuele herclassificatie).
    Werkt met:
      - Azure OpenAI (als AZURE_OPENAI_* envs staan), of
      - Ollama (OpenAI-compatibel) via OPENAI_BASE_URL=http://localhost:11434/v1 en OPENAI_API_KEY=ollama
    Als geen van beide beschikbaar is, retourneert dit de input ongewijzigd (safe no-op).
    """
    # Detect Azure OpenAI
    azure_key = os.environ.get("AZURE_OPENAI_KEY")
    azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")

    # Detect lokale Ollama (OpenAI-compatibel)
    base_url = os.environ.get("OPENAI_BASE_URL")  # bv. http://localhost:11434/v1
    api_key = os.environ.get("OPENAI_API_KEY")    # bij Ollama: willekeurige string (bv. "ollama")
    model = os.environ.get("LLM_MODEL", "llama3.1")

    try:
        from openai import OpenAI
    except Exception:
        return requirements  # geen client → no-op

    client = None
    # 1) Azure
    if azure_key and azure_endpoint:
        # Azure OpenAI (chat.completions) endpoint via base_url
        # Let op: past aan jouw deployment naam aan (model variabel is dan je deployment name)
        client = OpenAI(
            api_key=azure_key,
            base_url=f"{azure_endpoint}/openai",
        )
        # Zet hier desnoods: model = "<jouw-azure-deployment-naam>"

    # 2) Ollama (OpenAI compatible)
    elif base_url and api_key:
        client = OpenAI(api_key=api_key, base_url=base_url)

    else:
        return requirements  # geen AI-config → no-op

    def ask_llm(txt: str) -> Dict:
        prompt = f"""
Je bent een requirements-analist. Vat de volgende requirement kernachtig samen (1 zin) en geef een mogelijke categorie (BR/FR/NFR).
Return JSON met velden: summary, suggested_category.
Requirement:
\"\"\"{txt}\"\"\"
"""
        try:
            rsp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            content = rsp.choices[0].message.content
            # Best effort JSON extractie (vereenvoudigd)
            import json, re
            m = re.search(r"\{.*\}", content, re.S)
            if m:
                data = json.loads(m.group(0))
                return {
                    "summary": data.get("summary"),
                    "suggested_category": data.get("suggested_category"),
                }
        except Exception:
            pass
        return {}

    enriched = []
    for it in requirements:
        extra = ask_llm(it.get("text", ""))
        if extra:
            it = {**it, **extra}
        enriched.append(it)
    return enriched