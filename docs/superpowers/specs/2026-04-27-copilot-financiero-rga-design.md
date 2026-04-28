# Copilot Financiero Multiagente — RGA / FLI Holdings

**Proyecto:** Copilot Financiero para Roque Gardea Asociados  
**Cliente piloto:** Restaurante de comida japonesa (5 sucursales A–E)  
**Fecha:** 2026-04-27  
**Equipo:** Equipo 5 — Tecnológico de Monterrey Campus Guadalajara  
**Deadline:** 10 semanas desde 2026-04-27 (entrega ~2026-07-05)

---

## 1. Objetivo

Sistema multiagente que integra análisis cuantitativo (Excel financiero) con análisis cualitativo (PDFs, audio, notas) para producir recomendaciones ejecutivas accionables, señales priorizadas y escenarios what-if sobre los estados financieros del cliente.

---

## 2. Datos disponibles

**Archivo:** `TEC SG - GN (Interno).xlsx`  
**Períodos:** Enero–Abril 2026

| Hoja | Descripción | Filas útiles |
|------|-------------|--------------|
| BD 2026 | Transaccional por producto/sucursal | 1,482 (filtradas de 2,678) |
| GASTOS 2026 | Gastos operativos por categoría/sucursal | 192 |
| NÓMINA 2026 | Nómina por concepto/sucursal | 24 |
| Glosario ER | Catálogo de líneas, categorías, sucursales | — |

**Issues conocidos:**
- 44.7% de filas son placeholders (SUBTOTAL=0, CANTIDAD=0) — filtrar antes de cualquier análisis
- Margen bruto real post-filtrado: ~70% (vs 39% con placeholders)
- 8 productos con utilidad negativa (-$10.5K total, mayoría cortesías)
- Pipeline debe ser incremental: nuevos meses se agregan sin reprocesar histórico

**Insights EDA relevantes al diseño:**
- Sucursal A lidera: $3.16M (35% total), ticket más alto
- Sucursal D más débil: $470K (5.2%), margen más bajo → alerta prioritaria
- Alimentos = 77% de ingresos; Destilados/Vinos tienen margen 23–30% vs 44–48% en Alimentos/Bebidas
- Producto estrella: YAKIMESHI MIXTO ($416K, 77% margen)

---

## 3. Arquitectura — Opción elegida: Pipeline Modular

Cada agente es un módulo Python con contratos Pydantic claros. El orquestador llama módulos en secuencia. Sin framework de orquestación (no LangGraph/CrewAI) para mantener la complejidad acorde al nivel del equipo y el timeline.

```
rga-copilot/
├── pipeline/
│   ├── ingestion.py       # Lee 4 hojas del Excel
│   ├── cleaning.py        # Filtra placeholders, renombra cols, deriva variables
│   ├── validation.py      # Valida sum(Nivel3)==Nivel2==Nivel1
│   └── kpi_engineering.py # Calcula KPIs por período
├── agents/
│   ├── quant/
│   │   ├── agent.py       # QuantAgent.run(period, db) → QuantOutput
│   │   ├── kpi_calculator.py
│   │   ├── alert_detector.py
│   │   ├── forecaster.py  # Regresión lineal ingresos mensuales
│   │   └── prompts/
│   ├── qual/
│   │   ├── agent.py       # QualAgent.run(docs, alerts) → QualOutput
│   │   ├── doc_processor.py  # OCR, Whisper, PyMuPDF
│   │   ├── embedder.py    # Chunking + ChromaDB
│   │   ├── signal_extractor.py  # Claude structured extraction
│   │   ├── sentiment.py
│   │   └── prompts/
│   └── synth/
│       ├── agent.py       # SynthAgent.run(quant, qual) → SynthOutput
│       ├── scenario_builder.py  # Cálculo determinístico, no LLM
│       ├── memo_generator.py    # Jinja2 + Claude narrativa + WeasyPrint PDF
│       └── prompts/
├── orchestrator.py        # run_analysis() llama pipeline → quant → qual → synth
├── api/
│   ├── main.py            # FastAPI app
│   ├── routes/
│   └── schemas/
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── QuantPanel/
│       │   ├── QualPanel/
│       │   └── ExecPanel/
│       └── pages/
├── data/
│   ├── raw/               # Excels originales
│   ├── processed/         # DuckDB .duckdb file
│   └── vector_store/      # ChromaDB embeddings
└── tests/
```

---

## 4. Pipeline de Datos

```python
# pipeline/ingestion.py
def load_excel(path: str) -> RawData:
    bd       = pd.read_excel(path, sheet_name='BD 2026')
    gastos   = pd.read_excel(path, sheet_name='GASTOS 2026')
    nomina   = pd.read_excel(path, sheet_name='NÓMINA 2026')
    glosario = pd.read_excel(path, sheet_name='Glosario ER')
    return RawData(bd=bd, gastos=gastos, nomina=nomina, glosario=glosario)

# pipeline/cleaning.py
def clean_bd(bd: pd.DataFrame) -> pd.DataFrame:
    # 1. Drop: FECHA VENTA, COL ESPECIAL 2-6
    # 2. Rename: COL ESPECIAL 1 → CATEGORÍA MENÚ, LÍNEA DE NEGOCIO → SUCURSAL
    # 3. Filter: SUBTOTAL > 0 (elimina 44.7% placeholders)
    # 4. Derive: PRECIO_UNITARIO = SUBTOTAL/CANTIDAD, COSTO_UNITARIO = COSTO_TOTAL/CANTIDAD
    # 5. Normalizar: montos en MXN, períodos etiquetados desde columna MES
```

**Almacenamiento:** DuckDB local (`.duckdb` por cliente). Incremental: nuevos períodos se insertan con `INSERT OR IGNORE`.

**Modelos Pydantic de contrato entre módulos:**
```python
class RawData(BaseModel): ...
class CleanData(BaseModel): ...
class PeriodKPIs(BaseModel): ...
class QuantOutput(BaseModel): ...
class QualOutput(BaseModel): ...
class SynthOutput(BaseModel): ...
class AnalysisResult(BaseModel): ...
```

---

## 5. Agente QUANT

**Responsabilidad:** Análisis numérico completo de un período.

**Input:** `period: str`, `db: DuckDBConn`  
**Output:** `QuantOutput`

**KPIs calculados:**

| KPI | Fórmula | Fuente |
|-----|---------|--------|
| Margen bruto por sucursal | Utilidad Bruta / Subtotal | BD 2026 |
| Contribución marginal por SKU | Subtotal - COSTO TOTAL SIN IVA | BD 2026 |
| EBITDA aprox por sucursal | Utilidad Bruta - Gastos - Nómina | BD + GASTOS + NÓMINA |
| Ticket promedio | Subtotal / count(transacciones) | BD 2026 |
| % nómina / ingresos | Nómina total / Subtotal total | NÓMINA + BD |
| Ranking contribución marginal | top N productos por (Subtotal - Costo) | BD 2026 |

**Alertas (umbrales configurables):**
- Sucursal margen bruto < 15% → alerta roja
- Producto utilidad bruta < 0 → lista de alertas
- Nómina > 35% de ingresos por sucursal → alerta
- EBITDA negativo por sucursal → alerta roja

**Forecast:** regresión lineal (`sklearn.LinearRegression`) sobre ingresos mensuales históricos. Con Ene–Abr disponibles → proyecta Mayo 2026.

**Narrativa:** Claude Sonnet recibe el JSON de KPIs y alertas → genera párrafo ejecutivo en español.

```python
class QuantOutput(BaseModel):
    period: str
    kpis: dict
    alerts: list[Alert]
    forecast: dict          # {"MAYO 2026": 9_200_000}
    narrative: str
    top_products: list[ProductKPI]
```

---

## 6. Agente QUAL

**Responsabilidad:** Procesar documentos cualitativos y generar contexto narrativo.

**Input:** `docs: list[QualDoc]`, `quant_alerts: list[Alert]`  
**Output:** `QualOutput`

**Pipeline de documentos:**
```
Input → detectar tipo
  PDF   → PyMuPDF → texto
  imagen → OCR (pytesseract) → validación Claude Vision
  audio  → Whisper → transcripción texto
  texto  → directo
→ Limpieza: minúsculas, normalizar espacios/números, quitar boilerplate
→ Chunking: ~500 tokens, overlap 50 tokens
→ Embeddings: `text-embedding-3-small` (OpenAI API) → almacenar en ChromaDB
```

**Extracción de señales (Claude structured output):**
```python
SIGNALS_SCHEMA = {
    "tipo_empresa": str,
    "posicionamiento": str,
    "fortalezas": list[str],
    "riesgos": list[str],
    "factores_crecimiento": list[str],
    "temas_topicos": list[str],
    "sentiment_score": float,   # -1.0 a 1.0
}
```

**RAG para hipótesis:** cuando QUANT produce alerta (ej. "Sucursal D margen bajo") → QUAL hace similarity search en ChromaDB sobre Sucursal D → Claude genera hipótesis explicativa con contexto recuperado.

**Formatos de input aceptados:** PDF, PNG/JPG, MP3/WAV, TXT/MD.

```python
class QualOutput(BaseModel):
    signals: dict            # SIGNALS_SCHEMA
    sentiment: float
    hypotheses: list[str]    # una por alerta QUANT relevante
    summary: str             # resumen ejecutivo cualitativo
```

---

## 7. Agente EXEC (Sintetizador)

**Responsabilidad:** Cruzar QUANT + QUAL → recomendaciones ejecutivas priorizadas.

**Input:** `quant: QuantOutput`, `qual: QualOutput`  
**Output:** `SynthOutput`

**Top 3 señales:** Claude recibe ambos outputs completos → selecciona y narra las 3 señales de mayor impacto con evidencia cuanti + cuali.

**Escenarios what-if (cálculo determinístico, sin LLM):**
```python
class Scenario(BaseModel):
    name: str           # "Salmón +15%"
    variable: str       # "costo_insumo"
    delta_pct: float    # 0.15
    affected_category: str  # "MAKIS"
    impact_on_ebitda: float  # calculado sobre datos reales

# Escenarios predefinidos (ajustables desde UI):
# 1. Costo insumo +X% en categoría Y → impacto margen → impacto EBITDA
# 2. Cierre sucursal D → redistribución gastos fijos + pérdida de ingresos
# 3. Cambio en mix de productos (shift % entre categorías)
```

**Memo ejecutivo:** template Jinja2 con secciones fijas + narrativa Claude + exportación PDF (WeasyPrint).

```
Secciones del memo:
1. Resumen del período
2. Top 3 señales (cuanti + cuali)
3. Escenarios simulados
4. Recomendaciones priorizadas (matriz 2x2 impacto/facilidad)
5. Próximos pasos
```

```python
class SynthOutput(BaseModel):
    signals: list[Signal]
    scenarios: list[Scenario]
    recommendations: list[str]
    memo_html: str
    memo_pdf_path: str
```

---

## 8. Orquestador

```python
# orchestrator.py
def run_analysis(excel_path: str, qual_docs: list[str], period: str) -> AnalysisResult:
    db    = pipeline.ingest_and_clean(excel_path)
    quant = QuantAgent().run(period, db)
    qual  = QualAgent().run(qual_docs, quant.alerts)
    synth = SynthAgent().run(quant, qual)
    return AnalysisResult(quant=quant, qual=qual, synth=synth)
```

Sin estado global. Cada `run_analysis()` es idempotente dado los mismos inputs.

---

## 9. API (FastAPI)

```
POST /analyze              # body: {excel_path, qual_docs, period} → {job_id}
GET  /results/{job_id}     # polling → AnalysisResult JSON
GET  /kpis/{period}        # KPIs de período específico desde DuckDB
POST /scenario             # body: Scenario → {impact_on_ebitda}
GET  /memo/{job_id}/pdf    # stream del PDF generado
```

Ejecución asíncrona con `BackgroundTasks` de FastAPI. Job state almacenado en memoria (MVP) o SQLite.

---

## 10. Frontend (React + TypeScript)

**3 paneles, 1 página por panel:**

| Panel | Componentes clave |
|-------|-------------------|
| QUANT | BarChart revenue por sucursal, LineChart forecast, tabla top productos, badges de alertas |
| QUAL | Sentiment gauge, lista señales extraídas, lista hipótesis, texto resumen |
| EXEC | Cards top 3 señales, simulador what-if con sliders, tabla recomendaciones, botón "Descargar Memo PDF" |

**Stack:** React 18 + TypeScript + Vite + Recharts + shadcn/ui + Zustand.

---

## 11. Stack Tecnológico

| Componente | Tecnología |
|------------|-----------|
| Lenguaje | Python 3.11+ |
| LLM | Claude Sonnet (API Anthropic) |
| Base de datos analítica | DuckDB |
| Vector store (RAG) | ChromaDB (local) + OpenAI `text-embedding-3-small` |
| Audio → texto | OpenAI Whisper |
| OCR | pytesseract + Claude Vision (validación) |
| PDF parsing | PyMuPDF |
| API | FastAPI |
| Frontend | React 18 + TypeScript + Vite |
| Visualizaciones | Recharts |
| UI components | shadcn/ui |
| Estado frontend | Zustand |
| Exportación PDF | WeasyPrint + Jinja2 |
| Hosting MVP | Railway o Render |

---

## 12. Plan de Sprints

| Sprint | Semanas | Objetivo | Entregable |
|--------|---------|----------|------------|
| 0 | 1–2 | Pipeline ingesta + DuckDB con Ene–Abr | Dataset limpio + pipeline funcional |
| 1 | 3–4 | QuantAgent operativo | KPIs + alertas + forecast + narrativa Claude |
| 2 | 5–6 | QualAgent con RAG | ChromaDB + señales + hipótesis |
| 3 | 7–8 | SynthAgent + Orquestador + FastAPI | Sistema end-to-end + memo PDF |
| 4 | 9–10 | Dashboard React + deploy | Demo con RGA |

---

## 13. KPIs de Éxito

**Técnicos:**
- Error forecast ventas < 15% vs real
- Latencia `/analyze` < 10 segundos
- Cobertura: > 95% registros reales procesados

**Negocio:**
- ≥ 3 recomendaciones validadas por CFOaaS en primera sesión
- Director no técnico entiende señales sin explicación adicional
- Memo generado < 2 minutos desde carga del Excel

---

## 14. Riesgos

| Riesgo | Prob | Impacto | Mitigación |
|--------|------|---------|-----------|
| Excel con hojas vacías/errores | Alta | Alto | Pipeline tolerante; `errors='ignore'` en openpyxl |
| Solo un mes de datos al inicio | Alta | Alto | Pipeline incremental desde Sprint 0 |
| Audio de baja calidad | Media | Medio | Fallback a texto libre si Whisper falla |
| Alucinaciones LLM en cifras | Media | Alto | Narrativa Claude solo describe JSON calculado; cifras nunca las inventa el LLM |
| Timeline ajustado | Media | Alto | Sprint 0 prioriza datos limpios; todo lo demás depende de datos correctos |
