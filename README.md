# RFP Extractor Extended

**AI‑assisted extractor** for multi‑document RFPs that produces structured requirements and governance mappings:

*   **Hybrid requirement detection** (rules + semantic embeddings)
*   **Semantic governance mapping** to **COBIT / ITIL / ISO 27001** with confidence + optional LLM explanation
*   **Document role detection** (RFP\_MAIN, SOW, Annex D, Pricing, Legal)
*   **Human‑in‑the‑loop UI** (Streamlit review & export)

Runs locally with **Ollama** for **embeddings** and, optionally, **LLM explanations**.  
*(This README replaces the previous one; we now target Python 3.12 and a lightweight chat model for stability and low RAM use.)* [\[cegekagrou...epoint.com\]](https://cegekagroup-my.sharepoint.com/personal/koen_goos_cegeka_com1/Documents/Microsoft%20Copilot%20Chat%20Files/README.md)

***

## 1) Prerequisites

*   **Windows 11** with **Python 3.12.x** (official python.org installer — *not* Microsoft Store).  
    During install: **Add Python to PATH**, **Install for all users**, **Disable path length limit**.
*   **Ollama** running locally at `http://127.0.0.1:11434`
    *   **Embedding model (default):** `nomic-embed-text`
    *   **Recommended chat model:** `qwen2.5:3b-instruct` (light & fast; good for short governance explanations)
*   **PowerShell**: if `.ps1` activation is blocked, use `activate.bat` or temporarily:
    ```powershell
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    ```

***

## 2) Setup

From the repo root:

```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # or: & ".\.venv\Scripts\activate.bat"

# Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Pull Ollama models (once):

```powershell
ollama pull nomic-embed-text
ollama pull qwen2.5:3b-instruct
```

***

## 3) Running the extractor (multi‑file)

Drop your **.docx** and **.xlsx** into a folder (e.g., `examples/`) and run:

```powershell
# RAM‑friendly LLM defaults
$env:OLLAMA_CHAT_MODEL="qwen2.5:3b-instruct"
$env:OLLAMA_CHAT_TIMEOUT="10"
$env:OLLAMA_NUM_CTX="512"
$env:OLLAMA_NUM_PREDICT="96"

# (Optional) enable LLM explanations in the Excel output (column governance_explanation)
$env:GOV_EXPLAIN="1"

python rfp_extract.py examples/ --xlsx out.xlsx --ai on
```

**Output:** `out.xlsx` with tabs **BR**, **FR**, **NFR**, **RISKS**, **SCOPE\_IN**, **SCOPE\_OUT**, **SCOPE\_OTHER**, **ALL**.  
If explanations are off you’ll see the placeholder `Explanation disabled (GOV_EXPLAIN=0).` in the explanation column. [\[cegekagrou...epoint.com\]](https://cegekagroup-my.sharepoint.com/personal/koen_goos_cegeka_com1/Documents/Microsoft%20Copilot%20Chat%20Files/README.md)

> **Override models (one‑off):**
>
> ```powershell
> python rfp_extract.py examples/ --xlsx out.xlsx --embed-model nomic-embed-text --chat-model "qwen2.5:3b-instruct"
> ```

***

## 4) What the extractor does

*   **Multi‑file ingest**: reads all **.docx** and **.xlsx** from provided paths/folders.
*   **Document roles** (auto‑detected):
    *   `REQ_ANNEX` → Annex D / explicit requirements
    *   `SOW` → Statement of Work
    *   `PRICING` → skipped
    *   `LEGAL` → skipped
    *   `RFP_MAIN` / `GENERIC` → normal ingestion
*   **Strict requirement gate**:
    *   **Rule score** (length, punctuation, modal/action verb) + **Semantic score** (embeddings); **hybrid** threshold
    *   Rejects headings/labels and **legal/address boilerplate** (e.g., `vzw/asbl`, `nv/sa`, “registered office at…”, BE postcodes, straat/laan/chaussée/…)
    *   **Stricter threshold** for **BR** from **RFP\_MAIN** (business context rarely maps directly)
*   **Governance mapping**:
    *   Only for texts with **governance cues**: `sla`, `service level`, `incident`, `change`, `security`, `access control`, `monitoring`, `continuity`, `compliance`, `risk`, `availability`, `response time`, …
    *   **Cosine similarity** against COBIT/ITIL/ISO control texts (configurable min similarity)
    *   Produces `cobit`, `itil`, `iso27001`, and `governance_confidence` (mean similarity)
    *   Optional **LLM explanation** (short rationale) with **fail‑safe** timeout and fallback

***

## 5) LLM explanations (governance\_explanation column)

Enable/disable per current shell:

```powershell
# on
$env:GOV_EXPLAIN="1"
# off (no chat calls; writes placeholder)
$env:GOV_EXPLAIN="0"
```

**Reduce LLM load**:

```powershell
# Explain only top-K rows by confidence
$env:GOV_EXPLAIN_TOPK="150"

# Or: only when confidence ≥ threshold
$env:GOV_EXPLAIN_MINCONF="0.60"
```

If the chat model is slow or not responding within timeout, a **concise fallback** explanation is written instead of hanging.

***

## 6) Environment variables (quick reference)

**Ollama / LLM:**

*   `OLLAMA_EMBED_MODEL` (default `nomic-embed-text`)
*   `OLLAMA_CHAT_MODEL` (recommend `qwen2.5:3b-instruct`)
*   `OLLAMA_CHAT_TIMEOUT` (default `10`)
*   `OLLAMA_NUM_CTX` (default `512`)
*   `OLLAMA_NUM_PREDICT` (default `128`)
*   `OLLAMA_KEEP_ALIVE` (e.g. `15s` to release models quickly when idle)

**Governance mapping:**

*   `GOV_MIN_SIM` (default `0.55`) → raise to `0.60` for stricter mappings
*   `GOV_EXPLAIN` (`1`/`0`) → enable/disable explanations
*   `GOV_EXPLAIN_TOPK` → explain only top‑K items
*   `GOV_EXPLAIN_MINCONF` → explain only above a confidence threshold

> **PowerShell tip:** `setx NAME VALUE` is **persistent** but only applies to **new shells**.  
> For the **current** shell, use `$env:NAME="VALUE"` before running Python.

***

## 7) RAM‑friendly defaults (16 GB laptops)

*   Chat model: **`qwen2.5:3b-instruct`** (or `mistral:latest`)
*   `OLLAMA_NUM_CTX=512`, `OLLAMA_NUM_PREDICT=96–128`, `OLLAMA_CHAT_TIMEOUT=10`
*   Embeddings cached as **float32**
*   Prefer **Top‑K** or **MINCONF** explanations to cap LLM calls

***

## 8) Human‑in‑the‑loop review UI

Start the UI:

```powershell
streamlit run ui/review.py
```

Upload `out.xlsx`, adjust **type/text/confidence/explanations**, and export **`reviewed.xlsx`**.

***

## 9) Troubleshooting (Windows 11 / OneDrive / PowerShell)

*   **Venv activation blocked**  
    Use `& ".\.venv\Scripts\activate.bat"` or:
    ```powershell
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    .\.venv\Scripts\Activate.ps1
    ```
*   **`python` not found or opens the Store**  
    Disable **App execution aliases** for `python.exe` / `python3.exe`, install Python 3.12 from python.org.
*   **Packages missing** (`requests`, `numpy`, `openpyxl`)  
    Ensure venv is active, then:
    ```powershell
    python -m pip install -r requirements.txt
    ```
*   **Chat timeouts/hangs**  
    Use a lighter model (`qwen2.5:3b-instruct`), keep `OLLAMA_CHAT_TIMEOUT=10`, confirm models:
    ```powershell
    ollama list
    curl http://127.0.0.1:11434/api/tags
    ```
*   **Explanation still shows “Explanation disabled…”**  
    Set:
    ```powershell
    $env:GOV_EXPLAIN="1"
    ```
    *(Remember: `setx` needs a new shell; `$env:` affects the current shell immediately.)*

***

## 10) Notes

*   Control embeddings are cached at `ai/embeddings/controls_embeddings.pkl` on first run for speed. [\[cegekagrou...epoint.com\]](https://cegekagroup-my.sharepoint.com/personal/koen_goos_cegeka_com1/Documents/Microsoft%20Copilot%20Chat%20Files/README.md)
*   Role handling summary:
    *   `REQ_ANNEX` → Annex D / explicit requirements
    *   `PRICING` → skipped
    *   `LEGAL` → skipped
    *   `SOW` → functional leaning
    *   `RFP_MAIN` / `GENERIC` → normal [\[cegekagrou...epoint.com\]](https://cegekagroup-my.sharepoint.com/personal/koen_goos_cegeka_com1/Documents/Microsoft%20Copilot%20Chat%20Files/README.md)

***

## 11) Example — one‑shot run (copy/paste)

```powershell
# Activate venv
.\.venv\Scripts\Activate.ps1

# LLM & mapping settings
$env:OLLAMA_CHAT_MODEL="qwen2.5:3b-instruct"
$env:OLLAMA_CHAT_TIMEOUT="10"
$env:OLLAMA_NUM_CTX="512"
$env:OLLAMA_NUM_PREDICT="96"
$env:GOV_EXPLAIN="1"
$env:GOV_MIN_SIM="0.60"
$env:GOV_EXPLAIN_TOPK="150"   # optional

# Run extractor
python rfp_extract.py examples/ --xlsx out.xlsx --ai on

