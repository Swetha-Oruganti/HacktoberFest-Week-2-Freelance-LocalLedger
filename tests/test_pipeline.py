from pathlib import Path
from localledger.models import Extraction
from localledger.pipeline import process_document
from localledger.storage import connect, list_documents

def test_import_saves_original_and_fields_with_local_extractor(tmp_path):
    conn=connect(":memory:")
    result=process_document("sample.pdf",b"synthetic original",conn,document_dir=tmp_path/"documents",
        ocr=lambda _: "Total 108.00",
        extractor=lambda _: Extraction(document_type="invoice",vendor_name="Northwind",total_amount=108))
    assert result["status"] == "saved"
    assert Path(result["path"]).read_bytes() == b"synthetic original"
    assert list_documents(conn)[0]["extraction"]["vendor_name"] == "Northwind"

def test_import_survives_offline_ollama_and_flags_review(tmp_path):
    conn=connect(":memory:")
    result=process_document("sample.pdf",b"synthetic original",conn,document_dir=tmp_path/"documents",
        ocr=lambda _: "Receipt total 12.00",
        extractor=lambda _: (_ for _ in ()).throw(ConnectionError("local Ollama is offline")))
    assert result["status"] == "saved"
    flags=list_documents(conn)[0]["extraction"]["review_flags"]
    assert any("Ollama extraction unavailable" in flag for flag in flags)
    assert Path(result["path"]).exists()

def test_exact_duplicate_is_skipped(tmp_path):
    conn=connect(":memory:")
    process_document("one.pdf",b"same bytes",conn,document_dir=tmp_path/"documents",ocr=lambda _: "",extractor=lambda _: Extraction())
    result=process_document("two.pdf",b"same bytes",conn,document_dir=tmp_path/"documents",ocr=lambda _: "",extractor=lambda _: Extraction())
    assert result["status"] == "duplicate"
