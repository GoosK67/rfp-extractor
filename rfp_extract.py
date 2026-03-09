# rfp_extract.py  — multi-file RFP extractor
# - Verwerkt meerdere DOCX en XLSX bestanden in 1 run
# - Dedupliceert op requirement-tekst
# - Classificeert (BR/FR/NFR/RISK/SCOPE*)
# - Voegt governance mapping + explanation + confidence toe
# - Exporteert naar multitab XLSX

import argparse
import sys
from pathlib import Path
import glob
import pandas as pd
import docx

from utils.helpers import (
    normalize_ws,
    is_probably_requirement_text,
    classify_requirement,
    governance_mapping,
    generate_req_id,
)

# ---------- Config ----------
ALLOWED_EXTS = {".docx", ".xlsx"}
XLSX_TEXT_CANDIDATES = {
    "requirement", "requirements", "req", "req_id",
    "text", "description", "omschrijving", "beschrijving",
    "requirement_text", "eis", "eisen"
}
# Kolomvolgorde voor output
OUTPUT_COLS = [
    "id", "text", "type", "source_file",
    "cobit", "itil", "iso27001",
    "governance_explanation", "governance_confidence"
]
# ----------------------------


def collect_input_files(args_list):
    """Verzamelt alle .docx en .xlsx uit opgegeven paden/patronen/mappen."""
    files = []
    for arg in args_list:
        p = Path(arg)
        if p.is_dir():
            # Neem alle .docx en .xlsx in de map (niet recursief)
            files += list(p.glob("*.docx"))
            files += list(p.glob("*.xlsx"))
        else:
            # Glob-patroon of enkel bestand
            matches = glob.glob(str(p))
            if not matches and p.exists():
                matches = [str(p)]
            for m in matches:
                mp = Path(m)
                if mp.suffix.lower() in ALLOWED_EXTS and mp.exists():
                    files.append(mp)
    # Uniek + sort
    uniq = []
    seen = set()
    for f in files:
        if f not in seen:
            uniq.append(f)
            seen.add(f)
    return uniq


def parse_docx_file(path: Path):
    """Parse DOCX: paragrafen -> filter -> classificeer -> governance."""
    out = []
    try:
        document = docx.Document(str(path))
    except Exception as e:
        print(f"[WARN] Kon DOCX niet openen: {path} ({e})", file=sys.stderr)
        return out

    for p in document.paragraphs:
        txt = normalize_ws(p.text)
        if not txt:
            continue
        if not is_probably_requirement_text(txt):
            continue

        rtype = classify_requirement(txt)
        gov = governance_mapping(txt)
        out.append({
            "id": generate_req_id(txt),
            "text": txt,
            "type": rtype,
            "source_file": path.name,
            "cobit": gov["cobit"],
            "itil": gov["itil"],
            "iso27001": gov["iso"],
            "governance_explanation": gov["explanation"],
            "governance_confidence": gov["confidence"],
        })
    return out


def _pick_text_column(columns):
    """Kies de meest waarschijnlijke kolom voor requirement-tekst."""
    cols_lower = [c.lower().strip() for c in columns]
    # 1) directe match
    for i, c in enumerate(cols_lower):
        if c in XLSX_TEXT_CANDIDATES:
            return i
    # 2) fuzzy: bevat 'require' of 'desc' of 'text'
    for i, c in enumerate(cols_lower):
        if "require" in c or "desc" in c or "text" in c:
            return i
    # 3) fallback: eerste kolom
    return 0 if columns else None


def parse_xlsx_file(path: Path):
    """Parse XLSX: elke sheet -> kies tekstkolom -> filter -> classificeer -> governance."""
    out = []
    try:
        xls = pd.ExcelFile(str(path), engine="openpyxl")
    except Exception as e:
        print(f"[WARN] Kon XLSX niet openen: {path} ({e})", file=sys.stderr)
        return out

    for sheet in xls.sheet_names:
        try:
            df = pd.read_excel(xls, sheet_name=sheet, engine="openpyxl")
        except Exception as e:
            print(f"[WARN] Kon sheet niet lezen: {path.name}:{sheet} ({e})", file=sys.stderr)
            continue

        if df.empty:
            continue

        # Kies een kolom met requirement-tekst
        text_col_idx = _pick_text_column(list(df.columns))
        if text_col_idx is None:
            continue

        text_col_name = df.columns[text_col_idx]
        for _, row in df.iterrows():
            val = row.get(text_col_name, "")
            txt = normalize_ws(str(val))
            if not txt:
                continue
            if not is_probably_requirement_text(txt):
                continue

            rtype = classify_requirement(txt)
            gov = governance_mapping(txt)
            out.append({
                "id": generate_req_id(txt),
                "text": txt,
                "type": rtype,
                "source_file": f"{path.name}:{sheet}",
                "cobit": gov["cobit"],
                "itil": gov["itil"],
                "iso27001": gov["iso"],
                "governance_explanation": gov["explanation"],
                "governance_confidence": gov["confidence"],
            })
    return out


def dedupe_requirements(records):
    """Dedupliceer op genormaliseerde tekst."""
    seen = {}
    deduped = []
    for r in records:
        key = normalize_ws(r["text"]).lower()
        if key in seen:
            continue
        seen[key] = True
        deduped.append(r)
    return deduped


def export_multitab_xlsx(records, out_path: Path):
    if not records:
        # Schrijf lege structuur met de juiste tabs/kolommen
        empty = pd.DataFrame(columns=OUTPUT_COLS)
        with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
            for tab in ["BR", "FR", "NFR", "RISKS", "SCOPE_IN", "SCOPE_OUT", "SCOPE_OTHER", "ALL"]:
                empty.to_excel(writer, sheet_name=tab, index=False)
        print(f"[OK] Geen requirements gevonden. Leeg bestand aangemaakt → {out_path}")
        return

    df = pd.DataFrame(records)
    # Zorg voor kolomvolgorde
    for col in OUTPUT_COLS:
        if col not in df.columns:
            df[col] = ""
    df = df[OUTPUT_COLS]

    # Per type naar sheet
    sheets = {
        "BR": df[df["type"] == "BR"],
        "FR": df[df["type"] == "FR"],
        "NFR": df[df["type"] == "NFR"],
        "RISKS": df[df["type"] == "RISK"],
        "SCOPE_IN": df[df["type"] == "SCOPE_IN"],
        "SCOPE_OUT": df[df["type"] == "SCOPE_OUT"],
        "SCOPE_OTHER": df[df["type"] == "SCOPE_OTHER"],
        "ALL": df,
    }

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        for name, subdf in sheets.items():
            subdf.to_excel(writer, sheet_name=name, index=False)

    print(f"[OK] Multitab XLSX geschreven → {out_path}  (totaal: {len(df)})")


def main():
    parser = argparse.ArgumentParser(
        description="RFP multi-file extractor (DOCX + XLSX) → multitab XLSX"
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Bestanden/patronen of een map (bijv. examples/ of 'examples/*.docx' 'examples/*.xlsx')",
    )
    parser.add_argument("--xlsx", default="output.xlsx", help="Output XLSX pad")
    parser.add_argument("--ai", default="on", choices=["on", "off"], help="(compat) AI explanation toggle")
    args = parser.parse_args()

    files = collect_input_files(args.inputs)
    if not files:
        print("[ERR] Geen invoerbestanden gevonden. Geef een map of bestanden/patronen op.")
        sys.exit(2)

    print("[INFO] Bestanden:")
    for f in files:
        print(f"  - {f}")

    all_records = []
    for f in files:
        ext = f.suffix.lower()
        if ext == ".docx":
            recs = parse_docx_file(f)
        elif ext == ".xlsx":
            recs = parse_xlsx_file(f)
        else:
            continue
        all_records.extend(recs)

    merged = dedupe_requirements(all_records)
    export_multitab_xlsx(merged, Path(args.xlsx))


if __name__ == "__main__":
    main()