from localledger.models import Extraction
from localledger.storage import connect, find_duplicate, save_document

def test_exact_hash_duplicate_and_metadata(tmp_path):
    conn=connect(tmp_path/"test.db")
    item=Extraction(vendor_name="Shop",total_amount=10,issue_date="2026-03-14")
    save_document(conn,"a.pdf","/docs/a.pdf","hash1","text",item)
    assert find_duplicate(conn,"hash1") is not None
    assert find_duplicate(conn,"hash2",item) is not None
