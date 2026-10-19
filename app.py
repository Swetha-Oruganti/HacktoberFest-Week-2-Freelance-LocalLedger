import os
os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")

import pandas as pd
import plotly.express as px
import streamlit as st

from localledger.analytics import documents_frame, monthly_summary, vendor_summary
from localledger.config import APP_DIR, DB_PATH, OLLAMA_MODEL, OLLAMA_URL, ensure_dirs
from localledger.extraction import check_ollama, validate_extraction
from localledger.ingest import SUPPORTED_SUFFIXES
from localledger.models import DOCUMENT_TYPES
from localledger.pipeline import process_document
from localledger.storage import connect, list_documents, update_extraction

st.set_page_config(page_title="LocalLedger AI", page_icon="◈", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
:root { --ink:#172521; --muted:#71807a; --green:#147d63; --soft:#eaf4ef; --line:#e5ebe7; }
.stApp { background:#f6f8f6; color:var(--ink); font-family:Inter,'Segoe UI',sans-serif; }
[data-testid="stSidebar"] { background:#f0f4f1; border-right:1px solid #e0e8e2; }
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3 { font-family:'Manrope',sans-serif; }
h1,h2,h3 { font-family:Inter,'Segoe UI',sans-serif !important; letter-spacing:-.035em; color:#172521; }
[data-testid="stMetric"] { background:white; border:1px solid var(--line); border-radius:16px; padding:18px 20px; box-shadow:0 3px 16px #233c2a08; }
[data-testid="stMetricLabel"] p { color:#71807a; font-size:.82rem; }
[data-testid="stMetricValue"] { color:#172521; }
.hero { background:linear-gradient(120deg,#113e32,#176d55 66%,#23916d); border-radius:22px; padding:30px 34px; color:white; margin:4px 0 24px; box-shadow:0 15px 40px #174c3524; }
.hero h1 { color:white !important; margin:0 0 7px; font-size:2.1rem; }
.hero p { color:#d3e9de; margin:0; font-size:1.02rem; }
.eyebrow { color:#9ddac0; font-size:.75rem; font-weight:700; text-transform:uppercase; letter-spacing:.12em; margin-bottom:8px; }
.section-kicker { color:#71807a; font-size:.76rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; }
.info-card { background:white; border:1px solid var(--line); border-radius:16px; padding:19px 21px; height:100%; }
.info-card h3 { font-size:1rem; margin:0 0 7px; }
.info-card p { color:#71807a; font-size:.9rem; margin:0; line-height:1.55; }
.status-ready { color:#157357; background:#e8f5ee; border:1px solid #cce8d9; padding:10px 13px; border-radius:12px; font-weight:600; }
.status-warn { color:#855d12; background:#fbf4e3; border:1px solid #f0dfb6; padding:10px 13px; border-radius:12px; font-weight:600; }
div.stButton > button[kind="primary"] { background:#147d63; border-color:#147d63; border-radius:10px; font-weight:700; }
div.stButton > button { border-radius:10px; }
[data-testid="stFileUploader"] { background:white; border:1px dashed #b5c9bc; border-radius:16px; padding:12px; }
[data-testid="stExpander"] { background:white; border:1px solid var(--line); border-radius:13px; }
</style>
""", unsafe_allow_html=True)

ensure_dirs()
conn = connect(DB_PATH)
ollama_online, model_ready, ollama_message = check_ollama()

with st.sidebar:
    st.markdown("<h2 style='margin-bottom:0'>◈ LocalLedger</h2><div style='color:#71807a;margin:0 0 22px'>Private finance workspace</div>", unsafe_allow_html=True)
    section = st.radio("WORKSPACE", ["Overview", "Import", "Review", "Analytics"], label_visibility="visible")
    st.divider()
    st.markdown("<div class='section-kicker'>LOCAL AI ENGINE</div>", unsafe_allow_html=True)
    st.caption(f"Ollama · `{OLLAMA_MODEL}`")
    st.caption(f"Endpoint · `{OLLAMA_URL}`")
    if model_ready:
        st.markdown("<div class='status-ready'>● &nbsp;Ollama model ready</div>", unsafe_allow_html=True)
    elif ollama_online:
        st.markdown(f"<div class='status-warn'>● &nbsp;{ollama_message}</div>", unsafe_allow_html=True)
        st.code(f"ollama pull {OLLAMA_MODEL}", language="powershell")
    else:
        st.markdown("<div class='status-warn'>● &nbsp;Ollama is offline</div>", unsafe_allow_html=True)
        st.caption("Start Ollama with `ollama serve`. Extraction will be saved for review if the model is unavailable.")
    st.divider()
    st.caption(f"Local data folder\n`{APP_DIR}`")
    st.caption("Documents are sent only to Ollama on this computer. No cloud AI keys or APIs.")

records = list_documents(conn)
df = documents_frame(records)

def import_files(uploads):
    progress = st.progress(0, text="Preparing local import…")
    for index, upload in enumerate(uploads):
        try:
            result = process_document(upload.name, upload.getvalue(), conn)
            if result["status"] == "duplicate":
                st.info(f"**{upload.name}** is already in your library as **{result['duplicate_of']}**; skipped.")
                continue
            extraction = result["extraction"]
            if extraction.review_flags:
                st.warning(f"**{upload.name}** saved as record {result['id']}; review needed: " + " · ".join(extraction.review_flags))
            else:
                st.success(f"**{upload.name}** imported and extracted (record {result['id']}).")
        except Exception as error:
            st.error(f"Could not import **{upload.name}**: {error}")
        finally:
            progress.progress((index + 1) / len(uploads), text=f"Processed {index + 1} of {len(uploads)} files")
    st.success("Import finished. Originals are preserved in your local documents folder.")

if section == "Overview":
    st.markdown("<div class='hero'><div class='eyebrow'>YOUR FINANCES, ON YOUR DEVICE</div><h1>A clearer view of your paperwork.</h1><p>Organize invoices and receipts with AI that runs locally on your computer.</p></div>", unsafe_allow_html=True)
    total = pd.to_numeric(df.get("total_amount", pd.Series(dtype=float)), errors="coerce").fillna(0).sum() if not df.empty else 0
    review_count = sum(bool(item["extraction"].get("review_flags")) for item in records)
    a, b, c = st.columns(3)
    a.metric("Documents organized", len(records))
    b.metric("Recorded spending", f"{total:,.2f}")
    c.metric("Need your review", review_count)
    st.write("")
    left, right = st.columns([1.35, 1])
    with left:
        st.subheader("Monthly activity")
        monthly = monthly_summary(df)
        if not monthly.empty:
            fig = px.bar(monthly, x="month", y="total_amount", labels={"month":"Month", "total_amount":"Amount"}, color_discrete_sequence=["#168064"])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=4,r=4,t=8,b=4), xaxis_title=None, yaxis_title=None, font_color="#66766e")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown("<div class='info-card'><h3>Your activity will appear here</h3><p>Import a receipt or invoice to start building a monthly view.</p></div>", unsafe_allow_html=True)
    with right:
        st.subheader("Getting started")
        st.markdown("<div class='info-card'><h3>01 · Add your documents</h3><p>Upload a PDF, receipt photo, or scanned bill. Originals stay on this device.</p></div>", unsafe_allow_html=True)
        st.write("")
        st.markdown("<div class='info-card'><h3>02 · Let local AI read them</h3><p>Ollama runs Qwen2.5 on your computer. Review flagged details before relying on them.</p></div>", unsafe_allow_html=True)
    if records:
        st.subheader("Recently added")
        latest = documents_frame(records).head(6)
        show = [col for col in ["original_name","document_type","vendor_name","issue_date","currency","total_amount"] if col in latest]
        st.dataframe(latest[show], hide_index=True, use_container_width=True)
    if not model_ready:
        st.info("**Local AI setup:** Install Ollama, run `ollama pull " + OLLAMA_MODEL + "`, then start `ollama serve`. You can still import files now; they will be saved for review if AI is offline.")

elif section == "Import":
    st.markdown("<div class='eyebrow' style='color:#147d63'>DOCUMENT INTAKE</div>", unsafe_allow_html=True)
    st.title("Import documents")
    st.write("Upload invoices, receipts, and expense bills. Text PDFs are read directly; scanned documents use Tesseract OCR.")
    if model_ready:
        st.success(f"Ollama is ready · `{OLLAMA_MODEL}` · extraction will run locally.")
    else:
        st.warning(f"{ollama_message} Files can still be imported and saved for review; AI fields will need a retry after Ollama starts.")
    st.markdown("<div class='info-card'><h3>Local processing path</h3><p>Document → PyMuPDF/Tesseract → <b>Ollama + Qwen2.5 on localhost</b> → validated fields → your review. No cloud AI service is called.</p></div>", unsafe_allow_html=True)
    st.write("")
    uploads = st.file_uploader("Drop files here or browse", type=[suffix[1:] for suffix in SUPPORTED_SUFFIXES], accept_multiple_files=True, help="PDF, PNG, JPG, TIFF, BMP")
    if uploads:
        st.caption(f"{len(uploads)} file(s) selected · originals will be copied to your local document library")
        if st.button("Import and extract", type="primary", use_container_width=True):
            import_files(uploads)

elif section == "Review":
    st.markdown("<div class='eyebrow' style='color:#147d63'>HUMAN IN THE LOOP</div>", unsafe_allow_html=True)
    st.title("Review your documents")
    st.write("Check uncertain fields, correct details, and save your changes.")
    query = st.text_input("Search by vendor, invoice number, or filename", placeholder="e.g. Northwind or INV-102")
    kind = st.selectbox("Document type", ["All types", *DOCUMENT_TYPES])
    for record in records:
        ex = record["extraction"]
        searchable = " ".join([record["original_name"], str(ex.get("vendor_name") or ""), str(ex.get("invoice_number") or "")]).casefold()
        if query and query.casefold() not in searchable: continue
        if kind != "All types" and ex.get("document_type") != kind: continue
        title_amount = f"{ex.get('currency') or ''} {ex.get('total_amount'):.2f}" if isinstance(ex.get("total_amount"),(float,int)) else "Amount pending"
        with st.expander(f"{ex.get('vendor_name') or 'Unknown vendor'}  ·  {title_amount}  ·  {record['original_name']}"):
            if ex.get("review_flags"):
                for flag in ex["review_flags"]: st.warning(flag)
            if model_ready and record.get("text_content") and st.button("Retry extraction with local Ollama", key=f"retry-{record['id']}"):
                try:
                    from localledger.extraction import extract_with_ollama
                    refreshed = extract_with_ollama(record["text_content"])
                    update_extraction(conn, record["id"], refreshed)
                    st.success("Ollama extraction complete. Review the refreshed fields below.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Local Ollama extraction failed: {error}")
            with st.form(f"review-{record['id']}"):
                c1,c2,c3 = st.columns(3)
                type_opts=list(DOCUMENT_TYPES)
                doc_type=c1.selectbox("Document type",type_opts,index=type_opts.index(ex.get("document_type")) if ex.get("document_type") in type_opts else 0,key=f"kind-{record['id']}")
                vendor=c2.text_input("Vendor",ex.get("vendor_name") or "",key=f"vendor-{record['id']}")
                invoice=c3.text_input("Invoice / receipt number",ex.get("invoice_number") or "",key=f"invoice-{record['id']}")
                date1,date2,date3=st.columns(3)
                issue=date1.text_input("Issue date (YYYY-MM-DD)",ex.get("issue_date") or "",key=f"issue-{record['id']}")
                due=date2.text_input("Due date (YYYY-MM-DD)",ex.get("due_date") or "",key=f"due-{record['id']}")
                currency=date3.text_input("Currency",ex.get("currency") or "",key=f"currency-{record['id']}")
                m1,m2,m3=st.columns(3)
                def amount_field(label, key):
                    value=ex.get(key)
                    return st.text_input(label,"" if value is None else str(value),key=f"{key}-{record['id']}")
                subtotal=amount_field("Subtotal", "subtotal")
                tax=amount_field("Tax", "tax")
                total_amount=amount_field("Total amount", "total_amount")
                pay_opts=["paid","unpaid","partially_paid","overdue","unknown"]
                payment=date1.selectbox("Payment status",pay_opts,index=pay_opts.index(ex.get("payment_status")) if ex.get("payment_status") in pay_opts else 4,key=f"payment-{record['id']}")
                category=date2.text_input("Expense category",ex.get("expense_category") or "",key=f"category-{record['id']}")
                flags=date3.text_area("Review flags (one per line)","\n".join(ex.get("review_flags") or []),key=f"flags-{record['id']}",height=90)
                if st.form_submit_button("Save reviewed details",type="primary"):
                    def parse_amount(raw, label):
                        if not raw.strip(): return None
                        try: return float(raw.replace(",",""))
                        except ValueError: raise ValueError(f"{label} must be a number or left blank")
                    try:
                        edited={"document_type":doc_type,"vendor_name":vendor or None,"invoice_number":invoice or None,"issue_date":issue or None,"due_date":due or None,"currency":currency or None,"subtotal":parse_amount(subtotal,"Subtotal"),"tax":parse_amount(tax,"Tax"),"total_amount":parse_amount(total_amount,"Total amount"),"payment_status":payment,"expense_category":category or None,"confidence":ex.get("confidence","low"),"review_flags":[line.strip() for line in flags.splitlines() if line.strip()]}
                        cleaned=validate_extraction(edited,record.get("text_content",""))
                        update_extraction(conn,record["id"],cleaned)
                        st.success("Saved. Validation flags were refreshed.")
                        st.rerun()
                    except ValueError as error: st.error(str(error))
            st.caption(f"Original preserved at `{record['stored_path']}`")

elif section == "Analytics":
    st.markdown("<div class='eyebrow' style='color:#147d63'>SPENDING INSIGHTS</div>", unsafe_allow_html=True)
    st.title("Analytics & export")
    if df.empty:
        st.info("Import documents to see monthly and vendor summaries.")
    else:
        monthly=monthly_summary(df); vendors=vendor_summary(df)
        col1,col2=st.columns(2)
        with col1:
            st.subheader("By month")
            if not monthly.empty:
                fig=px.bar(monthly,x="month",y="total_amount",labels={"month":"Month","total_amount":"Amount"},color_discrete_sequence=["#168064"])
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",margin=dict(l=4,r=4,t=8,b=4),xaxis_title=None,yaxis_title=None)
                st.plotly_chart(fig,use_container_width=True)
        with col2:
            st.subheader("By vendor")
            clean_vendors=vendors.copy(); clean_vendors["vendor_name"]=clean_vendors["vendor_name"].fillna("Unknown")
            fig=px.bar(clean_vendors.head(12),x="vendor_name",y="total_amount",labels={"vendor_name":"Vendor","total_amount":"Amount"},color_discrete_sequence=["#87a993"])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",margin=dict(l=4,r=4,t=8,b=4),xaxis_title=None,yaxis_title=None)
            st.plotly_chart(fig,use_container_width=True)
        st.subheader("Document ledger")
        fields=[field for field in ["original_name","document_type","vendor_name","invoice_number","issue_date","currency","subtotal","tax","total_amount","payment_status","expense_category"] if field in df]
        st.dataframe(df[fields],hide_index=True,use_container_width=True)
        st.download_button("Download CSV",df.to_csv(index=False).encode("utf-8-sig"),"localledger_export.csv","text/csv",type="primary")
        st.caption("The export contains your locally stored document metadata and extraction results.")
