
import argparse
from pathlib import Path
import json
import pandas as pd
from docx import Document

from utils.helpers import normalize_ws, is_heading, classify_requirement, is_shell_requirement, generate_req_id
from parser.text_extractor import extract_paragraphs
from parser.table_extractor import extract_table_texts

# ---------------- Governance mapping helpers ----------------
def _load_mapping(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return {}

def _match_keywords(text: str, mapping: dict) -> list[str]:
    t = (text or '').lower()
    hits = []
    for kw, controls in mapping.items():
        if kw.lower() in t:
            hits.extend(controls if isinstance(controls, list) else [controls])
    return sorted(set(hits))

def map_governance(text: str, base_dir: Path) -> tuple[list[str], list[str], list[str], float]:
    cobit = _load_mapping(base_dir / 'governance' / 'mappings_cobit.json')
    itil = _load_mapping(base_dir / 'governance' / 'mappings_itil.json')
    iso  = _load_mapping(base_dir / 'governance' / 'mappings_iso27001.json')
    cobit_hits = _match_keywords(text, cobit)
    itil_hits  = _match_keywords(text, itil)
    iso_hits   = _match_keywords(text, iso)
    total_hits = len(cobit_hits) + len(itil_hits) + len(iso_hits)
    confidence = min(0.9, 0.4 + 0.2 * total_hits) if total_hits else 0.0
    return cobit_hits, itil_hits, iso_hits, round(confidence, 2)

# ---------------- Extraction pipeline ----------------
def extract_requirements(docx_path: Path, enable_ai: bool = False) -> list[dict]:
    base_dir = Path(__file__).parent
    doc = Document(str(docx_path))
    items: list[dict] = []

    current_heading = ''
    # 1) Paragraphs
    for p in extract_paragraphs(doc):
        text = normalize_ws(p['text'])
        if not text:
            continue
        if is_heading(text) or (p.get('style') and 'Heading' in p['style']):
            current_heading = text
            continue
        if len(text) < 6:
            continue
        if is_shell_requirement(text):
            continue
        cat = classify_requirement(text) or 'UNCLASSIFIED'
        source = f"para:{p['index']}"
        rid = generate_req_id(text, source)
        cobit, itil, iso, conf = map_governance(text, base_dir)
        items.append({
            'req_id': rid,
            'category': cat,
            'text': text,
            'heading': current_heading,
            'source': source,
            'COBIT': ", ".join(cobit),
            'ITIL': ", ".join(itil),
            'ISO27001': ", ".join(iso),
            'confidence': conf,
        })

    # 2) Tables
    for cell in extract_table_texts(doc):
        text = normalize_ws(cell['text'])
        if not text or len(text) < 6 or is_shell_requirement(text):
            continue
        cat = classify_requirement(text) or 'UNCLASSIFIED'
        source = f"table:{cell['table_idx']}/{cell['row']},{cell['col']}"
        rid = generate_req_id(text, source)
        cobit, itil, iso, conf = map_governance(text, base_dir)
        items.append({
            'req_id': rid,
            'category': cat,
            'text': text,
            'heading': current_heading,
            'source': source,
            'COBIT': ", ".join(cobit),
            'ITIL': ", ".join(itil),
            'ISO27001': ", ".join(iso),
            'confidence': conf,
        })

    # 3) (Optional) AI enrichment hook
    if enable_ai:
        try:
            from ai.ai_hooks import enrich_with_ai
            items = enrich_with_ai(items)
        except Exception:
            pass
    return items

def main():
    ap = argparse.ArgumentParser(description='Extract requirements from a DOCX RFP into XLSX (and optionally enrich).')
    ap.add_argument('input', help='Pad naar .docx bestand')
    ap.add_argument('--xlsx', default='out.xlsx', help='Output Excel pad (default: out.xlsx)')
    ap.add_argument('--json', default=None, help='(optioneel) export JSON')
    ap.add_argument('--ai', default='off', choices=['on', 'off'], help='AI enrichment (default: off)')
    args = ap.parse_args()

    docx_path = Path(args.input)
    if not docx_path.exists():
        raise SystemExit(f"Input niet gevonden: {docx_path}")

    items = extract_requirements(docx_path, enable_ai=(args.ai == 'on'))
    if not items:
        print('Geen requirements gevonden (na filtering).')

    # DataFrame export
    df = pd.DataFrame(items, columns=[
        'req_id', 'category', 'text', 'heading', 'source', 'COBIT', 'ITIL', 'ISO27001', 'confidence'
    ])
    df.to_excel(args.xlsx, index=False)
    print(f"Excel geschreven: {args.xlsx}  (rows={len(df)})")

    if args.json:
        Path(args.json).write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"JSON geschreven: {args.json}")

if __name__ == '__main__':
    main()
