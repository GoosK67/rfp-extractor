
import streamlit as st
import pandas as pd

st.set_page_config(page_title="RFP Extractor Review", layout="wide")

st.title("RFP Extractor – Human‑in‑the‑Loop Review")

uploaded = st.file_uploader("Upload multitab XLSX (out.xlsx)", type=["xlsx"])
if not uploaded:
    st.info("Upload je out.xlsx om te starten.")
    st.stop()

xls = pd.ExcelFile(uploaded)
all_df = pd.read_excel(xls, sheet_name="ALL")

st.subheader("Filters")
col1, col2, col3 = st.columns(3)
with col1:
    t = st.multiselect("Type", options=sorted(all_df["type"].unique()), default=list(sorted(all_df["type"].unique())))
with col2:
    src = st.text_input("Zoek in bronbestand (contains)")
with col3:
    fw = st.text_input("Zoek in tekst (contains)")

view = all_df.copy()
if t:
    view = view[view["type"].isin(t)]
if src:
    view = view[view["source_file"].astype(str).str.contains(src, case=False, na=False)]
if fw:
    view = view[view["text"].astype(str).str.contains(fw, case=False, na=False)]

st.write(f"Rijen: {len(view)}")

def edit_row(row):
    with st.expander(f"{row['id']} – {row['type']} – {row['source_file']}"):
        new_type = st.selectbox("Type", ["BR","FR","NFR","RISK","SCOPE_IN","SCOPE_OUT","SCOPE_OTHER"], index=["BR","FR","NFR","RISK","SCOPE_IN","SCOPE_OUT","SCOPE_OTHER"].index(row['type']))
        new_text = st.text_area("Text", value=row['text'])
        new_conf = st.slider("Governance confidence", 0.0, 1.0, float(row['governance_confidence'] or 0.0), 0.01)
        new_expl = st.text_area("Governance explanation", value=row.get('governance_explanation',''))
        return new_type, new_text, new_conf, new_expl

edited_rows = []
for i, r in view.iterrows():
    tp, tx, cf, ex = edit_row(r)
    edited_rows.append((i, tp, tx, cf, ex))

if st.button("Apply edits"):
    for i, tp, tx, cf, ex in edited_rows:
        all_df.at[i, 'type'] = tp
        all_df.at[i, 'text'] = tx
        all_df.at[i, 'governance_confidence'] = cf
        all_df.at[i, 'governance_explanation'] = ex
    st.success("Edits applied in memory. Export to XLSX below.")

if st.button("Export XLSX"):
    import io
    from pandas import ExcelWriter
    out = io.BytesIO()
    with ExcelWriter(out, engine="openpyxl") as w:
        # Rebuild sheets like extractor
        tabs = {
            "BR": all_df[all_df["type"]=="BR"],
            "FR": all_df[all_df["type"]=="FR"],
            "NFR": all_df[all_df["type"]=="NFR"],
            "RISKS": all_df[all_df["type"]=="RISK"],
            "SCOPE_IN": all_df[all_df["type"]=="SCOPE_IN"],
            "SCOPE_OUT": all_df[all_df["type"]=="SCOPE_OUT"],
            "SCOPE_OTHER": all_df[all_df["type"]=="SCOPE_OTHER"],
            "ALL": all_df,
        }
        for name, sub in tabs.items():
            sub.to_excel(w, sheet_name=name, index=False)
    st.download_button("Download reviewed.xlsx", data=out.getvalue(), file_name="reviewed.xlsx")
