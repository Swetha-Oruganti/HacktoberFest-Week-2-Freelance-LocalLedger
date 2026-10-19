import pandas as pd

def documents_frame(records: list[dict]) -> pd.DataFrame:
    rows=[]
    for record in records:
        row=dict(record.get("extraction", {})); row.update({"id":record.get("id"),"original_name":record.get("original_name"),"stored_path":record.get("stored_path"),"imported_at":record.get("imported_at")}); rows.append(row)
    df=pd.DataFrame(rows)
    if not df.empty:
        df["issue_date"]=pd.to_datetime(df["issue_date"], errors="coerce")
        df["month"]=df["issue_date"].dt.to_period("M").astype(str)
    return df

def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return pd.DataFrame(columns=["month","total_amount"])
    return df.dropna(subset=["month"]).groupby("month", as_index=False)["total_amount"].sum()

def vendor_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return pd.DataFrame(columns=["vendor_name","total_amount"])
    return df.groupby("vendor_name", dropna=False, as_index=False)["total_amount"].sum().sort_values("total_amount", ascending=False)
