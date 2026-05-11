import warnings
from agents.qual.models import QualDoc, ProcessedDoc


class LowOCRConfidenceWarning(UserWarning):
    pass


def _extract_pdf(path: str) -> str:
    import fitz  # PyMuPDF
    doc = fitz.open(path)
    return "\n".join(page.get_text() for page in doc)


def _extract_image(path: str) -> str:
    import pytesseract
    from PIL import Image
    text = pytesseract.image_to_string(Image.open(path), lang="spa")
    if len(text.strip()) < 50:
        warnings.warn(
            f"OCR returned fewer than 50 characters for '{path}'. Skipping.",
            LowOCRConfidenceWarning,
        )
        return ""
    return text


def _extract_text(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


_EXTRACTORS = {
    "pdf": _extract_pdf,
    "image": _extract_image,
    "text": _extract_text,
}


def process(doc: QualDoc) -> ProcessedDoc:
    extractor = _EXTRACTORS[doc.doc_type]
    raw_text = extractor(doc.path)
    return ProcessedDoc(
        raw_text=raw_text,
        chunks=[],
        source_path=doc.path,
        doc_type=doc.doc_type,
    )
