import pytest
from pathlib import Path
from agents.qual.models import QualDoc
from agents.qual.doc_processor import process, LowOCRConfidenceWarning

FIXTURES = Path(__file__).parent / "fixtures"


def test_process_text_file():
    doc = QualDoc(path=str(FIXTURES / "sample.txt"))
    result = process(doc)
    assert result.doc_type == "text"
    assert "prueba" in result.raw_text
    assert result.source_path == str(FIXTURES / "sample.txt")


def test_process_unknown_extension_falls_back_to_text():
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
        f.write("# Titulo\nContenido del markdown.")
        tmp_path = f.name
    try:
        doc = QualDoc(path=tmp_path)
        result = process(doc)
        assert "Contenido" in result.raw_text
    finally:
        os.unlink(tmp_path)
