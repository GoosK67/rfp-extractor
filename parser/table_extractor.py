
from docx.document import Document as _Document

def extract_table_texts(doc: _Document):
    '''Yield dicts: {table_idx, row, col, text} for each cell text (non-empty).'''
    for ti, tbl in enumerate(doc.tables):
        for ri, row in enumerate(tbl.rows):
            for ci, cell in enumerate(row.cells):
                t = (cell.text or '').strip()
                if t:
                    yield {
                        'table_idx': ti,
                        'row': ri,
                        'col': ci,
                        'text': t
                    }
