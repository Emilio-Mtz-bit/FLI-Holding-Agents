import pytest
from agents.qual.models import QualDoc, Chunk, ProcessedDoc, QualOutput, Alert


def test_qual_doc_auto_detects_type_from_extension():
    doc = QualDoc(path="some/file.pdf")
    assert doc.doc_type == "pdf"


def test_qual_doc_auto_detects_image():
    doc = QualDoc(path="some/image.png")
    assert doc.doc_type == "image"


def test_qual_doc_auto_detects_text():
    doc = QualDoc(path="some/notes.md")
    assert doc.doc_type == "text"


def test_qual_doc_accepts_explicit_type():
    doc = QualDoc(path="some/file.xyz", doc_type="text")
    assert doc.doc_type == "text"


def test_chunk_fields():
    chunk = Chunk(text="hello world", source_path="file.md", chunk_index=0)
    assert chunk.text == "hello world"
    assert chunk.chunk_index == 0


def test_qual_output_defaults():
    output = QualOutput(
        signals={"fortalezas": ["calidad"]},
        sentiment=0.5,
        summary="resumen",
        chunks_stored=3,
    )
    assert output.hypotheses == []
