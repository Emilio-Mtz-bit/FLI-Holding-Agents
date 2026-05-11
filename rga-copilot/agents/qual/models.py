from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, model_validator


def _detect_type(path: str) -> str:
    ext = path.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        return "pdf"
    if ext in ("png", "jpg", "jpeg"):
        return "image"
    return "text"


class Alert(BaseModel):
    sucursal: str
    message: str
    severity: Literal["red", "yellow"]


class QualDoc(BaseModel):
    path: str
    doc_type: Literal["pdf", "image", "text"] | None = None

    @model_validator(mode="after")
    def auto_detect_type(self) -> QualDoc:
        if self.doc_type is None:
            self.doc_type = _detect_type(self.path)
        return self


class Chunk(BaseModel):
    text: str
    source_path: str
    chunk_index: int


class ProcessedDoc(BaseModel):
    raw_text: str
    chunks: list[Chunk]
    source_path: str
    doc_type: str


class QualOutput(BaseModel):
    signals: dict[str, Any]
    sentiment: float
    hypotheses: list[str] = []
    summary: str
    chunks_stored: int
