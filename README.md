
# RFP Extractor Extended (Python 3.13 + Ollama LLM)

This package adds **semantic requirement classification**, **semantic governance mapping**, **document role detection**, and a **human‑in‑the‑loop UI** to your existing extractor. It uses **Ollama** locally for both **embeddings** and **LLM explanations**.

## Prereqs
- Python 3.13
- Ollama running locally (http://127.0.0.1:11434)
  - Embedding model (default): `nomic-embed-text`
  - Chat model (default): `llama3.1`

## Setup
```powershell

python -m venv .venv
.\.venv\Scripts\Activate.ps1  # or .\.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run extractor (multi-file)
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
$env:GOV_EXPLAIN="1"
python rfp_extract.py examples/ --xlsx out.xlsx --ai on --chat-model "qwen2.5:3b-instruct"
```

Override models (optional):
```powershell
python rfp_extract.py examples/ --xlsx out.xlsx --embed-model nomic-embed-text --chat-model llama3
```

## Run review UI
```powershell
streamlit run ui/review.py
```

## Notes
- Controls embeddings are cached at `ai/embeddings/controls_embeddings.pkl` on first run.
- Document roles:
  - `REQ_ANNEX` → Annex D / explicit requirements
  - `PRICING` → skipped
  - `LEGAL` → skipped
  - `SOW` → functional leaning
  - `RFP_MAIN`/`GENERIC` → normal
