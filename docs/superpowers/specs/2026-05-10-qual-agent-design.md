# QualAgent — Diseño Detallado

**Proyecto:** Copilot Financiero Multiagente — RGA / FLI Holdings  
**Componente:** `agents/qual/`  
**Fecha:** 2026-05-10  
**Equipo:** Equipo 5 — Tecnológico de Monterrey Campus Guadalajara  
**Sesión:** Sprint 2 — Base del QualAgent (local, sin RAG)

---

## 1. Alcance de esta sesión

Esta spec cubre la implementación base del QualAgent. Lo siguiente queda **diferido** a sesiones futuras:

| Diferido | Razón |
|---|---|
| Ingesta de audio (Whisper) | No hay documentos de audio disponibles en el piloto actual |
| RAG + generación de hipótesis | Requiere integración con QuantAgent; se aborda en Sprint 2 completo |
| Claude Vision para validación OCR | pytesseract es suficiente para el MVP |
| Deduplicación en ChromaDB | No crítico mientras los docs fuente no cambien frecuentemente |

**Tipos de documentos soportados en esta sesión:** PDF, imagen (PNG/JPG), texto/Markdown.

---

## 2. Responsabilidad del QualAgent

Procesar documentos cualitativos de un cliente, extraer señales estructuradas mediante Claude y producir un `QualOutput` que el SynthAgent puede consumir.

**Input:** `docs: list[QualDoc]`, `quant_alerts: list[Alert]`  
**Output:** `QualOutput`

`quant_alerts` se recibe pero no se usa en esta sesión (se usará para RAG en la siguiente).

---

## 3. Estructura de archivos

```
agents/qual/
├── agent.py                  # QualAgent — único punto de entrada, método run()
├── doc_processor.py          # Detecta tipo → extrae texto crudo por documento
├── cleaner.py                # Normalización de texto
├── chunker.py                # División en chunks con overlap
├── embedder.py               # EmbedderBase interface + SentenceTransformerEmbedder + ChromaStore
├── signal_extractor.py       # Carga schema cliente → extracción estructurada con Claude
├── summarizer.py             # Dos llamadas Claude: párrafo señales + cita clave
├── prompts/
│   ├── signal_extraction.txt # Prompt template para extracción de señales
│   └── summary.txt           # Prompt template para resumen ejecutivo
└── config/
    └── nama_signals.yaml     # Schema de señales para cliente NAMA
```

---

## 4. Contratos Pydantic

```python
class QualDoc(BaseModel):
    path: str
    doc_type: Literal["pdf", "image", "text"] | None = None  # auto-detectado si None

class Chunk(BaseModel):
    text: str
    source_path: str      # archivo origen
    chunk_index: int      # posición dentro del archivo

class ProcessedDoc(BaseModel):
    raw_text: str
    chunks: list[Chunk]
    source_path: str
    doc_type: str

class QualOutput(BaseModel):
    signals: dict             # keys definidas por schema del cliente
    sentiment: float          # extraído de signals["sentiment_score"], rango -1.0 a 1.0
    hypotheses: list[str]     # lista vacía en esta sesión (RAG diferido)
    summary: str              # párrafo de señales + cita clave del texto
    chunks_stored: int        # chunks almacenados en ChromaDB en esta ejecución
```

---

## 5. Schema de señales por cliente (YAML)

El schema es configurable por cliente. El QualAgent recibe la ruta al archivo YAML en su constructor.

```yaml
# config/nama_signals.yaml
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

Para añadir un cliente nuevo: crear `config/<cliente>_signals.yaml` con las claves relevantes. No se modifica código.

---

## 6. Pipeline de procesamiento de documentos

### 6.1 `doc_processor.py` — Extracción de texto

| Tipo | Librería | Notas |
|---|---|---|
| `.pdf` | PyMuPDF (`fitz`) | Concatena texto de todas las páginas |
| `.png` / `.jpg` | pytesseract | Si resultado < 50 chars → `LowOCRConfidenceWarning` + skip |
| `.txt` / `.md` | `open()` nativo | Lectura directa |

Auto-detección de tipo por extensión si `doc_type` no se provee en `QualDoc`.

### 6.2 `cleaner.py` — Normalización

1. Lowercase
2. Normalización unicode (accents, caracteres especiales)
3. Colapso de espacios y saltos de línea múltiples
4. Eliminación de patrones boilerplate: números de página, separadores `---`, encabezados repetidos

### 6.3 `chunker.py` — División en chunks

- Tamaño objetivo: ~500 tokens (~2,000 caracteres)
- Overlap: ~50 tokens (~200 caracteres) entre chunks consecutivos
- Output: `list[Chunk]` con `source_path` y `chunk_index` para trazabilidad

---

## 7. Embedder e interfaz swappable

### 7.1 `EmbedderBase` — interfaz

```python
class EmbedderBase(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...
```

### 7.2 Implementación por defecto: `SentenceTransformerEmbedder`

- Modelo: `paraphrase-multilingual-MiniLM-L12-v2`
- Totalmente local, sin API key, soporte nativo para español
- Para cambiar a OpenAI: implementar `OpenAIEmbedder(EmbedderBase)` y pasarlo al constructor de `ChromaStore`

### 7.3 `ChromaStore`

```python
class ChromaStore:
    def __init__(self, persist_path: str, collection_name: str, embedder: EmbedderBase): ...
    def store(self, chunks: list[Chunk]) -> int: ...  # retorna cantidad almacenada
```

- Usa `chromadb.PersistentClient` apuntando a `data/vector_store/`
- IDs de chunks: `"{source_path}::chunk-{chunk_index}"` — trazables sin metadata adicional
- `get_or_create_collection`: idempotente, no falla si la colección ya existe

---

## 8. Extracción de señales con Claude

### 8.1 `signal_extractor.py`

1. Carga el YAML del cliente → construye lista de claves esperadas
2. Concatena todos los chunks en un solo texto (truncado a 50,000 caracteres si el total excede ese límite — suficiente para los documentos del piloto NAMA)
3. Llama a Claude con un prompt que incluye el texto y las claves del schema
4. Parsea el JSON retornado → retorna `dict`

El prompt instruye a Claude a devolver **únicamente JSON válido** con exactamente las claves del schema. Si Claude devuelve texto fuera del JSON, el parser lo ignora.

### 8.2 `summarizer.py` — 2 llamadas Claude secuenciales

| Llamada | Input | Output |
|---|---|---|
| 1. Párrafo de señales | `signals dict` en JSON | Párrafo ejecutivo narrativo en español |
| 2. Cita clave | Texto crudo concatenado de los chunks | La frase más representativa del documento |

Output final de `summary`: `"{párrafo}\n\n> {cita}"` — formato Markdown listo para el frontend.

**Total de llamadas Claude por ejecución completa:** 2. Costo predecible y testeable.

---

## 9. `agent.py` — Orquestación interna

```python
class QualAgent:
    def __init__(self, schema_path: str, chroma_store: ChromaStore, claude_client: Anthropic):
        self.signal_extractor = SignalExtractor(schema_path, claude_client)
        self.summarizer = Summarizer(claude_client)
        self.chroma_store = chroma_store

    def run(self, docs: list[QualDoc], quant_alerts: list[Alert]) -> QualOutput:
        all_chunks = []
        for doc in docs:
            processed = doc_processor.process(doc)      # extrae texto
            cleaned = cleaner.clean(processed.raw_text) # normaliza
            chunks = chunker.chunk(cleaned, source_path=doc.path)
            all_chunks.extend(chunks)

        chunks_stored = self.chroma_store.store(all_chunks)
        signals = self.signal_extractor.extract(all_chunks)
        summary = self.summarizer.generate(signals, all_chunks)

        return QualOutput(
            signals=signals,
            sentiment=signals.get("sentiment_score", 0.0),
            hypotheses=[],
            summary=summary,
            chunks_stored=chunks_stored,
        )
```

Sin estado global. Cada `run()` es idempotente dado los mismos inputs.

---

## 10. Dependencias Python

```
pymupdf          # extracción PDF
pytesseract      # OCR imágenes
pillow           # requerido por pytesseract
chromadb         # vector store local
sentence-transformers  # embeddings locales multilingüe
anthropic        # Claude API
pydantic         # contratos de datos
pyyaml           # lectura de schema YAML
```

---

## 11. Consideraciones de error

| Escenario | Comportamiento |
|---|---|
| pytesseract retorna < 50 chars | `LowOCRConfidenceWarning` + doc skipped |
| PyMuPDF falla en PDF corrupto | Excepción propagada con path del archivo |
| Claude retorna JSON malformado | `json.JSONDecodeError` → loguear + retornar `signals={}` |
| ChromaDB no puede escribir en disco | Excepción propagada (problema de permisos/path) |

---

## 12. Lo que NO hace el QualAgent en esta sesión

- No genera hipótesis (RAG diferido)
- No procesa audio
- No valida OCR con Claude Vision
- No deduplica chunks si el mismo doc se ingesta dos veces
- No expone endpoint HTTP (eso lo maneja `api/`)
