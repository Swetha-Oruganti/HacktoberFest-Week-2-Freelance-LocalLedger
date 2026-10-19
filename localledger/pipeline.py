"""Document import orchestration, separated from the Streamlit interface."""
from pathlib import Path
import shutil
import tempfile
from typing import Callable

from .config import DOCUMENT_DIR
from .extraction import extract_with_ollama, validate_extraction
from .ingest import extract_text, sha256_file
from .models import Extraction
from .storage import find_duplicate, save_document

def process_document(original_name: str, content: bytes, conn, *,
                     document_dir: Path = DOCUMENT_DIR,
                     ocr: Callable[[Path], str] = extract_text,
                     extractor: Callable[[str], Extraction] = extract_with_ollama) -> dict:
    """Preserve and index an upload even if OCR or the local model needs review."""
    suffix = Path(original_name).suffix.lower()
    document_dir = Path(document_dir)
    document_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix="incoming_", suffix=suffix, dir=document_dir.parent, delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    try:
        digest = sha256_file(temp_path)
        exact = find_duplicate(conn, digest)
        if exact:
            return {"status": "duplicate", "duplicate_of": exact["original_name"], "sha256": digest}

        text = ""
        extraction = Extraction()
        try:
            text = ocr(temp_path)
            if not text.strip():
                extraction.review_flags.append("No readable text found; check OCR language, image quality, or scanned page orientation")
            else:
                try:
                    extraction = extractor(text)
                except Exception as error:
                    extraction = validate_extraction({}, text)
                    extraction.review_flags.append(f"Ollama extraction unavailable: {error}")
        except Exception as error:
            extraction.review_flags.append(f"Text extraction failed: {error}")

        possible = find_duplicate(conn, digest, extraction)
        if possible:
            extraction.review_flags.append(f"Possible duplicate of {possible['original_name']} (vendor/amount/date or invoice number match)")
        category = extraction.document_type if extraction.document_type != "unknown" else "needs_review"
        destination_dir = document_dir / category
        destination_dir.mkdir(parents=True, exist_ok=True)
        base_name = Path(original_name).name
        destination = destination_dir / f"{digest[:12]}_{base_name}"
        suffix = 1
        while destination.exists():
            destination = destination_dir / f"{digest[:12]}_{suffix}_{base_name}"
            suffix += 1
        shutil.copy2(temp_path, destination)
        doc_id = save_document(conn, original_name, str(destination), digest, text, extraction)
        return {"status": "saved", "id": doc_id, "path": str(destination), "text": text, "extraction": extraction}
    finally:
        temp_path.unlink(missing_ok=True)
