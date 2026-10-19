from localledger.analytics import documents_frame, monthly_summary, vendor_summary

def test_monthly_and_vendor_summaries():
    df=documents_frame([{"id":1,"original_name":"a.pdf","extraction":{"vendor_name":"Shop","issue_date":"2026-03-14","total_amount":10}},{"id":2,"original_name":"b.pdf","extraction":{"vendor_name":"Shop","issue_date":"2026-03-20","total_amount":5}}])
    assert monthly_summary(df).iloc[0]["total_amount"] == 15
    assert vendor_summary(df).iloc[0]["total_amount"] == 15
