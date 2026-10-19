import json
import re
from urllib.parse import urlparse
from datetime import date
from typing import Any
import requests
from .config import OLLAMA_MODEL, OLLAMA_URL
from .models import DOCUMENT_TYPES, PAYMENT_STATUSES, Extraction

FIELDS = ("document_type", "vendor_name", "invoice_number", "issue_date", "due_date", "currency", "subtotal", "tax", "total_amount", "payment_status", "expense_category", "confidence", "review_flags")

def check_ollama(model: str = OLLAMA_MODEL, base_url: str = OLLAMA_URL, timeout: int = 2) -> tuple[bool, bool, str]:
    """Return (reachable, model_available, display message) for the local Ollama server."""
    if urlparse(base_url).hostname not in {"localhost", "127.0.0.1", "::1"}:
        return False, False, "Ollama URL must point to this computer (localhost)."
    try:
        response = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=timeout)
        response.raise_for_status()
        models = response.json().get("models", [])
        names = {str(item.get("name", "")) for item in models}
        available = model in names or any(name.split(":", 1)[0] == model.split(":", 1)[0] and name == model for name in names)
        return True, available, "Model ready" if available else f"Ollama is running, but {model} is not installed."
    except requests.RequestException:
        return False, False, "Ollama is not responding at the local address."
    except (ValueError, TypeError):
        return False, False, "Ollama returned an unexpected response."

def _parse_json(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I)
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            raise ValueError("Model did not return a JSON object")
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("Model response must be a JSON object")
    return value

def validate_extraction(value: dict[str, Any], source_text: str = "") -> Extraction:
    data = {k: value.get(k) for k in FIELDS}
    flags = list(data.get("review_flags") or [])
    if data["document_type"] is None: data["document_type"] = "unknown"
    if data["document_type"] not in DOCUMENT_TYPES:
        data["document_type"] = "unknown"; flags.append("Unrecognized document type")
    if data["payment_status"] is None: data["payment_status"] = "unknown"
    if data["payment_status"] not in PAYMENT_STATUSES:
        data["payment_status"] = "unknown"; flags.append("Unrecognized payment status")
    for key in ("subtotal", "tax", "total_amount"):
        number = data[key]
        if number in (None, ""):
            data[key] = None
        else:
            try:
                data[key] = float(str(number).replace(",", ""))
                if data[key] < 0: raise ValueError
            except (ValueError, TypeError):
                data[key] = None; flags.append(f"Invalid {key.replace('_', ' ')}")
    for key in ("issue_date", "due_date"):
        val = data[key]
        if val in (None, ""): data[key] = None
        else:
            try:
                date.fromisoformat(str(val)); data[key] = str(val)
            except ValueError:
                data[key] = None; flags.append(f"Ambiguous {key.replace('_', ' ')}")
    for key in ("vendor_name", "invoice_number", "currency", "expense_category"):
        data[key] = str(data[key]).strip() if data[key] not in (None, "") else None
    if data["confidence"] not in ("high", "medium", "low"): data["confidence"] = "low"
    if data["total_amount"] is None: flags.append("Total amount missing or unclear")
    if data["vendor_name"] is None: flags.append("Vendor name missing or unclear")
    if data["subtotal"] is not None and data["tax"] is not None and data["total_amount"] is not None:
        if abs(data["subtotal"] + data["tax"] - data["total_amount"]) > max(0.02, abs(data["total_amount"]) * 0.005):
            flags.append("Subtotal plus tax does not match total")
    if source_text and data["total_amount"] is not None:
        compact = f"{data['total_amount']:.2f}"
        integer = str(int(data["total_amount"])) if data["total_amount"].is_integer() else None
        if compact not in source_text.replace(",", "") and (integer is None or not re.search(rf"(?<!\d){integer}(?!\d)", source_text.replace(",", ""))):
            flags.append("Extracted total not found verbatim in document text")
    data["review_flags"] = list(dict.fromkeys(str(x) for x in flags if x))
    return Extraction.from_dict(data)

def extract_with_ollama(text: str, model: str = OLLAMA_MODEL, base_url: str = OLLAMA_URL, timeout: int = 120) -> Extraction:
    if not text.strip():
        return validate_extraction({}, text)
    if urlparse(base_url).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("For privacy, Ollama must use a loopback URL on this computer")
    prompt = ("Extract financial fields from the supplied document text. Do not infer or invent; use null for missing/unclear values. "
        "Return only a JSON object with keys: document_type (invoice, receipt, expense_bill, other_financial_document, unknown), "
        "vendor_name, invoice_number, issue_date and due_date (ISO YYYY-MM-DD or null), currency (ISO code when clear), "
        "subtotal, tax, total_amount (numbers or null), payment_status (paid, unpaid, partially_paid, overdue, unknown), "
        "expense_category, confidence (high/medium/low), review_flags (array of strings).\nDOCUMENT TEXT:\n" + text[:20000])
    response = requests.post(f"{base_url.rstrip('/')}/api/generate", json={"model": model, "prompt": prompt, "stream": False, "format": "json", "options": {"temperature": 0}}, timeout=timeout)
    response.raise_for_status()
    body = response.json()
    return validate_extraction(_parse_json(body.get("response", "")), text)
