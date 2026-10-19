from pathlib import Path
import hashlib

SUPPORTED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        import fitz
        import pytesseract
        from PIL import Image
        import io
        pages = []
        with fitz.open(path) as doc:
            for page in doc:
                text = page.get_text("text").strip()
                if len(text) < 30:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    text = pytesseract.image_to_string(Image.open(io.BytesIO(pix.tobytes("png"))))
                pages.append(text)
        return "\n".join(pages).strip()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported document type: {suffix}")
    import pytesseract
    from PIL import Image
    return pytesseract.image_to_string(Image.open(path)).strip()
