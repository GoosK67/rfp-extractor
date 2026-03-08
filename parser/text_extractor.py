
from docx.document import Document as _Document

def extract_paragraphs(doc: _Document):
    '''Yield dicts: {index, text, style} for each paragraph.'''
    for i, p in enumerate(doc.paragraphs):
        style_name = None
        try:
            style_name = p.style.name if p.style else None
        except Exception:
            style_name = None
        yield {
            'index': i,
            'text': p.text or '',
            'style': style_name or ''
        }
