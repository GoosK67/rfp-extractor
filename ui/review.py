import streamlit as st
import pandas as pd

st.set_page_config(page_title="RFP Extractor Review", layout="wide")
st.title("RFP Extractor – Human‑in‑the‑Loop Review")

uploaded = st.file_uploader("Upload multitab XLSX (out.xlsx)", type=["xlsx"])
if not uploaded:
    st.info("Upload je out.xlsx om te starten.")
    st.stop()

# Probeer 'ALL', val terug op samenvoegen van bekende tabs
xls = pd.ExcelFile(uploaded)
try:
    all_df = pd.read_excel(xls, sheet_name="ALL")
except Exception:
    frames = []
    for sh in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sh)
        if {"id", "text", "type"}.issubset(df.columns):
            frames.append(df)
    if frames:
        all_df = pd.concat(frames, ignore_index=True)
    else:
        st.error("Kon geen 'ALL' tab vinden en geen alternatief met (id, text, type).")
        st.stop()

# Filters
st.subheader("Filters")
col1, col2, col3 = st.columns(3)
with col1:
    type_options = sorted(all_df["type"].dropna().unique())
    sel_types = st.multiselect("Type", options=type_options, default=list(type_options), key="flt_types")
with col2:
    src_filter = st.text_input("Filter op bronbestand (contains)", key="flt_src")
with col3:
    text_filter = st.text_input("Filter op tekst (contains)", key="flt_txt")

view = all_df.copy()
if sel_types:
    view = view[view["type"].isin(sel_types)]
if src_filter:
    view = view[view["source_file"].astype(str).str.contains(src_filter, case=False, na=False)]
if text_filter:
    view = view[view["text"].astype(str).str.contains(text_filter, case=False, na=False)]

st.write(f"Rijen na filter: {len(view)}")

EDITABLE_TYPES = ["BR", "FR", "NFR", "RISK", "SCOPE_IN", "SCOPE_OUT", "SCOPE_OTHER"]

def edit_row(row: pd.Series, unique_prefix: str):
    """
    Per rij een expander + form met unieke Streamlit-keys.
    """
    label = f"{row.get('id','(zonder id)')} – {row.get('type','?')} – {row.get('source_file','')}"
    with st.expander(label, expanded=False):
        with st.form(key=f"{unique_prefix}-form"):
            # Type
            cur_type = row.get("type", "BR")
            if cur_type not in EDITABLE_TYPES:
                cur_type = "BR"
            idx = EDITABLE_TYPES.index(cur_type)

            new_type = st.selectbox(
                "Type",
                options=EDITABLE_TYPES,
                index=idx,
                key=f"{unique_prefix}-type"
            )

            # Text
            new_text = st.text_area(
                "Text",
                value=str(row.get("text", "")),
                key=f"{unique_prefix}-text",
                height=140
            )

            # Confidence
            try:
                conf_val = float(row.get("governance_confidence", 0.0) or 0.0)
            except Exception:
                conf_val = 0.0

            new_conf = st.slider(
                "Governance confidence",
                min_value=0.0, max_value=1.0, value=conf_val, step=0.01,
                key=f"{unique_prefix}-conf"
            )

            # Explanation
            new_expl = st.text_area(
                "Governance explanation",
                value=str(row.get("governance_explanation", "")),
                key=f"{unique_prefix}-expl",
                height=120
            )

            submitted = st.form_submit_button("Apply edits for this row")
            return submitted, new_type, new_text, new_conf, new_expl

# Buffer voor edits in session_state
if "pending_edits" not in st.session_state:
    st.session_state["pending_edits"] = {}

# Itereer deterministisch (reset index zodat we een stabiele loop hebben)
for i, r in view.reset_index(drop=True).iterrows():
    uid = str(r.get("id", f"idx-{i}"))  # gebruik extractor-id indien aanwezig
    unique_prefix = f"row-{uid}"
    submitted, tp, tx, cf, ex = edit_row(r, unique_prefix)
    if submitted:
        st.session_state["pending_edits"][uid] = {
            "type": tp,
            "text": tx,
            "governance_confidence": cf,
            "governance_explanation": ex,
        }
        st.success(f"Edit buffered for {uid}")

# Toepassen op all_df in één keer
if st.button("Apply all buffered edits to data"):
    apply_count = 0
    # id -> index mapping
    id_to_idx = {}
    if "id" in all_df.columns:
        for idx_val, id_val in all_df["id"].reset_index(drop=True).items():
            id_to_idx[str(id_val)] = idx_val

    for uid, patch in st.session_state["pending_edits"].items():
        if uid in id_to_idx:
            row_idx = id_to_idx[uid]
            for k, v in patch.items():
                if k in all_df.columns:
                    all_df.at[row_idx, k] = v
            apply_count += 1
    st.success(f"Applied {apply_count} edits to dataframe.")

# Export
st.subheader("Export")
if st.button("Export XLSX"):
    import io
    from pandas import ExcelWriter

    out = io.BytesIO()
    # Bouw dezelfde tabs als de extractor
    def safe(df, t):
        return df[df["type"] == t] if "type" in df.columns else pd.DataFrame()

    tabs = {
        "BR":        safe(all_df, "BR"),
        "FR":        safe(all_df, "FR"),
        "NFR":       safe(all_df, "NFR"),
        "RISKS":     safe(all_df, "RISK"),
        "SCOPE_IN":  safe(all_df, "SCOPE_IN"),
        "SCOPE_OUT": safe(all_df, "SCOPE_OUT"),
        "SCOPE_OTHER": safe(all_df, "SCOPE_OTHER"),
        "ALL":       all_df
    }

    with ExcelWriter(out, engine="openpyxl") as w:
        for name, sub in tabs.items():
            sub.to_excel(w, sheet_name=name, index=False)

    st.download_button(
        "Download reviewed.xlsx",
        data=out.getvalue(),
        file_name="reviewed.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )