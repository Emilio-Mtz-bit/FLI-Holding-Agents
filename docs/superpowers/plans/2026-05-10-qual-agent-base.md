# QualAgent Base Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the base QualAgent that ingests PDF, image, and text documents, chunks and embeds them into ChromaDB, extracts structured signals via Claude, and returns a `QualOutput` with signals, sentiment, and executive summary.

**Architecture:** Single-pass flat pipeline — each document is processed sequentially (extract → clean → chunk → embed), then one Claude call extracts signals from all chunks concatenated, and a second Claude call generates the summary. No RAG or hypothesis generation in this phase.

**Tech Stack:** Python 3.11+, PyMuPDF, pytesseract, Pillow, chromadb, sentence-transformers, anthropic, pydantic, pyyaml, pytest

---

## File Map

| File | Responsibility |
|---|---|
| `rga-copilot/agents/qual/models.py` | Pydantic contracts: QualDoc, Chunk, ProcessedDoc, QualOutput |
| `rga-copilot/agents/qual/config/nama_signals.yaml` | Per-client signal schema for NAMA |
| `rga-copilot/agents/qual/doc_processor.py` | Type detection + raw text extraction (PDF/image/text) |
| `rga-copilot/agents/qual/cleaner.py` | Text normalization |
| `rga-copilot/agents/qual/chunker.py` | Split text into Chunk objects with overlap |
| `rga-copilot/agents/qual/embedder.py` | EmbedderBase ABC + SentenceTransformerEmbedder + ChromaStore |
| `rga-copilot/agents/qual/signal_extractor.py` | Load client YAML schema + Claude structured extraction |
| `rga-copilot/agents/qual/summarizer.py` | Two Claude calls: signals paragraph + key quote |
| `rga-copilot/agents/qual/agent.py` | QualAgent.run() — orchestrates all steps |
| `rga-copilot/agents/qual/prompts/signal_extraction.txt` | Prompt template for signal extraction |
| `rga-copilot/agents/qual/prompts/summary.txt` | Prompt template for summary generation |
| `rga-copilot/requirements.txt` | Python dependencies |
| `tests/qual/test_models.py` | Tests for Pydantic contracts |
| `tests/qual/test_doc_processor.py` | Tests for text extraction |
| `tests/qual/test_cleaner.py` | Tests for text normalization |
| `tests/qual/test_chunker.py` | Tests for chunking logic |
| `tests/qual/test_embedder.py` | Tests for ChromaStore |
| `tests/qual/test_signal_extractor.py` | Tests for signal extraction (mocked Claude) |
| `tests/qual/test_summarizer.py` | Tests for summary generation (mocked Claude) |
| `tests/qual/test_agent.py` | Integration test with real NAMA document |

---

### Task 1: Project structure + dependencies

**Files:**
- Create: `rga-copilot/requirements.txt`
- Create: `rga-copilot/agents/__init__.py`
- Create: `rga-copilot/agents/qual/__init__.py`
- Create: `rga-copilot/agents/qual/config/` (directory)
- Create: `rga-copilot/agents/qual/prompts/` (directory)
- Create: `tests/__init__.py`
- Create: `tests/qual/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
# rga-copilot/requirements.txt
anthropic>=0.30.0
pydantic>=2.0.0
pyyaml>=6.0
pymupdf>=1.24.0
pytesseract>=0.3.10
Pillow>=10.0.0
chromadb>=0.5.0
sentence-transformers>=3.0.0
pytest>=8.0.0
pytest-mock>=3.14.0
```

- [ ] **Step 2: Install dependencies**

```bash
cd rga-copilot
pip install -r requirements.txt
```

Expected: all packages install without errors.

- [ ] **Step 3: Create directory structure**

```bash
mkdir -p rga-copilot/agents/qual/config
mkdir -p rga-copilot/agents/qual/prompts
mkdir -p tests/qual
touch rga-copilot/agents/__init__.py
touch rga-copilot/agents/qual/__init__.py
touch tests/__init__.py
touch tests/qual/__init__.py
```

- [ ] **Step 4: Commit**

```bash
git add rga-copilot/requirements.txt rga-copilot/agents/ tests/
git commit -m "chore: scaffold qual agent directory structure and dependencies"
```

---

### Task 2: Pydantic contracts

**Files:**
- Create: `rga-copilot/agents/qual/models.py`
- Create: `tests/qual/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/qual/test_models.py
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd rga-copilot
pytest ../tests/qual/test_models.py -v
```

Expected: `ModuleNotFoundError: No module named 'agents.qual.models'`

- [ ] **Step 3: Write minimal implementation**

```python
# rga-copilot/agents/qual/models.py
from __future__ import annotations
from typing import Literal
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
    signals: dict
    sentiment: float
    hypotheses: list[str] = []
    summary: str
    chunks_stored: int
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd rga-copilot
pytest ../tests/qual/test_models.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add rga-copilot/agents/qual/models.py tests/qual/test_models.py
git commit -m "feat: add QualAgent Pydantic contracts"
```

---

### Task 3: Client signal schema YAML

**Files:**
- Create: `rga-copilot/agents/qual/config/nama_signals.yaml`

- [ ] **Step 1: Create NAMA signal schema**

```yaml
# rga-copilot/agents/qual/config/nama_signals.yaml
client: nama
signals:
  - key: tipo_empresa
    type: str
  - key: posicionamiento
    type: str
  - key: fortalezas
    type: list[str]
  - key: riesgos
    type: list[str]
  - key: factores_crecimiento
    type: list[str]
  - key: temas_topicos
    type: list[str]
  - key: sentiment_score
    type: float
    range: [-1.0, 1.0]
```

- [ ] **Step 2: Verify it loads correctly**

```bash
python -c "
import yaml
schema = yaml.safe_load(open('rga-copilot/agents/qual/config/nama_signals.yaml'))
print(schema['client'])
print([s['key'] for s in schema['signals']])
"
```

Expected output:
```
nama
['tipo_empresa', 'posicionamiento', 'fortalezas', 'riesgos', 'factores_crecimiento', 'temas_topicos', 'sentiment_score']
```

- [ ] **Step 3: Commit**

```bash
git add rga-copilot/agents/qual/config/nama_signals.yaml
git commit -m "feat: add NAMA client signal schema"
```

---

### Task 4: doc_processor.py

**Files:**
- Create: `rga-copilot/agents/qual/doc_processor.py`
- Create: `tests/qual/test_doc_processor.py`
- Create: `tests/qual/fixtures/sample.txt` (test fixture)

- [ ] **Step 1: Create text fixture**

```bash
echo "Este es un texto de prueba para el agente cualitativo." > tests/qual/fixtures/sample.txt
```

- [ ] **Step 2: Write the failing test**

```python
# tests/qual/test_doc_processor.py
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
    # .md should be treated as text
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
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd rga-copilot
pytest ../tests/qual/test_doc_processor.py -v
```

Expected: `ModuleNotFoundError: No module named 'agents.qual.doc_processor'`

- [ ] **Step 4: Write minimal implementation**

```python
# rga-copilot/agents/qual/doc_processor.py
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
        chunks=[],          # chunker fills this later
        source_path=doc.path,
        doc_type=doc.doc_type,
    )
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd rga-copilot
pytest ../tests/qual/test_doc_processor.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add rga-copilot/agents/qual/doc_processor.py tests/qual/test_doc_processor.py tests/qual/fixtures/
git commit -m "feat: add doc_processor with PDF, image OCR, and text extraction"
```

---

### Task 5: cleaner.py

**Files:**
- Create: `rga-copilot/agents/qual/cleaner.py`
- Create: `tests/qual/test_cleaner.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/qual/test_cleaner.py
from agents.qual.cleaner import clean


def test_collapses_multiple_spaces():
    assert clean("hola   mundo") == "hola mundo"


def test_collapses_multiple_newlines():
    result = clean("linea1\n\n\n\nlinea2")
    assert "\n\n\n" not in result


def test_strips_page_number_pattern():
    result = clean("contenido\n3\nmas contenido")
    # standalone digits on their own line should be stripped
    assert "\n3\n" not in result


def test_strips_horizontal_rule():
    result = clean("texto\n---\nmas texto")
    assert "---" not in result


def test_normalizes_unicode():
    result = clean("café y señor")
    assert "café" in result


def test_lowercases_text():
    result = clean("GRUPO NAMA es Excelente")
    assert result == result.lower()


def test_empty_string_returns_empty():
    assert clean("") == ""
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd rga-copilot
pytest ../tests/qual/test_cleaner.py -v
```

Expected: `ModuleNotFoundError: No module named 'agents.qual.cleaner'`

- [ ] **Step 3: Write minimal implementation**

```python
# rga-copilot/agents/qual/cleaner.py
import re
import unicodedata


def clean(text: str) -> str:
    if not text:
        return ""
    # Normalize unicode (preserve accented chars)
    text = unicodedata.normalize("NFC", text)
    # Lowercase
    text = text.lower()
    # Strip standalone horizontal rules
    text = re.sub(r"^\s*---+\s*$", "", text, flags=re.MULTILINE)
    # Strip standalone page numbers (lone digits on their own line)
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
    # Collapse multiple spaces (but not newlines)
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse more than 2 consecutive newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd rga-copilot
pytest ../tests/qual/test_cleaner.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add rga-copilot/agents/qual/cleaner.py tests/qual/test_cleaner.py
git commit -m "feat: add text cleaner with normalization and boilerplate removal"
```

---

### Task 6: chunker.py

**Files:**
- Create: `rga-copilot/agents/qual/chunker.py`
- Create: `tests/qual/test_chunker.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/qual/test_chunker.py
from agents.qual.chunker import chunk


SHORT_TEXT = "hola mundo"
LONG_TEXT = "palabra " * 600  # ~4800 chars, should produce multiple chunks


def test_short_text_produces_one_chunk():
    chunks = chunk(SHORT_TEXT, source_path="doc.txt")
    assert len(chunks) == 1
    assert chunks[0].text == SHORT_TEXT
    assert chunks[0].source_path == "doc.txt"
    assert chunks[0].chunk_index == 0


def test_long_text_produces_multiple_chunks():
    chunks = chunk(LONG_TEXT, source_path="doc.txt")
    assert len(chunks) > 1


def test_chunks_have_sequential_indices():
    chunks = chunk(LONG_TEXT, source_path="doc.txt")
    for i, c in enumerate(chunks):
        assert c.chunk_index == i


def test_chunks_have_correct_source_path():
    chunks = chunk(LONG_TEXT, source_path="informe.pdf")
    for c in chunks:
        assert c.source_path == "informe.pdf"


def test_overlap_means_last_chars_of_chunk_appear_in_next():
    # With overlap, end of chunk N should appear in start of chunk N+1
    chunks = chunk(LONG_TEXT, source_path="doc.txt")
    if len(chunks) > 1:
        end_of_first = chunks[0].text[-100:]
        start_of_second = chunks[1].text[:300]
        assert end_of_first.strip() in start_of_second
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd rga-copilot
pytest ../tests/qual/test_chunker.py -v
```

Expected: `ModuleNotFoundError: No module named 'agents.qual.chunker'`

- [ ] **Step 3: Write minimal implementation**

```python
# rga-copilot/agents/qual/chunker.py
from agents.qual.models import Chunk

CHUNK_SIZE = 2000   # ~500 tokens
OVERLAP = 200       # ~50 tokens


def chunk(text: str, source_path: str) -> list[Chunk]:
    if len(text) <= CHUNK_SIZE:
        return [Chunk(text=text, source_path=source_path, chunk_index=0)]

    chunks = []
    start = 0
    index = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunks.append(Chunk(
            text=text[start:end],
            source_path=source_path,
            chunk_index=index,
        ))
        start += CHUNK_SIZE - OVERLAP
        index += 1
    return chunks
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd rga-copilot
pytest ../tests/qual/test_chunker.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add rga-copilot/agents/qual/chunker.py tests/qual/test_chunker.py
git commit -m "feat: add chunker with 2000 char chunks and 200 char overlap"
```

---

### Task 7: embedder.py

**Files:**
- Create: `rga-copilot/agents/qual/embedder.py`
- Create: `tests/qual/test_embedder.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/qual/test_embedder.py
import tempfile
import pytest
from agents.qual.models import Chunk
from agents.qual.embedder import EmbedderBase, SentenceTransformerEmbedder, ChromaStore


class FakeEmbedder(EmbedderBase):
    """Returns fixed-length zero vectors — avoids loading a real model in tests."""
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 384 for _ in texts]


def test_fake_embedder_returns_vectors_for_each_text():
    emb = FakeEmbedder()
    result = emb.embed(["hola", "mundo"])
    assert len(result) == 2
    assert len(result[0]) == 384


def test_chroma_store_stores_chunks_and_returns_count():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ChromaStore(
            persist_path=tmpdir,
            collection_name="test",
            embedder=FakeEmbedder(),
        )
        chunks = [
            Chunk(text="chunk uno", source_path="a.txt", chunk_index=0),
            Chunk(text="chunk dos", source_path="a.txt", chunk_index=1),
        ]
        count = store.store(chunks)
        assert count == 2


def test_chroma_store_is_idempotent_on_same_collection():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ChromaStore(
            persist_path=tmpdir,
            collection_name="test",
            embedder=FakeEmbedder(),
        )
        chunks = [Chunk(text="hola", source_path="b.txt", chunk_index=0)]
        store.store(chunks)
        # Second call should not raise
        store2 = ChromaStore(tmpdir, "test", FakeEmbedder())
        count = store2.store([Chunk(text="mundo", source_path="b.txt", chunk_index=1)])
        assert count == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd rga-copilot
pytest ../tests/qual/test_embedder.py -v
```

Expected: `ModuleNotFoundError: No module named 'agents.qual.embedder'`

- [ ] **Step 3: Write minimal implementation**

```python
# rga-copilot/agents/qual/embedder.py
from abc import ABC, abstractmethod
import chromadb
from agents.qual.models import Chunk


class EmbedderBase(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class SentenceTransformerEmbedder(EmbedderBase):
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, show_progress_bar=False).tolist()


class ChromaStore:
    def __init__(self, persist_path: str, collection_name: str, embedder: EmbedderBase):
        self.client = chromadb.PersistentClient(path=persist_path)
        self.collection = self.client.get_or_create_collection(collection_name)
        self.embedder = embedder

    def store(self, chunks: list[Chunk]) -> int:
        if not chunks:
            return 0
        texts = [c.text for c in chunks]
        embeddings = self.embedder.embed(texts)
        ids = [f"{c.source_path}::chunk-{c.chunk_index}" for c in chunks]
        self.collection.add(documents=texts, embeddings=embeddings, ids=ids)
        return len(chunks)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd rga-copilot
pytest ../tests/qual/test_embedder.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add rga-copilot/agents/qual/embedder.py tests/qual/test_embedder.py
git commit -m "feat: add EmbedderBase interface, SentenceTransformerEmbedder, and ChromaStore"
```

---

### Task 8: Prompts + signal_extractor.py

**Files:**
- Create: `rga-copilot/agents/qual/prompts/signal_extraction.txt`
- Create: `rga-copilot/agents/qual/signal_extractor.py`
- Create: `tests/qual/test_signal_extractor.py`

- [ ] **Step 1: Create signal extraction prompt template**

```
# rga-copilot/agents/qual/prompts/signal_extraction.txt
Analiza el siguiente texto empresarial y extrae las señales indicadas.
Devuelve ÚNICAMENTE un objeto JSON válido con exactamente las siguientes claves:

{schema_keys}

Reglas:
- Para claves de tipo list[str]: devuelve una lista de strings, mínimo 1 elemento.
- Para claves de tipo float con rango [-1.0, 1.0]: devuelve un número decimal en ese rango.
- Para claves de tipo str: devuelve una cadena de texto concisa.
- No incluyas texto fuera del JSON.
- No inventes información que no esté en el texto.

Texto:
{text}
```

- [ ] **Step 2: Write the failing test**

```python
# tests/qual/test_signal_extractor.py
import json
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from agents.qual.models import Chunk
from agents.qual.signal_extractor import SignalExtractor

SCHEMA_PATH = Path(__file__).parent.parent.parent / "rga-copilot/agents/qual/config/nama_signals.yaml"

MOCK_RESPONSE = json.dumps({
    "tipo_empresa": "Restaurantero japonés",
    "posicionamiento": "Gama media-alta",
    "fortalezas": ["Calidad del producto del mar"],
    "riesgos": ["Insumos importados"],
    "factores_crecimiento": ["Expansión a Morelia"],
    "temas_topicos": ["sushi", "teppanyaki"],
    "sentiment_score": 0.7,
})


def _make_mock_client(response_text: str):
    mock_content = MagicMock()
    mock_content.text = response_text
    mock_message = MagicMock()
    mock_message.content = [mock_content]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message
    return mock_client


def test_extract_returns_dict_with_all_schema_keys():
    client = _make_mock_client(MOCK_RESPONSE)
    extractor = SignalExtractor(schema_path=str(SCHEMA_PATH), claude_client=client)
    chunks = [Chunk(text="texto de prueba", source_path="doc.md", chunk_index=0)]
    result = extractor.extract(chunks)
    assert isinstance(result, dict)
    for key in ["tipo_empresa", "posicionamiento", "fortalezas", "riesgos",
                 "factores_crecimiento", "temas_topicos", "sentiment_score"]:
        assert key in result


def test_extract_truncates_text_at_50000_chars():
    client = _make_mock_client(MOCK_RESPONSE)
    extractor = SignalExtractor(schema_path=str(SCHEMA_PATH), claude_client=client)
    big_text = "palabra " * 10000  # ~80000 chars
    chunks = [Chunk(text=big_text, source_path="big.txt", chunk_index=0)]
    extractor.extract(chunks)
    call_args = client.messages.create.call_args
    prompt_sent = call_args[1]["messages"][0]["content"]
    assert len(prompt_sent) < 55000  # prompt + template overhead


def test_extract_returns_empty_dict_on_malformed_json():
    client = _make_mock_client("Este no es JSON válido")
    extractor = SignalExtractor(schema_path=str(SCHEMA_PATH), claude_client=client)
    chunks = [Chunk(text="texto", source_path="doc.txt", chunk_index=0)]
    result = extractor.extract(chunks)
    assert result == {}
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd rga-copilot
pytest ../tests/qual/test_signal_extractor.py -v
```

Expected: `ModuleNotFoundError: No module named 'agents.qual.signal_extractor'`

- [ ] **Step 4: Write minimal implementation**

```python
# rga-copilot/agents/qual/signal_extractor.py
import json
import logging
from pathlib import Path
import yaml
from anthropic import Anthropic
from agents.qual.models import Chunk

logger = logging.getLogger(__name__)
MAX_TEXT_CHARS = 50_000
PROMPT_TEMPLATE = (Path(__file__).parent / "prompts" / "signal_extraction.txt").read_text(encoding="utf-8")


class SignalExtractor:
    def __init__(self, schema_path: str, claude_client: Anthropic):
        self.schema = yaml.safe_load(open(schema_path, encoding="utf-8"))
        self.client = claude_client

    def _build_schema_keys(self) -> str:
        return "\n".join(
            f"- \"{s['key']}\": {s['type']}" for s in self.schema["signals"]
        )

    def extract(self, chunks: list[Chunk]) -> dict:
        full_text = "\n\n".join(c.text for c in chunks)[:MAX_TEXT_CHARS]
        prompt = PROMPT_TEMPLATE.format(
            schema_keys=self._build_schema_keys(),
            text=full_text,
        )
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return json.loads(response.content[0].text)
        except json.JSONDecodeError:
            logger.warning("Claude returned malformed JSON during signal extraction.")
            return {}
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd rga-copilot
pytest ../tests/qual/test_signal_extractor.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add rga-copilot/agents/qual/prompts/signal_extraction.txt rga-copilot/agents/qual/signal_extractor.py tests/qual/test_signal_extractor.py
git commit -m "feat: add signal extractor with configurable client schema and Claude integration"
```

---

### Task 9: Prompts + summarizer.py

**Files:**
- Create: `rga-copilot/agents/qual/prompts/summary.txt`
- Create: `rga-copilot/agents/qual/summarizer.py`
- Create: `tests/qual/test_summarizer.py`

- [ ] **Step 1: Create summary prompt templates**

```
# rga-copilot/agents/qual/prompts/summary.txt — Call 1: signals paragraph
Basándote en las siguientes señales extraídas de documentos cualitativos de la empresa,
escribe un párrafo ejecutivo conciso (3-5 oraciones) en español que describa el perfil
de la empresa, sus fortalezas clave y sus principales riesgos.
No inventes información. Usa únicamente los datos proporcionados.

Señales:
{signals_json}
```

- [ ] **Step 1b: Create key quote prompt**

```
# rga-copilot/agents/qual/prompts/key_quote.txt
Del siguiente texto, extrae la frase o cita más representativa de la identidad,
propuesta de valor o situación estratégica de la empresa.
Devuelve ÚNICAMENTE la cita, sin comillas adicionales, sin explicación.
Máximo 2 oraciones.

Texto:
{text}
```

- [ ] **Step 2: Write the failing test**

```python
# tests/qual/test_summarizer.py
from unittest.mock import MagicMock
from agents.qual.models import Chunk
from agents.qual.summarizer import Summarizer


def _make_mock_client(responses: list[str]):
    """Returns a mock client that yields responses in order."""
    call_count = {"n": 0}
    def create(**kwargs):
        mock_content = MagicMock()
        mock_content.text = responses[call_count["n"]]
        mock_message = MagicMock()
        mock_message.content = [mock_content]
        call_count["n"] += 1
        return mock_message
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = create
    return mock_client


def test_generate_returns_paragraph_and_quote():
    client = _make_mock_client([
        "Grupo NAMA es un operador restaurantero sólido con fuerte presencia en Querétaro.",
        "compartir lo mejor del mar a través de técnicas japonesas",
    ])
    summarizer = Summarizer(claude_client=client)
    signals = {"fortalezas": ["calidad"], "sentiment_score": 0.7}
    chunks = [Chunk(text="texto de ejemplo", source_path="doc.md", chunk_index=0)]
    result = summarizer.generate(signals, chunks)
    assert "Grupo NAMA" in result
    assert ">" in result   # Markdown blockquote for the key quote
    assert client.messages.create.call_count == 2


def test_generate_makes_exactly_two_claude_calls():
    client = _make_mock_client(["párrafo", "cita"])
    summarizer = Summarizer(claude_client=client)
    summarizer.generate({}, [Chunk(text="x", source_path="f.txt", chunk_index=0)])
    assert client.messages.create.call_count == 2
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd rga-copilot
pytest ../tests/qual/test_summarizer.py -v
```

Expected: `ModuleNotFoundError: No module named 'agents.qual.summarizer'`

- [ ] **Step 4: Write minimal implementation**

```python
# rga-copilot/agents/qual/summarizer.py
import json
from pathlib import Path
from anthropic import Anthropic
from agents.qual.models import Chunk

_PROMPTS = Path(__file__).parent / "prompts"
_SUMMARY_TEMPLATE = (_PROMPTS / "summary.txt").read_text(encoding="utf-8")
_QUOTE_TEMPLATE = (_PROMPTS / "key_quote.txt").read_text(encoding="utf-8")
MAX_RAW_CHARS = 50_000


class Summarizer:
    def __init__(self, claude_client: Anthropic):
        self.client = claude_client

    def _call(self, prompt: str) -> str:
        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    def generate(self, signals: dict, chunks: list[Chunk]) -> str:
        signals_prompt = _SUMMARY_TEMPLATE.format(signals_json=json.dumps(signals, ensure_ascii=False, indent=2))
        paragraph = self._call(signals_prompt)

        raw_text = "\n\n".join(c.text for c in chunks)[:MAX_RAW_CHARS]
        quote_prompt = _QUOTE_TEMPLATE.format(text=raw_text)
        key_quote = self._call(quote_prompt)

        return f"{paragraph}\n\n> {key_quote}"
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd rga-copilot
pytest ../tests/qual/test_summarizer.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add rga-copilot/agents/qual/prompts/ rga-copilot/agents/qual/summarizer.py tests/qual/test_summarizer.py
git commit -m "feat: add summarizer with signals paragraph and key quote extraction"
```

---

### Task 10: agent.py — QualAgent orchestration

**Files:**
- Create: `rga-copilot/agents/qual/agent.py`
- Create: `tests/qual/test_agent.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/qual/test_agent.py
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from agents.qual.models import QualDoc, Alert, Chunk
from agents.qual.embedder import EmbedderBase, ChromaStore
from agents.qual.agent import QualAgent

SCHEMA_PATH = str(Path(__file__).parent.parent.parent / "rga-copilot/agents/qual/config/nama_signals.yaml")
NAMA_DOC = str(Path(__file__).parent.parent.parent / "rga-copilot/agents/qual/Grupo_NAMA_Overview_RGA.md")


class FakeEmbedder(EmbedderBase):
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 384 for _ in texts]


def _make_mock_claude(signals_json: str, summary_text: str, quote_text: str):
    call_count = {"n": 0}
    responses = [signals_json, summary_text, quote_text]
    def create(**kwargs):
        mock_content = MagicMock()
        mock_content.text = responses[min(call_count["n"], len(responses) - 1)]
        mock_msg = MagicMock()
        mock_msg.content = [mock_content]
        call_count["n"] += 1
        return mock_msg
    mock = MagicMock()
    mock.messages.create.side_effect = create
    return mock


def test_qual_agent_run_returns_qual_output():
    import json
    signals = json.dumps({
        "tipo_empresa": "Restaurantero",
        "posicionamiento": "Gama media-alta",
        "fortalezas": ["Calidad del mar"],
        "riesgos": ["Insumos importados"],
        "factores_crecimiento": ["Expansión"],
        "temas_topicos": ["sushi"],
        "sentiment_score": 0.7,
    })
    claude = _make_mock_claude(signals, "Párrafo ejecutivo.", "cita clave del documento")

    with tempfile.TemporaryDirectory() as tmpdir:
        store = ChromaStore(persist_path=tmpdir, collection_name="test", embedder=FakeEmbedder())
        agent = QualAgent(schema_path=SCHEMA_PATH, chroma_store=store, claude_client=claude)
        docs = [QualDoc(path=NAMA_DOC)]
        result = agent.run(docs=docs, quant_alerts=[])

    assert result.sentiment == 0.7
    assert result.chunks_stored > 0
    assert result.hypotheses == []
    assert "Párrafo" in result.summary
    assert ">" in result.summary


def test_qual_agent_run_with_no_docs_returns_empty_output():
    claude = _make_mock_claude("{}", "", "")
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ChromaStore(persist_path=tmpdir, collection_name="test2", embedder=FakeEmbedder())
        agent = QualAgent(schema_path=SCHEMA_PATH, chroma_store=store, claude_client=claude)
        result = agent.run(docs=[], quant_alerts=[])

    assert result.chunks_stored == 0
    assert result.hypotheses == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd rga-copilot
pytest ../tests/qual/test_agent.py -v
```

Expected: `ModuleNotFoundError: No module named 'agents.qual.agent'`

- [ ] **Step 3: Write minimal implementation**

```python
# rga-copilot/agents/qual/agent.py
from anthropic import Anthropic
from agents.qual.models import QualDoc, Alert, QualOutput
from agents.qual.embedder import ChromaStore
from agents.qual import doc_processor, cleaner, chunker
from agents.qual.signal_extractor import SignalExtractor
from agents.qual.summarizer import Summarizer


class QualAgent:
    def __init__(self, schema_path: str, chroma_store: ChromaStore, claude_client: Anthropic):
        self.chroma_store = chroma_store
        self.signal_extractor = SignalExtractor(schema_path, claude_client)
        self.summarizer = Summarizer(claude_client)

    def run(self, docs: list[QualDoc], quant_alerts: list[Alert]) -> QualOutput:
        all_chunks = []
        for doc in docs:
            processed = doc_processor.process(doc)
            if not processed.raw_text:
                continue
            cleaned = cleaner.clean(processed.raw_text)
            chunks = chunker.chunk(cleaned, source_path=doc.path)
            all_chunks.extend(chunks)

        chunks_stored = self.chroma_store.store(all_chunks) if all_chunks else 0
        signals = self.signal_extractor.extract(all_chunks) if all_chunks else {}
        summary = self.summarizer.generate(signals, all_chunks) if all_chunks else ""

        return QualOutput(
            signals=signals,
            sentiment=float(signals.get("sentiment_score", 0.0)),
            hypotheses=[],
            summary=summary,
            chunks_stored=chunks_stored,
        )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd rga-copilot
pytest ../tests/qual/test_agent.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
cd rga-copilot
pytest ../tests/qual/ -v
```

Expected: all tests across all test files PASS.

- [ ] **Step 6: Commit**

```bash
git add rga-copilot/agents/qual/agent.py tests/qual/test_agent.py
git commit -m "feat: add QualAgent orchestrator — complete base implementation"
```

---

### Task 11: Smoke test with real NAMA document

This is a manual verification step to confirm the agent works end-to-end with real Claude API calls.

**Files:**
- Create: `rga-copilot/scripts/smoke_test_qual.py`

- [ ] **Step 1: Set your Anthropic API key**

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

- [ ] **Step 2: Create smoke test script**

```python
# rga-copilot/scripts/smoke_test_qual.py
import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from anthropic import Anthropic
from agents.qual.models import QualDoc
from agents.qual.embedder import SentenceTransformerEmbedder, ChromaStore
from agents.qual.agent import QualAgent

SCHEMA_PATH = "agents/qual/config/nama_signals.yaml"
NAMA_DOC = "agents/qual/Grupo_NAMA_Overview_RGA.md"

client = Anthropic()
embedder = SentenceTransformerEmbedder()
store = ChromaStore(
    persist_path="data/vector_store",
    collection_name="nama",
    embedder=embedder,
)
agent = QualAgent(schema_path=SCHEMA_PATH, chroma_store=store, claude_client=client)

result = agent.run(docs=[QualDoc(path=NAMA_DOC)], quant_alerts=[])

print(f"\n=== QualOutput ===")
print(f"Sentiment: {result.sentiment}")
print(f"Chunks stored: {result.chunks_stored}")
print(f"\nSignals:")
for k, v in result.signals.items():
    print(f"  {k}: {v}")
print(f"\nSummary:\n{result.summary}")
```

- [ ] **Step 3: Run the smoke test**

```bash
cd rga-copilot
python scripts/smoke_test_qual.py
```

Expected: signals dict with all 7 NAMA keys populated, sentiment between -1 and 1, summary with paragraph and blockquote, chunks_stored > 0.

- [ ] **Step 4: Commit smoke test script**

```bash
git add rga-copilot/scripts/smoke_test_qual.py
git commit -m "chore: add QualAgent smoke test script for manual verification"
```
