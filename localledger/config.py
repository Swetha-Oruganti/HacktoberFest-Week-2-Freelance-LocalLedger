from pathlib import Path
import os

APP_DIR = Path(os.getenv("LOCALLEDGER_HOME", Path.home() / ".localledger"))
DOCUMENT_DIR = APP_DIR / "documents"
DB_PATH = APP_DIR / "localledger.sqlite3"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct")

def ensure_dirs() -> None:
    DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)
