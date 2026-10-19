from pathlib import Path
from localledger.extraction import _parse_json, validate_extraction

def test_json_extraction_is_validated_and_total_verified():
    text=Path("tests/fixtures/sample_invoice.txt").read_text()
    result=validate_extraction({"document_type":"invoice","vendor_name":"Northwind Studio Supplies","invoice_number":"NW-2026-0042","issue_date":"2026-03-14","due_date":"2026-04-13","currency":"USD","subtotal":"100.00","tax":"8.00","total_amount":"108.00","payment_status":"unpaid","confidence":"high","review_flags":[]},text)
    assert result.total_amount == 108.0
    assert not result.review_flags

def test_bad_amount_and_mismatch_are_flagged():
    result=validate_extraction({"document_type":"receipt","vendor_name":"Shop","subtotal":"oops","tax":3,"total_amount":12,"issue_date":"14/03/26"},"Total 12")
    assert result.subtotal is None
    assert any("Invalid subtotal" in x for x in result.review_flags)
    assert any("Ambiguous issue date" in x for x in result.review_flags)
    assert any("does not match" in x for x in result.review_flags)

def test_json_parser_accepts_json_fence():
    assert _parse_json('```json\n{"total_amount": 2}\n```')["total_amount"] == 2
