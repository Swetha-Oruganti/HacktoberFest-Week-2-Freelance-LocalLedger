import json
import sqlite3
from pathlib import Path
from .models import Extraction

def connect(db_path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("""CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY, original_name TEXT NOT NULL, stored_path TEXT NOT NULL,
        sha256 TEXT NOT NULL, text_content TEXT NOT NULL DEFAULT '', extraction_json TEXT NOT NULL DEFAULT '{}',
        imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(sha256))""")
    return conn

def find_duplicate(conn: sqlite3.Connection, digest: str, extraction: Extraction | None = None) -> sqlite3.Row | None:
    row = conn.execute("SELECT * FROM documents WHERE sha256=?", (digest,)).fetchone()
    if row or extraction is None: return row
    candidates = conn.execute("SELECT * FROM documents").fetchall()
    for candidate in candidates:
        try: other = Extraction.from_dict(json.loads(candidate["extraction_json"]))
        except (ValueError, TypeError): continue
        same_vendor = extraction.vendor_name and other.vendor_name and extraction.vendor_name.casefold() == other.vendor_name.casefold()
        same_total = extraction.total_amount is not None and extraction.total_amount == other.total_amount
        same_date = extraction.issue_date and extraction.issue_date == other.issue_date
        same_invoice = extraction.invoice_number and extraction.invoice_number == other.invoice_number
        if same_vendor and same_total and (same_date or same_invoice): return candidate
    return None

def save_document(conn: sqlite3.Connection, original_name: str, stored_path: str, digest: str, text: str, extraction: Extraction) -> int:
    cur = conn.execute("INSERT INTO documents(original_name,stored_path,sha256,text_content,extraction_json) VALUES(?,?,?,?,?)",
        (original_name, stored_path, digest, text, json.dumps(extraction.to_dict(), ensure_ascii=False)))
    conn.commit()
    return int(cur.lastrowid)

def list_documents(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM documents ORDER BY imported_at DESC").fetchall()
    out=[]
    for row in rows:
        item=dict(row); item["extraction"]=json.loads(item.pop("extraction_json")); out.append(item)
    return out

def update_extraction(conn: sqlite3.Connection, doc_id: int, extraction: Extraction) -> None:
    conn.execute("UPDATE documents SET extraction_json=? WHERE id=?", (json.dumps(extraction.to_dict(), ensure_ascii=False), doc_id)); conn.commit()

def delete_document(conn: sqlite3.Connection, doc_id: int) -> None:
    """Delete metadata only; caller must explicitly confirm and decide about the preserved original."""
    conn.execute("DELETE FROM documents WHERE id=?", (doc_id,)); conn.commit()
