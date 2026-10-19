# LocalLedger AI

LocalLedger AI is a local-first invoice and receipt organizer for freelancers. It uses Streamlit, Tesseract OCR, PyMuPDF, SQLite, Pandas/Plotly, and a local Qwen2.5 Instruct model served by Ollama. It does not require API keys or call proprietary cloud AI services.

## Architecture

```text
Streamlit UI (app.py)
  ├─ Import: PDF text / Tesseract OCR → local Ollama extraction
  ├─ Review: validate fields, flag uncertainty, save corrections
  ├─ Search and analytics: SQLite → Pandas/Plotly → local CSV download
  └─ Local document store: originals under ~/.localledger/documents/<type>/

localledger/
  config.py       Local paths and Ollama endpoint/model configuration
  ingest.py       SHA-256, PDF text extraction and OCR fallback
  extraction.py   Ollama prompt, JSON parser and conservative validation
  models.py       Structured extraction schema
  storage.py      SQLite persistence and duplicate matching
  analytics.py    Monthly and vendor summaries
tests/            Synthetic sample data and unit tests
```

Ollama is called in `localledger/extraction.py` with a request to `http://127.0.0.1:11434/api/generate`; the endpoint is restricted to localhost so document text cannot be posted to a remote host. The sidebar checks `/api/tags` and shows whether the selected model is installed. Files and database records stay on this computer. Streamlit usage statistics are disabled in `.streamlit/config.toml`; the app loads no remote fonts or analytics. After dependencies and the model are installed, processing works offline as long as Ollama is running.

## Windows installation

1. Install Python 3.10 or later.
2. Install [Tesseract OCR for Windows](https://github.com/UB-Mannheim/tesseract/wiki) and ensure `tesseract.exe` is on PATH. If needed, set `pytesseract.pytesseract.tesseract_cmd` in `localledger/ingest.py` to its installed path.
3. Install [Ollama for Windows](https://ollama.com/download).
4. In PowerShell, from this folder:

   ```powershell
   .\install_windows.ps1
   ollama pull qwen2.5:3b-instruct
   ollama serve
   ```

   In a second PowerShell window, launch the app:

   ```powershell
   .\.venv\Scripts\streamlit.exe run app.py
   ```

   A 7B variant may be selected with `ollama pull qwen2.5:7b-instruct` and `$env:OLLAMA_MODEL='qwen2.5:7b-instruct'` before launching.

5. Visit the local Streamlit URL printed in the terminal (usually `http://localhost:8501`). No AI API key is needed. The default local data directory is `%USERPROFILE%\.localledger`; override with `$env:LOCALLEDGER_HOME='D:\LocalLedgerData'` before launch.

## Use

- Import PDFs or images. Text PDFs are parsed directly; scanned PDFs and images go through local Tesseract OCR.
- Ollama proposes fields and the app flags missing, ambiguous, arithmetic-inconsistent, or text-unverified totals for human review.
- Exact duplicates are skipped by SHA-256. Potential duplicates are marked when vendor, amount, and date or invoice number match.
- Imported originals are kept in hash-prefixed, type-organized folders to avoid filename collisions. The dashboard does not expose deletion.
- Review fields, search by filename/vendor/invoice, inspect monthly and vendor summaries, and export a CSV from Analytics.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Tests use synthetic text records and a temporary SQLite database; they do not require Ollama or real financial data.

## Reliability and limitations

Model output is parsed as JSON and validated before saving. Amount checks use a tolerance for rounding; OCR quality and unusual tax structures can still require human review. Possible-duplicate matching is a review signal, not an automatic merge. SQLite stores metadata and extracted text locally; back up the LocalLedger data directory if you need to preserve the index. Originals are retained even if you later remove database records manually.
