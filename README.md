# RFP Extractor

AI‑ondersteunde extractor voor RFP’s in **.docx**: herkent **BR/FR/NFR**, filtert “shell requirements”, extraheert tekst én tabellen, en doet optionele **governance‑mapping** (COBIT/ITIL/ISO) + **AI‑enrichment**.

***

## Inhoud

*   \#1-vereisten
*   \#2-repository-reproduceren
*   \#3-installatie-python
*   \#4-basisscenario-draaien-zonder-ai
*   \#5-ai-scenario-a-azure-openai
*   \#6-ai-scenario-b-lokaal-met-llama-ollama
*   \#7-governance-mappings-beheren
*   \#8-troubleshooting

***

## 1. Vereisten

*   **Python 3.10+**
*   **Git**
*   Windows, macOS of Linux
*   Voor AI (optie):
    *   **Azure OpenAI** *of*
    *   **Ollama** met **LLaMA‑model** lokaal

***

## 2. Repository reproduceren

### Optie 1 — Clonen (aanbevolen)

```bash
git clone https://github.com/<org-of-user>/rfp-extractor.git
cd rfp-extractor
```

> Heb je geen git‑toegang? Vraag ‘Read’ of ‘Contribute’ op de repo.

### Optie 2 — ZIP

1.  Download de ZIP van de repo (Code → Download ZIP)
2.  Pak uit naar een werkmap zonder spaties/sync‑locks (bv. `C:\Dev\rfp-extractor`)

***

## 3. Installatie (Python)

Maak een virtuele omgeving en installeer de dependencies.

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate
pip install -r requirements.txt
```

**macOS/Linux (bash/zsh):**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

***

## 4. Basisscenario: draaien zonder AI

```bash
python rfp_extract.py "examples/example.docx" --xlsx out.xlsx
```

**Output**: `out.xlsx` met kolommen:

*   `req_id` – stabiele hash voor traceability
*   `category` – BR/FR/NFR (heuristisch)
*   `text`, `heading`, `source`
*   `COBIT`, `ITIL`, `ISO27001` (keyword‑match)
*   `confidence` (0.0–0.9, op basis van #keywordhits)

> Gebruik je eigen `.docx` RFP’s: plaats ze onder `examples/` of geef een volledig pad.

***

## 5. AI‑scenario A: Azure OpenAI

> Dit is **optioneel**. Zonder key kun je de extractor volledig gebruiken; AI‑enrichment blijft dan uit.

1.  **Omgevingsvariabelen zetten**

**Windows (PowerShell):**

```powershell
setx AZURE_OPENAI_KEY "<jouw_key>"
setx AZURE_OPENAI_ENDPOINT "https://<jouw-resource>.openai.azure.com/"
```

**macOS/Linux (bash/zsh):**

```bash
export AZURE_OPENAI_KEY="<jouw_key>"
export AZURE_OPENAI_ENDPOINT="https://<jouw-resource>.openai.azure.com/"
```

> Herstart je terminal/VS Code na `setx` (Windows).

2.  **Run met AI:**

```bash
python rfp_extract.py "input.docx" --xlsx out.xlsx --ai on
```

> In de huidige code is AI‑enrichment een **veilige no‑op** als de env vars of client ontbreken.

***

## 6. AI‑scenario B: Lokaal met LLaMA (Ollama)

Wil je **zonder cloud** lokaal AI draaien? Gebruik **Ollama** + **LLaMA**.

### 6.1 Ollama installeren

**Windows:**

1.  Download en installeer via <https://ollama.com/download>
2.  Start **Ollama app** (of service). Dit exposeert een lokale OpenAI‑achtige API op `http://localhost:11434/v1`.

**macOS:**

```bash
brew install ollama
ollama serve
```

**Linux (bijv. Ubuntu):**

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
```

### 6.2 LLaMA model downloaden

Kies een model (bv. `llama3.1`) en pull:

```bash
ollama pull llama3.1
```

> Alternatieven: `llama3.2`, `llama2`, `phi4`, `qwen2.5`, …  
> Hoe groter het model, hoe zwaarder de RAM/VRAM‑vereisten.

### 6.3 AI‑hook activeren voor Ollama

De meegeleverde `ai/ai_hooks.py` is een **placeholder**. Voor lokale LLama via Ollama (OpenAI‑compatibel endpoint) kun je dit mini‑patchje toepassen:

**Stap 1 — Installeer OpenAI‑client (indien nog niet):**

```bash
pip install "openai>=1.12.0"
```

**Stap 2 — Zet deze env vars (lokale API + modelnaam):**

**Windows (PowerShell):**

```powershell
$env:OPENAI_API_KEY="ollama"                    # placeholder; wordt niet gevalideerd
$env:OPENAI_BASE_URL="http://localhost:11434/v1"
$env:LLM_MODEL="llama3.1"                       # of jouw modelnaam
```

**macOS/Linux (bash/zsh):**

```bash
export OPENAI_API_KEY="ollama"
export OPENAI_BASE_URL="http://localhost:11434/v1"
export LLM_MODEL="llama3.1"
```

**Stap 3 — Vervang de inhoud van `ai/ai_hooks.py` door onderstaand (of maak een branch met deze wijziging):**

```python
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
```

**Stap 4 — Draai met AI ingeschakeld:**

```bash
python rfp_extract.py "input.docx" --xlsx out.xlsx --ai on
python rfp_extract.py "examples/*.docx" "examples/*.xlsx" --xlsx out.xlsx --ai on
```

> **Performance tip**: eerste run van een model kan traag zijn (download + warmup).  
> **Privacy tip**: lokaal met Ollama blijft data **on‑device**.

***

## 7. Governance‑mappings beheren

De JSON’s in `governance/` bepalen de keyword→control/practice mapping:

*   `governance/mappings_cobit.json`
*   `governance/mappings_itil.json`
*   `governance/mappings_iso27001.json`

**Formaat:**

```json
{
  "keyword": ["CONTROL_OR_PRACTICE_ID_1", "CONTROL_OR_PRACTICE_ID_2"]
}
```

**Voorbeeld (COBIT):**

```json
{
  "risk": ["APO12"],
  "security": ["APO13", "DSS05"]
}
```

**Uitzondering in `.gitignore`**  
We negeren generieke `*.json` outputs, maar **whitelisten** governance JSON’s en `utils/patterns_shell.json`.  
Zorg dat `.gitignore` deze regels bevat:

```gitignore
*.json
!governance/*.json
!utils/patterns_shell.json
```

***

## 8. Troubleshooting

**A. “The following paths are ignored by one of your .gitignore files”**  
→ `.gitignore` negeert `*.json`. Voeg de uitzonderingen toe (zie §7) of forceer met `git add -f governance/*.json`.

**B. LF/CRLF‑waarschuwing bij `git add`**  
→ Onschuldig. Voeg `.gitattributes` toe om line endings te normaliseren (bijv. `*.py *.json *.md text eol=lf`).

**C. “fatal: not a git repository”**  
→ Je zit niet in de repo‑map. `cd` naar de map met de `.git` folder (de root van het project).

**D. Push faalt: non‑fast‑forward**  
→ `git pull --rebase origin main`, los conflicts op (meestal `README.md`), dan `git push`.

**E. OneDrive locks**  
→ Pauzeer OneDrive tijdens `rebase/merge`, of werk buiten OneDrive (bv. `C:\Dev`).

**F. Ollama draait niet / model niet gevonden**

*   Check service: open <http://localhost:11434/>
*   Pull het model (bv. `ollama pull llama3.1`)
*   Check env vars: `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `LLM_MODEL`

***

## Contact

*   Vragen/suggesties? Open een **Issue** op de repo of contacteer de maintainer.

***

> **Security note:** Deel geen vertrouwelijke RFP’s of klantdata in publieke repos of cloud AI‑diensten. Gebruik **lokale (Ollama)** of **tenant‑beheerste** AI voor gevoelige documenten.
