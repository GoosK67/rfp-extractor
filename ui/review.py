import streamlit as st
import pandas as pd

st.set_page_config(page_title="RFP Extractor Review", layout="wide")
st.title("RFP Extractor – Human‑in‑the‑Loop Review")

uploaded = st.file_uploader("Upload multitab XLSX (out.xlsx)", type=["xlsx"])
if not uploaded:
    st.info("Upload je out.xlsx om te starten.")
    st.stop()

# Lees ALL tab (verplicht aanwezig in onze export)
xls = pd.ExcelFile(uploaded)
try:
    all_df = pd.read_excel(xls, sheet_name="ALL")
except Exception:
    # fallback: concat alle tabs die bekende kolommen hebben
    frames = []
    for sh in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sh)
        if {"id","text","type"}.issubset(df.columns):
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
    types_sorted = sorted(all_df["type"].dropna().unique())
    sel_types = st.multiselect("Type", options=types_sorted, default=list(types_sorted), key="filter_types")
with col2:
    src_filter = st.text_input("Filter op bronbestand (contains)", key="filter_source")
with col3:
    text_filter = st.text_input("Filter op tekst (contains)", key="filter_text")

view = all_df.copy()
if sel_types:
    view = view[view["type"].isin(sel_types)]
if src_filter:
    view = view[view["source_file"].astype(str).str.contains(src_filter, case=False, na=False)]
if text_filter:
    view = view[view["text"].astype(str).str.contains(text_filter, case=False, na=False)]

st.write(f"Rijen na filter: {len(view)}")

EDITABLE_TYPES = ["BR","FR","NFR","RISK","SCOPE_IN","SCOPE_OUT","SCOPE_OTHER"]

def edit_row(row, unique_prefix: str):
    """
    Maakt unieke keys per widget op basis van 'unique_prefix'.
    unique_prefix kan bv. 'row-{row["id"]}' of 'row-<index>' zijn.
    """
    with st.expander(f"{row['id']} – {row['type']} – {row.get('source_file','')}", expanded=False):
        # Gebruik een form per rij (zorgt voor duidelijke apply‑actie)
        # Je kan ook zonder form werken; keys blijven verplicht uniek.
        with st.form(key=f"{unique_prefix}-form"):
            # TYPE
            current_type = row["type"] if row["type"] in EDITABLE_TYPES else "BR"
            type_idx = EDITABLE_TYPES.index(current_type)
            new_type = st.selectbox(
                "Type",
                EDITABLE_TYPES,
                index=type_idx,
                key=f"{unique_prefix}-type"
            )

            # TEXT
            new_text = st.text_area(
                "Text",
                value=str(row.get("text","")),
                key=f"{unique_prefix}-text",
                height=140
            )

            # CONFIDENCE
            conf_val = float(row.get("governance_confidence", 0.0) or 0.0)
            new_conf = st.slider(
                "Governance confidence",
                min_value=0.0, max_value=1.0, value=conf_val, step=0.01,
                key=f"{unique_prefix}-conf"
            )

            # EXPLANATION
            new_expl = st.text_area(
                "Governance explanation",
                value=str(row.get("governance_explanation","")),
                key=f"{unique_prefix}-expl",
                height=120
            )

            # Submit
            submitted = st.form_submit_button("Apply edits for this row")
            return submitted, new_type, new_text, new_conf, new_expl

# Bewerkingen opslaan in memory (session state) zodat meerdere rijen los kunnen worden ge‑'applied'
if "pending_edits" not in st.session_state:
    st.session_state["pending_edits"] = {}

# Itereer deterministisch over gefilterde weergave
edited_any = False
for i, r in view.reset_index(drop=False).iterrows():
    # Unieke prefix: neem liefst de 'id' uit de extractor (stabiel)
    uid = str(r.get("id", f"idx-{i}"))
    unique_prefix = f"row-{uid}"

    submitted, tp, tx, cf, ex = edit_row(r, unique_prefix)
    if submitted:
        # Bewaar wijziging voor deze rij-id
        st.session_state["pending_edits"][uid] = {
            "type": tp,
            "text": tx,
            "governance_confidence": cf,
            "governance_explanation": ex,
        }
        edited_any = True
        st.success(f"Edit applied (buffered) for {uid}")

# Toepassen op all_df (1‑klik voor alle buffered changes)
if st.button("Apply all buffered edits to data"):
    apply_count = 0
    # We mappen per id (stabiel); als id ontbreekt, mappen via index
    by_id = {str(x): idx for idx, x in all_df["id"].reset_index(drop=True).items()}
    for uid, patch in st.session_state["pending_edits"].items():
        if uid in by_id:
            row_idx = by_id[uid]
            for k, v in patch.items():
                all_df.at[row_idx, k] = v
            apply_count += 1
    st.success(f"Applied {apply_count} edits.")
    # optioneel: leeglopen van buffer
    # st.session_state["pending_edits"] = {}

# Exportknop (bouwt dezelfde tabs als de extractor)
st.subheader("Export")
if st.button("Export XLSX"):
    import io
    from pandas import ExcelWriter

    out = io.BytesIO()

    # Rebuild sheets like extractor
    tabs = {
        "BR": all_df[all_df["type"] == "BR"],
        "FR": all_df[all_df["type"] == "FR"],
        "NFR": all_df[all_df["type"] == "NFR"],
        "RISKS": all_df[all_df["type"] == "RISK"],
        "SCOPE_IN": all_df[all_df["type"] == "SCOPE_IN"],
        "SCOPE_OUT": all_df[all_df["type"] == "SCOPE_OUT"],
        "SCOPE_OTHER": all_df[all_df["type"] == "SCOPE_OTHER"],
        "ALL": all_df,
    }

    with ExcelWriter(out, engine="openpyxl") as w:
        for name, sub in tabs.items():
            sub.to_excel(w, sheet_name=name, index=False)

    st.download_button("Download reviewed.xlsx", data=out.getvalue(), file_name="reviewed.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
``