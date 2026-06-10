# RGA Copilot Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an interactive React dashboard with FastAPI backend that lets users upload financial data, run the full analysis pipeline, and explore KPIs — with a customizable, slider-driven What-If Lab as the standout feature.

**Architecture:** FastAPI wraps the existing `orchestrator.run_analysis()` in a background thread; jobs are tracked in-memory. React (Vite + shadcn/ui + Tailwind) polls the job endpoint then renders KPIs and an interactive scenario sandbox where all EBITDA math runs client-side in `scenarios.ts` — no round-trip for slider updates.

**Tech Stack:** Python 3.11, FastAPI, uvicorn, React 18, Vite, TypeScript, shadcn/ui, Tailwind CSS, Recharts, Zustand, React Router v6, Vitest, pytest

---

## File Map

```
FLI Holdings/
├── api/
│   ├── main.py                  # FastAPI app factory, CORS, sys.path patch
│   ├── job_store.py             # thread-safe in-memory job registry
│   ├── routes/
│   │   ├── run.py               # POST /api/run
│   │   └── jobs.py              # GET  /api/jobs/{id}
│   └── tests/
│       ├── conftest.py          # TestClient fixture
│       ├── test_job_store.py
│       └── test_routes.py
├── dashboard/
│   ├── package.json
│   ├── vite.config.ts           # proxy /api → :8000
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx              # sidebar layout + React Router
│       ├── types/
│       │   └── analysis.ts      # TS mirrors of Python models
│       ├── store/
│       │   └── analysis.ts      # Zustand store
│       ├── lib/
│       │   ├── scenarios.ts     # client-side scenario math
│       │   └── format.ts        # currency / pct formatters
│       ├── components/
│       │   ├── MetricCard.tsx
│       │   ├── ScenarioCard.tsx
│       │   ├── WaterfallChart.tsx
│       │   └── BreakEvenCard.tsx
│       ├── pages/
│       │   ├── Setup.tsx
│       │   ├── Overview.tsx
│       │   ├── WhatIfLab.tsx
│       │   └── Memo.tsx
│       └── tests/
│           └── scenarios.test.ts
└── Makefile
```

---

## Task 1: FastAPI scaffold + job store

**Files:**
- Create: `api/main.py`
- Create: `api/job_store.py`
- Create: `api/tests/conftest.py`
- Create: `api/tests/test_job_store.py`

- [ ] **Step 1: Install FastAPI into the shared venv**

```bash
cd "rga-copilot" && .venv/bin/pip install fastapi "uvicorn[standard]" python-multipart httpx pytest-asyncio
```

Expected: packages install without error.

- [ ] **Step 2: Write failing tests for job_store**

Create `api/tests/test_job_store.py`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from job_store import create_job, get_job, update_job


def test_create_job_returns_uuid():
    job_id = create_job()
    assert len(job_id) == 36
    assert job_id.count("-") == 4


def test_new_job_status_is_pending():
    job_id = create_job()
    job = get_job(job_id)
    assert job["status"] == "pending"
    assert job["result"] is None
    assert job["error"] is None


def test_update_job_running():
    job_id = create_job()
    update_job(job_id, "running")
    assert get_job(job_id)["status"] == "running"


def test_update_job_done_with_result():
    job_id = create_job()
    update_job(job_id, "done", result={"key": "value"})
    job = get_job(job_id)
    assert job["status"] == "done"
    assert job["result"] == {"key": "value"}


def test_get_nonexistent_job_returns_none():
    assert get_job("does-not-exist") is None
```

- [ ] **Step 3: Run tests — expect failure**

```bash
cd "FLI Holdings" && rga-copilot/.venv/bin/pytest api/tests/test_job_store.py -v
```

Expected: `ModuleNotFoundError: No module named 'job_store'`

- [ ] **Step 4: Create `api/job_store.py`**

```python
import threading
import uuid
from typing import Any

_store: dict[str, dict] = {}
_lock = threading.Lock()


def create_job() -> str:
    job_id = str(uuid.uuid4())
    with _lock:
        _store[job_id] = {"status": "pending", "result": None, "error": None}
    return job_id


def update_job(job_id: str, status: str, result: Any = None, error: str | None = None) -> None:
    with _lock:
        _store[job_id] = {"status": status, "result": result, "error": error}


def get_job(job_id: str) -> dict | None:
    with _lock:
        return _store.get(job_id)
```

- [ ] **Step 5: Create `api/main.py`**

```python
import sys
from pathlib import Path

# Must come before any rga-copilot imports
sys.path.insert(0, str(Path(__file__).parent.parent / "rga-copilot"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.run import router as run_router
from routes.jobs import router as jobs_router

app = FastAPI(title="RGA Copilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(run_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
```

- [ ] **Step 6: Create empty route files so imports resolve**

Create `api/routes/__init__.py` (empty).

Create `api/routes/run.py`:

```python
from fastapi import APIRouter
router = APIRouter()
```

Create `api/routes/jobs.py`:

```python
from fastapi import APIRouter
router = APIRouter()
```

- [ ] **Step 7: Run job_store tests — expect pass**

```bash
cd "FLI Holdings" && rga-copilot/.venv/bin/pytest api/tests/test_job_store.py -v
```

Expected: 5 passed.

- [ ] **Step 8: Commit**

```bash
git add api/
git commit -m "feat(api): FastAPI scaffold + thread-safe job store"
```

---

## Task 2: POST /api/run endpoint

**Files:**
- Modify: `api/routes/run.py`
- Create: `api/tests/test_routes.py`
- Create: `api/tests/conftest.py`

- [ ] **Step 1: Create test client fixture**

Create `api/tests/conftest.py`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)
```

- [ ] **Step 2: Write failing test for POST /api/run**

Create `api/tests/test_routes.py`:

```python
import io


def test_run_returns_job_id(client, tmp_path):
    # Minimal xlsx-like bytes (real validation not needed for route test)
    fake_xlsx = io.BytesIO(b"PK fake xlsx content")
    response = client.post(
        "/api/run",
        data={
            "period": "ENERO 2026",
            "year": "2026",
            "company": "Test Co",
            "break_even_target_ebitda": "1500000",
        },
        files={"xlsx": ("test.xlsx", fake_xlsx, "application/vnd.ms-excel")},
    )
    assert response.status_code == 200
    body = response.json()
    assert "job_id" in body
    assert len(body["job_id"]) == 36


def test_run_job_starts_as_pending_or_running(client, tmp_path):
    fake_xlsx = io.BytesIO(b"PK fake xlsx content")
    run_resp = client.post(
        "/api/run",
        data={"period": "ENERO 2026", "year": "2026"},
        files={"xlsx": ("test.xlsx", fake_xlsx, "application/vnd.ms-excel")},
    )
    job_id = run_resp.json()["job_id"]
    status_resp = client.get(f"/api/jobs/{job_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] in ("pending", "running", "error")
```

- [ ] **Step 3: Run — expect failure**

```bash
cd "FLI Holdings" && rga-copilot/.venv/bin/pytest api/tests/test_routes.py -v
```

Expected: `422 Unprocessable Entity` or route not found errors.

- [ ] **Step 4: Implement `api/routes/run.py`**

```python
import os
import sys
import tempfile
import threading
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "rga-copilot"))

from job_store import create_job, update_job

router = APIRouter()


@router.post("/run")
async def run_analysis(
    xlsx: UploadFile = File(...),
    qual_docs: list[UploadFile] = File(default=[]),
    period: str = Form(...),
    year: int = Form(...),
    company: str = Form(default="Grupo Nama"),
    break_even_target_ebitda: float = Form(default=1_500_000.0),
):
    job_id = create_job()

    tmp_dir = tempfile.mkdtemp()
    xlsx_bytes = await xlsx.read()
    xlsx_path = os.path.join(tmp_dir, xlsx.filename or "data.xlsx")
    with open(xlsx_path, "wb") as f:
        f.write(xlsx_bytes)

    qual_paths: list[str] = []
    for doc in qual_docs:
        doc_bytes = await doc.read()
        path = os.path.join(tmp_dir, doc.filename or "doc.pdf")
        with open(path, "wb") as f:
            f.write(doc_bytes)
        qual_paths.append(path)

    def _run() -> None:
        try:
            update_job(job_id, "running")
            from orchestrator import run_analysis as _pipeline
            result = _pipeline(
                xlsx_path=xlsx_path,
                year=year,
                qual_docs=qual_paths,
                period=period,
                company=company,
                break_even_target_ebitda=break_even_target_ebitda,
            )
            update_job(job_id, "done", result=result.model_dump(mode="json"))
        except Exception as exc:
            update_job(job_id, "error", error=str(exc))

    threading.Thread(target=_run, daemon=True).start()
    return {"job_id": job_id}
```

- [ ] **Step 5: Implement `api/routes/jobs.py`**

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, HTTPException
from job_store import get_job

router = APIRouter()


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
```

- [ ] **Step 6: Run tests — expect pass**

```bash
cd "FLI Holdings" && rga-copilot/.venv/bin/pytest api/tests/ -v
```

Expected: 7 passed.

- [ ] **Step 7: Smoke-test the live server**

```bash
cd "FLI Holdings/api" && ../rga-copilot/.venv/bin/uvicorn main:app --port 8000 &
sleep 2
curl -s http://localhost:8000/api/jobs/nonexistent | python3 -m json.tool
# Expected: {"detail": "Job not found"}
kill %1
```

- [ ] **Step 8: Commit**

```bash
git add api/
git commit -m "feat(api): POST /api/run + GET /api/jobs/{id} endpoints"
```

---

## Task 3: React + Vite scaffold

**Files:**
- Create: `dashboard/` (entire Vite project)

- [ ] **Step 1: Scaffold Vite project**

```bash
cd "FLI Holdings"
npm create vite@latest dashboard -- --template react-ts
cd dashboard && npm install
```

- [ ] **Step 2: Install dependencies**

```bash
cd "FLI Holdings/dashboard"
npm install react-router-dom zustand recharts
npm install -D tailwindcss postcss autoprefixer @types/recharts
npx tailwindcss init -p
```

- [ ] **Step 3: Init shadcn/ui**

```bash
cd "FLI Holdings/dashboard"
npx shadcn@latest init
```

When prompted:
- Style: **Default**
- Base color: **Slate**
- CSS variables: **Yes**

- [ ] **Step 4: Add shadcn components**

```bash
cd "FLI Holdings/dashboard"
npx shadcn@latest add card button input label slider select sheet badge tabs table progress separator switch
```

- [ ] **Step 5: Configure Tailwind**

Replace `dashboard/tailwind.config.js` content:

```js
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
        secondary: { DEFAULT: "hsl(var(--secondary))", foreground: "hsl(var(--secondary-foreground))" },
        destructive: { DEFAULT: "hsl(var(--destructive))", foreground: "hsl(var(--destructive-foreground))" },
        muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" },
        accent: { DEFAULT: "hsl(var(--accent))", foreground: "hsl(var(--accent-foreground))" },
        card: { DEFAULT: "hsl(var(--card))", foreground: "hsl(var(--card-foreground))" },
      },
    },
  },
  plugins: [],
}
```

- [ ] **Step 6: Configure Vite proxy**

Replace `dashboard/vite.config.ts`:

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

Add `path` types: `npm install -D @types/node`

- [ ] **Step 7: Update tsconfig.json to include path alias**

In `dashboard/tsconfig.json`, inside `compilerOptions`:

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  }
}
```

- [ ] **Step 8: Verify dev server starts**

```bash
cd "FLI Holdings/dashboard" && npm run dev
```

Expected: `VITE ready at http://localhost:5173`. Stop with Ctrl+C.

- [ ] **Step 9: Commit**

```bash
cd "FLI Holdings"
git add dashboard/
git commit -m "feat(dashboard): React+Vite+shadcn+Tailwind scaffold"
```

---

## Task 4: TypeScript types + Zustand store

**Files:**
- Create: `dashboard/src/types/analysis.ts`
- Create: `dashboard/src/store/analysis.ts`
- Create: `dashboard/src/lib/format.ts`

- [ ] **Step 1: Create `dashboard/src/types/analysis.ts`**

```ts
export interface Consolidado {
  ingresos_total: number;
  utilidad_bruta_total: number;
  ebitda_total: number;
  margen_bruto_global: number;
  margen_ebitda_global: number;
  nomina_total: number;
  gastos_operativos_total: number;
  pct_nomina_ingresos_global: number;
  gastos_financieros?: number;
  utilidad_neta?: number;
}

export interface BranchKPI {
  sucursal: string;
  ingresos: number;
  costo_ventas: number;
  utilidad_bruta: number;
  margen_bruto: number;
  gastos_operativos: number;
  nomina: number;
  ebitda: number;
  pct_nomina_ingresos: number;
  ticket_promedio: number;
  transacciones: number;
}

export interface CategoryKPI {
  categoria: string;
  ingresos: number;
  costo: number;
  margen_bruto: number;
  pct_total_ingresos: number;
}

export interface ProductKPI {
  sku: string;
  categoria: string;
  sucursal: string;
  ingresos: number;
  contribucion_marginal: number;
  margen_bruto: number;
  cantidad: number;
}

export interface PeriodKPIs {
  period: string;
  consolidado: Consolidado;
  por_sucursal: BranchKPI[];
  top_productos: ProductKPI[];
  pct_mix_categoria: Record<string, number>;
  por_categoria: CategoryKPI[];
}

export interface QuantOutput {
  period: string;
  kpis: PeriodKPIs;
  alerts: Alert[];
  narrative: string;
  top_products: ProductKPI[];
}

export interface Alert {
  level: 'red' | 'warning';
  tipo: string;
  sucursal: string | null;
  sku: string | null;
  mensaje: string;
  valor: number | null;
}

export interface Signal {
  rank: number;
  titulo: string;
  evidencia_quant: string;
  evidencia_qual: string;
  recomendacion: string;
  impacto: 'alto' | 'medio' | 'bajo';
  facilidad: 'alta' | 'media' | 'baja';
}

export interface QualOutput {
  signals: Signal[];
  summary: string;
}

export interface Scenario {
  name: string;
  variable: string;
  delta_pct: number;
  affected_target: string;
  base_ebitda: number;
  impact_on_ebitda: number;
  ebitda_post: number;
}

export interface BreakEvenResult {
  sucursal: string;
  target_ebitda: number;
  current_ebitda: number;
  current_ticket: number;
  required_ticket: number;
  ticket_delta_pct: number;
  transacciones: number;
}

export interface SynthOutput {
  signals: Signal[];
  scenarios: Scenario[];
  break_even_results: BreakEvenResult[];
  recommendations: Recommendation[];
  next_steps: string;
  memo_html: string;
  memo_pdf_path: string;
}

export interface Recommendation {
  accion: string;
  impacto: 'alto' | 'medio' | 'bajo';
  facilidad: 'alta' | 'media' | 'baja';
  fuente: string;
}

export interface AnalysisResult {
  period: string;
  quant: QuantOutput;
  qual: QualOutput;
  synth: SynthOutput;
}

export type ScenarioType =
  | 'costo_insumo'
  | 'cierre_sucursal'
  | 'shift_mix'
  | 'reduccion_nomina'
  | 'incremento_salarial';

export interface ScenarioCard {
  id: string;
  type: ScenarioType;
  label: string;
  params: {
    categoria?: string;
    sucursal?: string;
    cat_from?: string;
    cat_to?: string;
    delta_pct: number;
  };
  active: boolean;
  impact: number;
}

export type JobStatus = 'idle' | 'pending' | 'running' | 'done' | 'error';
```

- [ ] **Step 2: Create `dashboard/src/store/analysis.ts`**

```ts
import { create } from 'zustand';
import type { AnalysisResult, ScenarioCard, JobStatus } from '@/types/analysis';

interface AnalysisStore {
  jobId: string | null;
  status: JobStatus;
  result: AnalysisResult | null;
  errorMessage: string | null;
  scenarios: ScenarioCard[];
  breakEvenTarget: number;

  setJob: (jobId: string) => void;
  setStatus: (status: JobStatus) => void;
  setResult: (result: AnalysisResult) => void;
  setError: (msg: string) => void;
  setScenarios: (cards: ScenarioCard[]) => void;
  updateScenario: (id: string, patch: Partial<ScenarioCard>) => void;
  addScenario: (card: ScenarioCard) => void;
  removeScenario: (id: string) => void;
  setBreakEvenTarget: (val: number) => void;
  reset: () => void;
}

export const useAnalysisStore = create<AnalysisStore>((set) => ({
  jobId: null,
  status: 'idle',
  result: null,
  errorMessage: null,
  scenarios: [],
  breakEvenTarget: 1_500_000,

  setJob: (jobId) => set({ jobId, status: 'pending' }),
  setStatus: (status) => set({ status }),
  setResult: (result) => set({ result, status: 'done' }),
  setError: (errorMessage) => set({ errorMessage, status: 'error' }),
  setScenarios: (scenarios) => set({ scenarios }),
  updateScenario: (id, patch) =>
    set((s) => ({
      scenarios: s.scenarios.map((c) => (c.id === id ? { ...c, ...patch } : c)),
    })),
  addScenario: (card) => set((s) => ({ scenarios: [...s.scenarios, card] })),
  removeScenario: (id) =>
    set((s) => ({ scenarios: s.scenarios.filter((c) => c.id !== id) })),
  setBreakEvenTarget: (breakEvenTarget) => set({ breakEvenTarget }),
  reset: () =>
    set({ jobId: null, status: 'idle', result: null, errorMessage: null, scenarios: [] }),
}));
```

- [ ] **Step 3: Create `dashboard/src/lib/format.ts`**

```ts
export const mxn = (n: number): string =>
  new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);

export const pct = (n: number, decimals = 1): string =>
  `${(n * 100).toFixed(decimals)}%`;

export const compact = (n: number): string => {
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return mxn(n);
};
```

- [ ] **Step 4: Commit**

```bash
cd "FLI Holdings"
git add dashboard/src/types/ dashboard/src/store/ dashboard/src/lib/format.ts
git commit -m "feat(dashboard): TS types, Zustand store, formatters"
```

---

## Task 5: scenarios.ts (pure math, fully tested)

**Files:**
- Create: `dashboard/src/lib/scenarios.ts`
- Create: `dashboard/src/tests/scenarios.test.ts`

- [ ] **Step 1: Install vitest**

```bash
cd "FLI Holdings/dashboard" && npm install -D vitest
```

Add to `dashboard/vite.config.ts` inside `defineConfig({...})`:

```ts
test: {
  environment: 'node',
},
```

Add to `dashboard/package.json` scripts:

```json
"test": "vitest run"
```

- [ ] **Step 2: Write failing tests**

Create `dashboard/src/tests/scenarios.test.ts`:

```ts
import { describe, it, expect } from 'vitest';
import {
  costoInsumo,
  cierreSucursal,
  shiftMix,
  reduccionNomina,
  incrementoSalarial,
  breakEvenTicket,
  computeImpact,
  initScenarioCards,
} from '@/lib/scenarios';
import type { PeriodKPIs, ScenarioCard } from '@/types/analysis';

const mockKpis = (): PeriodKPIs => ({
  period: 'ENERO 2026',
  consolidado: {
    ingresos_total: 9_000_000,
    utilidad_bruta_total: 6_300_000,
    ebitda_total: 1_800_000,
    margen_bruto_global: 0.7,
    margen_ebitda_global: 0.2,
    nomina_total: 2_000_000,
    gastos_operativos_total: 2_500_000,
    pct_nomina_ingresos_global: 0.222,
  },
  por_sucursal: [
    {
      sucursal: 'ANT',
      ingresos: 4_000_000,
      costo_ventas: 1_200_000,
      utilidad_bruta: 2_800_000,
      margen_bruto: 0.7,
      gastos_operativos: 700_000,
      nomina: 800_000,
      ebitda: 1_300_000,
      pct_nomina_ingresos: 0.2,
      ticket_promedio: 10_000,
      transacciones: 400,
    },
    {
      sucursal: 'SOK',
      ingresos: 2_500_000,
      costo_ventas: 800_000,
      utilidad_bruta: 1_700_000,
      margen_bruto: 0.68,
      gastos_operativos: 600_000,
      nomina: 700_000,
      ebitda: 400_000,
      pct_nomina_ingresos: 0.28,
      ticket_promedio: 7_000,
      transacciones: 357,
    },
  ],
  top_productos: [],
  pct_mix_categoria: {},
  por_categoria: [
    { categoria: 'MAKIS', ingresos: 5_000_000, costo: 1_500_000, margen_bruto: 0.7, pct_total_ingresos: 0.56 },
    { categoria: 'POKE', ingresos: 2_000_000, costo: 800_000, margen_bruto: 0.6, pct_total_ingresos: 0.22 },
    { categoria: 'BEBIDAS', ingresos: 2_000_000, costo: 400_000, margen_bruto: 0.8, pct_total_ingresos: 0.22 },
  ],
});

describe('costoInsumo', () => {
  it('returns -delta * costo for given category', () => {
    expect(costoInsumo(mockKpis(), 'MAKIS', 0.15)).toBeCloseTo(-225_000);
  });
  it('throws for unknown category', () => {
    expect(() => costoInsumo(mockKpis(), 'UNKNOWN', 0.1)).toThrow();
  });
});

describe('cierreSucursal', () => {
  it('returns negative of branch EBITDA', () => {
    expect(cierreSucursal(mockKpis(), 'ANT')).toBe(-1_300_000);
  });
  it('throws for unknown sucursal', () => {
    expect(() => cierreSucursal(mockKpis(), 'ZZZ')).toThrow();
  });
});

describe('shiftMix', () => {
  it('computes margin differential on cat_from revenue', () => {
    // delta_revenue = 2_000_000 * 0.05 = 100_000
    // impact = 100_000 * (0.8 - 0.6) = 20_000
    expect(shiftMix(mockKpis(), 'POKE', 'BEBIDAS', 0.05)).toBeCloseTo(20_000);
  });
  it('returns negative when shifting to lower margin', () => {
    expect(shiftMix(mockKpis(), 'BEBIDAS', 'POKE', 0.05)).toBeLessThan(0);
  });
});

describe('reduccionNomina', () => {
  it('returns positive impact (saving)', () => {
    expect(reduccionNomina(mockKpis(), 'SOK', 0.10)).toBeCloseTo(70_000);
  });
});

describe('incrementoSalarial', () => {
  it('returns negative impact (cost increase)', () => {
    expect(incrementoSalarial(mockKpis(), 0.10)).toBeCloseTo(-200_000);
  });
});

describe('breakEvenTicket', () => {
  it('computes required ticket correctly', () => {
    // ANT: target=0, gastos=700k, nomina=800k, transacciones=400, margen=0.7
    // required = (0 + 700_000 + 800_000) / (400 * 0.7) = 1_500_000 / 280 = 5_357.14
    const result = breakEvenTicket(mockKpis(), 'ANT', 0);
    expect(result.required_ticket).toBeCloseTo(5_357.14, 1);
    expect(result.current_ticket).toBe(10_000);
  });
  it('reflects target_ebitda in result', () => {
    const result = breakEvenTicket(mockKpis(), 'ANT', 500_000);
    expect(result.target_ebitda).toBe(500_000);
  });
});

describe('computeImpact', () => {
  it('recomputes impact for a costo_insumo card', () => {
    const card: ScenarioCard = {
      id: '1',
      type: 'costo_insumo',
      label: 'test',
      params: { categoria: 'MAKIS', delta_pct: 0.15 },
      active: true,
      impact: 0,
    };
    expect(computeImpact(mockKpis(), card)).toBeCloseTo(-225_000);
  });
});

describe('initScenarioCards', () => {
  it('returns 5 cards from server scenarios', () => {
    const serverScenarios = [
      { name: 'Costo insumo MAKIS +15%', variable: 'costo_insumo', delta_pct: 0.15, affected_target: 'MAKIS', base_ebitda: 1_800_000, impact_on_ebitda: -225_000, ebitda_post: 1_575_000 },
      { name: 'Cierre sucursal ANT', variable: 'cierre_sucursal', delta_pct: 1.0, affected_target: 'ANT', base_ebitda: 1_800_000, impact_on_ebitda: -1_300_000, ebitda_post: 500_000 },
      { name: 'Mix shift 5%: POKE → BEBIDAS', variable: 'shift_mix', delta_pct: 0.05, affected_target: 'POKE→BEBIDAS', base_ebitda: 1_800_000, impact_on_ebitda: 20_000, ebitda_post: 1_820_000 },
      { name: 'Reducción nómina SOK -10%', variable: 'reduccion_nomina', delta_pct: 0.10, affected_target: 'SOK', base_ebitda: 1_800_000, impact_on_ebitda: 70_000, ebitda_post: 1_870_000 },
      { name: 'Incremento salarial +10%', variable: 'incremento_salarial', delta_pct: 0.10, affected_target: 'todas las sucursales', base_ebitda: 1_800_000, impact_on_ebitda: -200_000, ebitda_post: 1_600_000 },
    ];
    const cards = initScenarioCards(serverScenarios);
    expect(cards).toHaveLength(5);
    expect(cards[0].type).toBe('costo_insumo');
    expect(cards[0].params.categoria).toBe('MAKIS');
    expect(cards[2].params.cat_from).toBe('POKE');
    expect(cards[2].params.cat_to).toBe('BEBIDAS');
  });
});
```

- [ ] **Step 3: Run tests — expect failure**

```bash
cd "FLI Holdings/dashboard" && npm test
```

Expected: `Cannot find module '@/lib/scenarios'`

- [ ] **Step 4: Create `dashboard/src/lib/scenarios.ts`**

```ts
import { v4 as uuidv4 } from 'uuid';
import type { PeriodKPIs, Scenario, ScenarioCard, ScenarioType } from '@/types/analysis';

// Install uuid: npm install uuid && npm install -D @types/uuid

// ---------------------------------------------------------------------------
// Lookup helpers
// ---------------------------------------------------------------------------

const catMap = (kpis: PeriodKPIs) =>
  Object.fromEntries(kpis.por_categoria.map((c) => [c.categoria, c]));

const branchMap = (kpis: PeriodKPIs) =>
  Object.fromEntries(kpis.por_sucursal.map((b) => [b.sucursal, b]));

// ---------------------------------------------------------------------------
// Five scenario formulas — mirror of scenario_builder.py
// ---------------------------------------------------------------------------

export function costoInsumo(kpis: PeriodKPIs, categoria: string, deltaPct: number): number {
  const cats = catMap(kpis);
  if (!cats[categoria]) throw new Error(`Categoría '${categoria}' not found`);
  return -deltaPct * cats[categoria].costo;
}

export function cierreSucursal(kpis: PeriodKPIs, sucursal: string): number {
  const branches = branchMap(kpis);
  if (!branches[sucursal]) throw new Error(`Sucursal '${sucursal}' not found`);
  return -branches[sucursal].ebitda;
}

export function shiftMix(
  kpis: PeriodKPIs,
  catFrom: string,
  catTo: string,
  deltaPct: number,
): number {
  const cats = catMap(kpis);
  if (!cats[catFrom]) throw new Error(`Categoría '${catFrom}' not found`);
  if (!cats[catTo]) throw new Error(`Categoría '${catTo}' not found`);
  const deltaRevenue = cats[catFrom].ingresos * deltaPct;
  return deltaRevenue * (cats[catTo].margen_bruto - cats[catFrom].margen_bruto);
}

export function reduccionNomina(kpis: PeriodKPIs, sucursal: string, deltaPct: number): number {
  const branches = branchMap(kpis);
  if (!branches[sucursal]) throw new Error(`Sucursal '${sucursal}' not found`);
  return branches[sucursal].nomina * deltaPct;
}

export function incrementoSalarial(kpis: PeriodKPIs, deltaPct: number): number {
  return -kpis.consolidado.nomina_total * deltaPct;
}

// ---------------------------------------------------------------------------
// Break-even solver
// ---------------------------------------------------------------------------

export function breakEvenTicket(
  kpis: PeriodKPIs,
  sucursal: string,
  targetEbitda: number,
): {
  sucursal: string;
  target_ebitda: number;
  current_ebitda: number;
  current_ticket: number;
  required_ticket: number;
  ticket_delta_pct: number;
  transacciones: number;
} {
  const b = branchMap(kpis)[sucursal];
  if (!b) throw new Error(`Sucursal '${sucursal}' not found`);
  const required =
    (targetEbitda + b.gastos_operativos + b.nomina) / (b.transacciones * b.margen_bruto);
  return {
    sucursal,
    target_ebitda: targetEbitda,
    current_ebitda: b.ebitda,
    current_ticket: b.ticket_promedio,
    required_ticket: required,
    ticket_delta_pct: (required - b.ticket_promedio) / b.ticket_promedio,
    transacciones: b.transacciones,
  };
}

// ---------------------------------------------------------------------------
// Dispatch: compute impact for any ScenarioCard
// ---------------------------------------------------------------------------

export function computeImpact(kpis: PeriodKPIs, card: ScenarioCard): number {
  const p = card.params;
  switch (card.type) {
    case 'costo_insumo':
      return costoInsumo(kpis, p.categoria!, p.delta_pct);
    case 'cierre_sucursal':
      return cierreSucursal(kpis, p.sucursal!);
    case 'shift_mix':
      return shiftMix(kpis, p.cat_from!, p.cat_to!, p.delta_pct);
    case 'reduccion_nomina':
      return reduccionNomina(kpis, p.sucursal!, p.delta_pct);
    case 'incremento_salarial':
      return incrementoSalarial(kpis, p.delta_pct);
  }
}

// ---------------------------------------------------------------------------
// Init scenario cards from server-returned scenarios
// ---------------------------------------------------------------------------

export function initScenarioCards(serverScenarios: Scenario[]): ScenarioCard[] {
  return serverScenarios.map((s) => {
    const type = s.variable as ScenarioType;
    const params: ScenarioCard['params'] = { delta_pct: s.delta_pct };

    if (type === 'costo_insumo') {
      params.categoria = s.affected_target;
    } else if (type === 'cierre_sucursal' || type === 'reduccion_nomina') {
      params.sucursal = s.affected_target;
    } else if (type === 'shift_mix') {
      const [catFrom, catTo] = s.affected_target.split('→');
      params.cat_from = catFrom;
      params.cat_to = catTo;
    }
    // incremento_salarial: affected_target is "todas las sucursales", no extra params

    return {
      id: uuidv4(),
      type,
      label: s.name,
      params,
      active: true,
      impact: s.impact_on_ebitda,
    };
  });
}
```

- [ ] **Step 5: Install uuid**

```bash
cd "FLI Holdings/dashboard" && npm install uuid && npm install -D @types/uuid
```

- [ ] **Step 6: Run tests — expect pass**

```bash
cd "FLI Holdings/dashboard" && npm test
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
cd "FLI Holdings"
git add dashboard/src/lib/scenarios.ts dashboard/src/tests/scenarios.test.ts dashboard/src/lib/format.ts dashboard/package.json
git commit -m "feat(dashboard): scenarios.ts with full test coverage"
```

---

## Task 6: App shell (layout + routing)

**Files:**
- Modify: `dashboard/src/main.tsx`
- Create: `dashboard/src/App.tsx`

- [ ] **Step 1: Update `dashboard/src/main.tsx`**

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
```

- [ ] **Step 2: Create `dashboard/src/App.tsx`**

```tsx
import { Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { useAnalysisStore } from '@/store/analysis';
import Setup from '@/pages/Setup';
import Overview from '@/pages/Overview';
import WhatIfLab from '@/pages/WhatIfLab';
import Memo from '@/pages/Memo';
import { BarChart3, FlaskConical, FileText, Settings } from 'lucide-react';

const NAV = [
  { to: '/setup', icon: Settings, label: 'Setup' },
  { to: '/overview', icon: BarChart3, label: 'Overview' },
  { to: '/whatif', icon: FlaskConical, label: 'What-If Lab' },
  { to: '/memo', icon: FileText, label: 'Memo' },
];

export default function App() {
  const status = useAnalysisStore((s) => s.status);
  const done = status === 'done';

  return (
    <div className="flex h-screen bg-background text-foreground">
      {/* Sidebar */}
      <nav className="w-56 flex-shrink-0 border-r bg-card flex flex-col pt-6 gap-1 px-2">
        <div className="px-4 mb-6">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">RGA Copilot</p>
        </div>
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2 rounded-md text-sm transition-colors
               ${isActive ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted hover:text-foreground'}
               ${!done && to !== '/setup' ? 'pointer-events-none opacity-40' : ''}`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Navigate to="/setup" replace />} />
          <Route path="/setup" element={<Setup />} />
          <Route path="/overview" element={<Overview />} />
          <Route path="/whatif" element={<WhatIfLab />} />
          <Route path="/memo" element={<Memo />} />
        </Routes>
      </main>
    </div>
  );
}
```

- [ ] **Step 3: Install lucide-react**

```bash
cd "FLI Holdings/dashboard" && npm install lucide-react
```

- [ ] **Step 4: Create stub pages** (needed so imports resolve)

Create `dashboard/src/pages/Overview.tsx`:
```tsx
export default function Overview() { return <div className="p-8">Overview</div>; }
```

Create `dashboard/src/pages/WhatIfLab.tsx`:
```tsx
export default function WhatIfLab() { return <div className="p-8">What-If Lab</div>; }
```

Create `dashboard/src/pages/Memo.tsx`:
```tsx
export default function Memo() { return <div className="p-8">Memo</div>; }
```

Create `dashboard/src/pages/Setup.tsx`:
```tsx
export default function Setup() { return <div className="p-8">Setup</div>; }
```

- [ ] **Step 5: Verify app renders**

```bash
cd "FLI Holdings/dashboard" && npm run dev
```

Open `http://localhost:5173`. Expect: sidebar with 4 nav items, Setup link active. Stop server.

- [ ] **Step 6: Commit**

```bash
cd "FLI Holdings"
git add dashboard/src/
git commit -m "feat(dashboard): app shell with sidebar nav and routing"
```

---

## Task 7: Setup page

**Files:**
- Modify: `dashboard/src/pages/Setup.tsx`
- Create: `dashboard/src/components/ProgressBar.tsx`

- [ ] **Step 1: Create `dashboard/src/components/ProgressBar.tsx`**

```tsx
import { Progress } from '@/components/ui/progress';

const STEPS = ['Loading', 'Quant', 'Qual', 'Synth', 'Done'];

interface Props {
  status: 'idle' | 'pending' | 'running' | 'done' | 'error';
  errorMessage?: string | null;
}

export default function ProgressBar({ status, errorMessage }: Props) {
  const idx =
    status === 'idle' ? -1
    : status === 'pending' ? 0
    : status === 'running' ? 2
    : status === 'done' ? 4
    : 4;
  const pct = status === 'idle' ? 0 : ((idx + 1) / STEPS.length) * 100;

  if (status === 'idle') return null;

  return (
    <div className="space-y-2">
      <Progress value={pct} className="h-2" />
      <div className="flex justify-between text-xs text-muted-foreground">
        {STEPS.map((s, i) => (
          <span key={s} className={i <= idx ? 'text-primary font-medium' : ''}>{s}</span>
        ))}
      </div>
      {status === 'error' && (
        <p className="text-sm text-destructive">{errorMessage}</p>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Implement `dashboard/src/pages/Setup.tsx`**

```tsx
import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAnalysisStore } from '@/store/analysis';
import { initScenarioCards } from '@/lib/scenarios';
import { compact } from '@/lib/format';
import ProgressBar from '@/components/ProgressBar';
import { Upload, FileSpreadsheet, FileText } from 'lucide-react';

export default function Setup() {
  const navigate = useNavigate();
  const xlsxRef = useRef<HTMLInputElement>(null);
  const docsRef = useRef<HTMLInputElement>(null);

  const [period, setPeriod] = useState('ENERO 2026');
  const [year, setYear] = useState(2026);
  const [company, setCompany] = useState('Grupo Nama');

  const { status, errorMessage, breakEvenTarget, setJob, setStatus, setResult, setError,
          setBreakEvenTarget, setScenarios } = useAnalysisStore();

  const POLL_MS = 2000;

  const poll = (jobId: string) => {
    const timer = setInterval(async () => {
      try {
        const res = await fetch(`/api/jobs/${jobId}`);
        const job = await res.json();
        if (job.status === 'done') {
          clearInterval(timer);
          setResult(job.result);
          setScenarios(initScenarioCards(job.result.synth.scenarios));
          navigate('/overview');
        } else if (job.status === 'error') {
          clearInterval(timer);
          setError(job.error ?? 'Unknown error');
        } else {
          setStatus(job.status);
        }
      } catch {
        clearInterval(timer);
        setError('Network error while polling job status.');
      }
    }, POLL_MS);
  };

  const handleRun = async () => {
    const xlsxFile = xlsxRef.current?.files?.[0];
    if (!xlsxFile) return;

    const form = new FormData();
    form.append('xlsx', xlsxFile);
    form.append('period', period);
    form.append('year', String(year));
    form.append('company', company);
    form.append('break_even_target_ebitda', String(breakEvenTarget));

    const qualFiles = docsRef.current?.files;
    if (qualFiles) {
      Array.from(qualFiles).forEach((f) => form.append('qual_docs', f));
    }

    try {
      const res = await fetch('/api/run', { method: 'POST', body: form });
      const { job_id } = await res.json();
      setJob(job_id);
      poll(job_id);
    } catch {
      setError('Failed to start analysis. Is the API server running?');
    }
  };

  return (
    <div className="p-8 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Run Analysis</h1>
        <p className="text-muted-foreground text-sm mt-1">Upload financial data and configure parameters.</p>
      </div>

      <Card>
        <CardHeader><CardTitle>Data Files</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Excel File <span className="text-destructive">*</span></Label>
            <div
              className="border-2 border-dashed rounded-lg p-6 text-center cursor-pointer hover:bg-muted/50 transition-colors"
              onClick={() => xlsxRef.current?.click()}
            >
              <FileSpreadsheet className="mx-auto mb-2 text-muted-foreground" size={32} />
              <p className="text-sm text-muted-foreground">
                {xlsxRef.current?.files?.[0]?.name ?? 'Click to select .xlsx file'}
              </p>
              <input ref={xlsxRef} type="file" accept=".xlsx" className="hidden" onChange={() => {}} />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Qual Documents <span className="text-muted-foreground text-xs">(optional — PDF, images)</span></Label>
            <div
              className="border-2 border-dashed rounded-lg p-4 text-center cursor-pointer hover:bg-muted/50 transition-colors"
              onClick={() => docsRef.current?.click()}
            >
              <FileText className="mx-auto mb-2 text-muted-foreground" size={24} />
              <p className="text-sm text-muted-foreground">Click to select files</p>
              <input ref={docsRef} type="file" accept=".pdf,.png,.jpg,.jpeg" multiple className="hidden" onChange={() => {}} />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Parameters</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Period</Label>
              <Input value={period} onChange={(e) => setPeriod(e.target.value)} placeholder="ENERO 2026" />
            </div>
            <div className="space-y-2">
              <Label>Year</Label>
              <Input type="number" value={year} onChange={(e) => setYear(Number(e.target.value))} />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Company</Label>
            <Input value={company} onChange={(e) => setCompany(e.target.value)} />
          </div>

          <div className="space-y-3">
            <div className="flex justify-between">
              <Label>Break-Even Target EBITDA</Label>
              <span className="text-sm font-medium">{compact(breakEvenTarget)}</span>
            </div>
            <Slider
              min={0}
              max={5_000_000}
              step={100_000}
              value={[breakEvenTarget]}
              onValueChange={([v]) => setBreakEvenTarget(v)}
            />
          </div>
        </CardContent>
      </Card>

      <ProgressBar status={status} errorMessage={errorMessage} />

      <Button
        size="lg"
        className="w-full"
        onClick={handleRun}
        disabled={status === 'pending' || status === 'running'}
      >
        <Upload size={16} className="mr-2" />
        {status === 'running' ? 'Running Analysis…' : 'Run Analysis'}
      </Button>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
cd "FLI Holdings"
git add dashboard/src/pages/Setup.tsx dashboard/src/components/ProgressBar.tsx
git commit -m "feat(dashboard): Setup page with file upload and polling"
```

---

## Task 8: Overview page

**Files:**
- Create: `dashboard/src/components/MetricCard.tsx`
- Modify: `dashboard/src/pages/Overview.tsx`

- [ ] **Step 1: Create `dashboard/src/components/MetricCard.tsx`**

```tsx
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface Props {
  title: string;
  value: string;
  sub?: string;
  trend?: 'up' | 'down' | 'neutral';
}

export default function MetricCard({ title, value, sub, trend }: Props) {
  return (
    <Card>
      <CardContent className="pt-6">
        <p className="text-xs text-muted-foreground uppercase tracking-wide">{title}</p>
        <p className="text-3xl font-bold mt-1">{value}</p>
        {(sub || trend) && (
          <div className="flex items-center gap-1 mt-1">
            {trend === 'up' && <TrendingUp size={14} className="text-emerald-500" />}
            {trend === 'down' && <TrendingDown size={14} className="text-rose-500" />}
            {sub && <p className="text-sm text-muted-foreground">{sub}</p>}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Implement `dashboard/src/pages/Overview.tsx`**

```tsx
import { useMemo } from 'react';
import { useAnalysisStore } from '@/store/analysis';
import MetricCard from '@/components/MetricCard';
import { compact, pct, mxn } from '@/lib/format';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

const COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe', '#ede9fe'];

export default function Overview() {
  const result = useAnalysisStore((s) => s.result);
  if (!result) return <div className="p-8 text-muted-foreground">No analysis loaded. Run setup first.</div>;

  const { consolidado, por_sucursal, por_categoria, pct_mix_categoria } = result.quant.kpis;

  const pieData = useMemo(
    () =>
      Object.entries(pct_mix_categoria).map(([name, value]) => ({
        name,
        value: Math.round(value * 100),
      })),
    [pct_mix_categoria],
  );

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold">{result.period}</h1>
        <p className="text-muted-foreground text-sm mt-1">Consolidated performance</p>
      </div>

      {/* Hero metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard title="Ingresos" value={compact(consolidado.ingresos_total)} />
        <MetricCard
          title="EBITDA"
          value={compact(consolidado.ebitda_total)}
          sub={pct(consolidado.margen_ebitda_global) + ' margin'}
          trend={consolidado.ebitda_total > 0 ? 'up' : 'down'}
        />
        <MetricCard
          title="Margen Bruto"
          value={pct(consolidado.margen_bruto_global)}
          trend="neutral"
        />
        <MetricCard
          title="Nómina / Ingresos"
          value={pct(consolidado.pct_nomina_ingresos_global)}
          trend={consolidado.pct_nomina_ingresos_global > 0.25 ? 'down' : 'up'}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Branch table */}
        <Card>
          <CardHeader><CardTitle>Por Sucursal</CardTitle></CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-muted-foreground">
                    <th className="text-left py-2">Sucursal</th>
                    <th className="text-right py-2">Ingresos</th>
                    <th className="text-right py-2">EBITDA</th>
                    <th className="text-right py-2">M. Bruto</th>
                  </tr>
                </thead>
                <tbody>
                  {por_sucursal.map((b) => (
                    <tr key={b.sucursal} className="border-b last:border-0 hover:bg-muted/30">
                      <td className="py-2 font-medium">{b.sucursal}</td>
                      <td className="py-2 text-right">{compact(b.ingresos)}</td>
                      <td className={`py-2 text-right font-semibold ${b.ebitda < 0 ? 'text-rose-500' : 'text-emerald-600'}`}>
                        {compact(b.ebitda)}
                      </td>
                      <td className="py-2 text-right">{pct(b.margen_bruto)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Category mix donut */}
        <Card>
          <CardHeader><CardTitle>Category Mix</CardTitle></CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} dataKey="value">
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => `${v}%`} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Quant narrative */}
      <Card>
        <CardHeader><CardTitle>Executive Summary</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed">{result.quant.narrative}</p>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
cd "FLI Holdings"
git add dashboard/src/pages/Overview.tsx dashboard/src/components/MetricCard.tsx
git commit -m "feat(dashboard): Overview page with KPI cards, branch table, donut chart"
```

---

## Task 9: WhatIfLab — ScenarioCard + WaterfallChart

**Files:**
- Create: `dashboard/src/components/ScenarioCard.tsx`
- Create: `dashboard/src/components/WaterfallChart.tsx`

- [ ] **Step 1: Create `dashboard/src/components/ScenarioCard.tsx`**

```tsx
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { compact } from '@/lib/format';
import { computeImpact } from '@/lib/scenarios';
import { useAnalysisStore } from '@/store/analysis';
import type { ScenarioCard as ScenarioCardType } from '@/types/analysis';
import type { PeriodKPIs } from '@/types/analysis';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Props {
  card: ScenarioCardType;
  kpis: PeriodKPIs;
  removable?: boolean;
}

export default function ScenarioCard({ card, kpis, removable = false }: Props) {
  const { updateScenario, removeScenario } = useAnalysisStore();

  const recompute = (patch: Partial<ScenarioCardType['params']>) => {
    const newParams = { ...card.params, ...patch };
    const newCard = { ...card, params: newParams };
    const impact = computeImpact(kpis, newCard);
    updateScenario(card.id, { params: newParams, impact });
  };

  const branches = kpis.por_sucursal.map((b) => b.sucursal);
  const categories = kpis.por_categoria.map((c) => c.categoria);

  const showBranch = card.type === 'cierre_sucursal' || card.type === 'reduccion_nomina';
  const showCategory = card.type === 'costo_insumo';
  const showShiftMix = card.type === 'shift_mix';
  const showDelta = card.type !== 'cierre_sucursal';

  return (
    <Card className={`transition-opacity ${card.active ? '' : 'opacity-50'}`}>
      <CardHeader className="pb-2 flex flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <Switch
            checked={card.active}
            onCheckedChange={(v) => updateScenario(card.id, { active: v })}
          />
          <span className="text-sm font-medium leading-tight">{card.label}</span>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={card.impact >= 0 ? 'default' : 'destructive'}>
            {card.impact >= 0 ? '+' : ''}{compact(card.impact)}
          </Badge>
          {removable && (
            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => removeScenario(card.id)}>
              <X size={12} />
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {showBranch && (
          <div className="space-y-1">
            <Label className="text-xs">Sucursal</Label>
            <Select value={card.params.sucursal} onValueChange={(v) => recompute({ sucursal: v })}>
              <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
              <SelectContent>
                {branches.map((b) => <SelectItem key={b} value={b}>{b}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        )}

        {showCategory && (
          <div className="space-y-1">
            <Label className="text-xs">Categoría</Label>
            <Select value={card.params.categoria} onValueChange={(v) => recompute({ categoria: v })}>
              <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
              <SelectContent>
                {categories.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        )}

        {showShiftMix && (
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <Label className="text-xs">From</Label>
              <Select value={card.params.cat_from} onValueChange={(v) => recompute({ cat_from: v })}>
                <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {categories.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">To</Label>
              <Select value={card.params.cat_to} onValueChange={(v) => recompute({ cat_to: v })}>
                <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {categories.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
        )}

        {showDelta && (
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Delta</span>
              <span>{(card.params.delta_pct * 100).toFixed(0)}%</span>
            </div>
            <Slider
              min={1}
              max={50}
              step={1}
              value={[card.params.delta_pct * 100]}
              onValueChange={([v]) => recompute({ delta_pct: v / 100 })}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Create `dashboard/src/components/WaterfallChart.tsx`**

```tsx
import { useMemo } from 'react';
import {
  ComposedChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts';
import { compact } from '@/lib/format';
import type { ScenarioCard } from '@/types/analysis';

interface Props {
  baseEbitda: number;
  scenarios: ScenarioCard[];
}

interface WaterfallEntry {
  name: string;
  base: number;    // invisible spacer bar
  delta: number;   // visible colored bar height (always positive)
  total: number;   // running total after this bar
  isNeg?: boolean; // true when the impact was negative
}

export default function WaterfallChart({ baseEbitda, scenarios }: Props) {
  const data: WaterfallEntry[] = useMemo(() => {
    const entries: WaterfallEntry[] = [
      { name: 'Base', base: 0, delta: baseEbitda, total: baseEbitda },
    ];
    let running = baseEbitda;
    scenarios.filter((s) => s.active).forEach((s) => {
      const start = running;
      const delta = s.impact;
      running += delta;
      entries.push({
        name: s.label.length > 20 ? s.label.slice(0, 18) + '…' : s.label,
        base: delta < 0 ? running : start,
        delta: Math.abs(delta),
        total: running,
        isNeg: delta < 0,
      });
    });
    entries.push({ name: 'Combined', base: 0, delta: running, total: running });
    return entries;
  }, [baseEbitda, scenarios]);

  const activeScenarios = scenarios.filter((s) => s.active);

  return (
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart data={data} margin={{ top: 20, right: 20, left: 20, bottom: 60 }}>
        <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-35} textAnchor="end" interval={0} />
        <YAxis tickFormatter={(v) => compact(v)} tick={{ fontSize: 11 }} />
        <Tooltip
          formatter={(value: number, name: string) =>
            name === 'delta' ? [compact(value), 'Impact'] : null
          }
          labelFormatter={(label) => label}
        />
        <ReferenceLine y={0} stroke="hsl(var(--border))" />
        {/* Invisible spacer */}
        <Bar dataKey="base" stackId="stack" fill="transparent" />
        {/* Visible delta */}
        <Bar dataKey="delta" stackId="stack" radius={[4, 4, 0, 0]}>
          {data.map((entry, i) => {
            const isBase = i === 0;
            const isCombined = i === data.length - 1;
            const isNeg = !!entry.isNeg;
            const color =
              isBase || isCombined
                ? 'hsl(var(--primary))'
                : isNeg
                ? '#f43f5e'
                : '#10b981';
            return <Cell key={i} fill={color} />;
          })}
        </Bar>
      </ComposedChart>
    </ResponsiveContainer>
  );
}
```

- [ ] **Step 3: Commit**

```bash
cd "FLI Holdings"
git add dashboard/src/components/ScenarioCard.tsx dashboard/src/components/WaterfallChart.tsx
git commit -m "feat(dashboard): ScenarioCard + WaterfallChart components"
```

---

## Task 10: WhatIfLab — full page + custom scenario drawer + break-even

**Files:**
- Create: `dashboard/src/components/BreakEvenCard.tsx`
- Modify: `dashboard/src/pages/WhatIfLab.tsx`

- [ ] **Step 1: Create `dashboard/src/components/BreakEvenCard.tsx`**

```tsx
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { compact, pct } from '@/lib/format';

interface Props {
  sucursal: string;
  currentTicket: number;
  requiredTicket: number;
  deltaPercent: number;
  currentEbitda: number;
  targetEbitda: number;
}

export default function BreakEvenCard({
  sucursal, currentTicket, requiredTicket, deltaPercent, currentEbitda, targetEbitda,
}: Props) {
  const needsIncrease = requiredTicket > currentTicket;
  return (
    <Card>
      <CardContent className="pt-4 space-y-2">
        <div className="flex items-center justify-between">
          <p className="font-semibold text-sm">{sucursal}</p>
          <Badge variant={needsIncrease ? 'destructive' : 'default'}>
            {needsIncrease ? '+' : ''}{pct(deltaPercent)} ticket
          </Badge>
        </div>
        <div className="text-xs text-muted-foreground space-y-1">
          <div className="flex justify-between">
            <span>Current ticket</span><span className="font-medium text-foreground">{compact(currentTicket)}</span>
          </div>
          <div className="flex justify-between">
            <span>Required ticket</span>
            <span className={`font-medium ${needsIncrease ? 'text-rose-500' : 'text-emerald-600'}`}>
              {compact(requiredTicket)}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Current EBITDA</span><span className="font-medium text-foreground">{compact(currentEbitda)}</span>
          </div>
          <div className="flex justify-between">
            <span>Target EBITDA</span><span className="font-medium text-foreground">{compact(targetEbitda)}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Implement `dashboard/src/pages/WhatIfLab.tsx`**

```tsx
import { useState, useMemo } from 'react';
import { useAnalysisStore } from '@/store/analysis';
import ScenarioCard from '@/components/ScenarioCard';
import WaterfallChart from '@/components/WaterfallChart';
import BreakEvenCard from '@/components/BreakEvenCard';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { compact } from '@/lib/format';
import { computeImpact, breakEvenTicket, initScenarioCards } from '@/lib/scenarios';
import type { ScenarioCard as ScenarioCardType, ScenarioType } from '@/types/analysis';
import { Plus } from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';

const SCENARIO_TYPES: { value: ScenarioType; label: string }[] = [
  { value: 'costo_insumo', label: 'Costo insumo (+%)' },
  { value: 'cierre_sucursal', label: 'Cierre sucursal' },
  { value: 'shift_mix', label: 'Mix shift (cat → cat)' },
  { value: 'reduccion_nomina', label: 'Reducción nómina' },
  { value: 'incremento_salarial', label: 'Incremento salarial' },
];

export default function WhatIfLab() {
  const { result, scenarios, addScenario, breakEvenTarget, setBreakEvenTarget } = useAnalysisStore();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [newType, setNewType] = useState<ScenarioType>('costo_insumo');
  const [newParams, setNewParams] = useState<ScenarioCardType['params']>({ delta_pct: 0.1 });

  if (!result) return <div className="p-8 text-muted-foreground">No analysis loaded. Run setup first.</div>;

  const kpis = result.quant.kpis;
  const baseEbitda = kpis.consolidado.ebitda_total;
  const branches = kpis.por_sucursal.map((b) => b.sucursal);
  const categories = kpis.por_categoria.map((c) => c.categoria);

  const combinedEbitda = useMemo(
    () => baseEbitda + scenarios.filter((s) => s.active).reduce((sum, s) => sum + s.impact, 0),
    [baseEbitda, scenarios],
  );

  const breakEvenResults = useMemo(
    () => branches.map((s) => breakEvenTicket(kpis, s, breakEvenTarget)),
    [kpis, branches, breakEvenTarget],
  );

  const handleAddScenario = () => {
    const draft: ScenarioCardType = {
      id: uuidv4(),
      type: newType,
      label: SCENARIO_TYPES.find((t) => t.value === newType)!.label,
      params: {
        delta_pct: newParams.delta_pct,
        sucursal: newParams.sucursal ?? branches[0],
        categoria: newParams.categoria ?? categories[0],
        cat_from: newParams.cat_from ?? categories[0],
        cat_to: newParams.cat_to ?? categories[1] ?? categories[0],
      },
      active: true,
      impact: 0,
    };
    draft.impact = computeImpact(kpis, draft);
    addScenario(draft);
    setDrawerOpen(false);
  };

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">What-If Lab</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Combined EBITDA:{' '}
            <span className={`font-semibold ${combinedEbitda < baseEbitda ? 'text-rose-500' : 'text-emerald-600'}`}>
              {compact(combinedEbitda)}
            </span>
            <span className="text-muted-foreground ml-2">(base: {compact(baseEbitda)})</span>
          </p>
        </div>
        <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
          <SheetTrigger asChild>
            <Button variant="outline" size="sm">
              <Plus size={14} className="mr-1" /> Add Scenario
            </Button>
          </SheetTrigger>
          <SheetContent>
            <SheetHeader>
              <SheetTitle>New Custom Scenario</SheetTitle>
            </SheetHeader>
            <div className="space-y-4 mt-6">
              <div className="space-y-2">
                <Label>Type</Label>
                <Select value={newType} onValueChange={(v) => setNewType(v as ScenarioType)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {SCENARIO_TYPES.map((t) => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {(newType === 'cierre_sucursal' || newType === 'reduccion_nomina') && (
                <div className="space-y-2">
                  <Label>Sucursal</Label>
                  <Select
                    value={newParams.sucursal ?? branches[0]}
                    onValueChange={(v) => setNewParams((p) => ({ ...p, sucursal: v }))}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {branches.map((b) => <SelectItem key={b} value={b}>{b}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {newType === 'costo_insumo' && (
                <div className="space-y-2">
                  <Label>Categoría</Label>
                  <Select
                    value={newParams.categoria ?? categories[0]}
                    onValueChange={(v) => setNewParams((p) => ({ ...p, categoria: v }))}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {categories.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {newType === 'shift_mix' && (
                <>
                  <div className="space-y-2">
                    <Label>From</Label>
                    <Select
                      value={newParams.cat_from ?? categories[0]}
                      onValueChange={(v) => setNewParams((p) => ({ ...p, cat_from: v }))}
                    >
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {categories.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>To</Label>
                    <Select
                      value={newParams.cat_to ?? categories[1] ?? categories[0]}
                      onValueChange={(v) => setNewParams((p) => ({ ...p, cat_to: v }))}
                    >
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {categories.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                </>
              )}

              {newType !== 'cierre_sucursal' && (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <Label>Delta</Label>
                    <span>{((newParams.delta_pct ?? 0.1) * 100).toFixed(0)}%</span>
                  </div>
                  <Slider
                    min={1} max={50} step={1}
                    value={[(newParams.delta_pct ?? 0.1) * 100]}
                    onValueChange={([v]) => setNewParams((p) => ({ ...p, delta_pct: v / 100 }))}
                  />
                </div>
              )}

              <Button className="w-full mt-4" onClick={handleAddScenario}>Add Scenario</Button>
            </div>
          </SheetContent>
        </Sheet>
      </div>

      {/* Scenarios + Waterfall */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
          {scenarios.map((card, i) => (
            <ScenarioCard
              key={card.id}
              card={card}
              kpis={kpis}
              removable={i >= 5}
            />
          ))}
        </div>
        <div className="sticky top-0">
          <WaterfallChart baseEbitda={baseEbitda} scenarios={scenarios} />
        </div>
      </div>

      {/* Break-Even section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Break-Even Ticket</h2>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground">Target EBITDA: {compact(breakEvenTarget)}</span>
            <div className="w-48">
              <Slider
                min={0}
                max={5_000_000}
                step={100_000}
                value={[breakEvenTarget]}
                onValueChange={([v]) => setBreakEvenTarget(v)}
              />
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {breakEvenResults.map((r) => (
            <BreakEvenCard
              key={r.sucursal}
              sucursal={r.sucursal}
              currentTicket={r.current_ticket}
              requiredTicket={r.required_ticket}
              deltaPercent={r.ticket_delta_pct}
              currentEbitda={r.current_ebitda}
              targetEbitda={r.target_ebitda}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
cd "FLI Holdings"
git add dashboard/src/pages/WhatIfLab.tsx dashboard/src/components/BreakEvenCard.tsx
git commit -m "feat(dashboard): What-If Lab with interactive scenarios, waterfall chart, break-even"
```

---

## Task 11: Memo page + Makefile

**Files:**
- Modify: `dashboard/src/pages/Memo.tsx`
- Create: `Makefile`

- [ ] **Step 1: Implement `dashboard/src/pages/Memo.tsx`**

```tsx
import { useAnalysisStore } from '@/store/analysis';
import { Button } from '@/components/ui/button';
import { Download } from 'lucide-react';

export default function Memo() {
  const result = useAnalysisStore((s) => s.result);
  if (!result) return <div className="p-8 text-muted-foreground">No analysis loaded. Run setup first.</div>;

  const html = result.synth.memo_html;
  const period = result.period;

  const handleDownload = () => {
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `memo_${period.replace(/\s+/g, '_')}.html`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-6 py-3 border-b">
        <h1 className="text-lg font-semibold">Memo — {period}</h1>
        <Button variant="outline" size="sm" onClick={handleDownload}>
          <Download size={14} className="mr-1" /> Download HTML
        </Button>
      </div>
      <iframe
        srcDoc={html}
        className="flex-1 w-full border-0"
        title="Analysis Memo"
        sandbox="allow-same-origin"
      />
    </div>
  );
}
```

- [ ] **Step 2: Create `Makefile` at repo root**

```makefile
.PHONY: dev api dashboard install

install:
	cd rga-copilot && .venv/bin/pip install fastapi "uvicorn[standard]" python-multipart httpx pytest-asyncio
	cd dashboard && npm install

api:
	cd api && ../rga-copilot/.venv/bin/uvicorn main:app --reload --port 8000

dashboard:
	cd dashboard && npm run dev

dev:
	@trap 'kill 0' SIGTERM SIGINT; \
	$(MAKE) api & \
	$(MAKE) dashboard & \
	wait
```

- [ ] **Step 3: Verify full stack starts**

```bash
cd "FLI Holdings" && make dev
```

Expected: API running on `:8000`, Vite running on `:5173`. Open `http://localhost:5173`.

- [ ] **Step 4: Commit**

```bash
cd "FLI Holdings"
git add dashboard/src/pages/Memo.tsx Makefile
git commit -m "feat(dashboard): Memo page + Makefile dev target"
```

---

## Task 12: End-to-end smoke test

- [ ] **Step 1: Run API unit tests**

```bash
cd "FLI Holdings" && rga-copilot/.venv/bin/pytest api/tests/ -v
```

Expected: 7 passed.

- [ ] **Step 2: Run frontend unit tests**

```bash
cd "FLI Holdings/dashboard" && npm test
```

Expected: all scenario math tests pass.

- [ ] **Step 3: Start the stack**

```bash
cd "FLI Holdings" && make dev
```

- [ ] **Step 4: Manual smoke test checklist**

1. Open `http://localhost:5173`. Confirm sidebar shows Setup active; other pages dimmed.
2. On Setup: confirm dropzone renders, period/year inputs work, break-even slider shows compact value.
3. Check the API directly: `curl -s http://localhost:8000/api/jobs/fake | python3 -m json.tool` → `{"detail":"Job not found"}`.
4. After a real run (requires valid xlsx + API key): confirm auto-navigation to Overview, KPI cards populated, donut chart renders.
5. Navigate to What-If Lab: confirm 5 default scenario cards load, sliders update impact badges instantly, waterfall chart repaints on toggle.
6. Add a custom scenario via drawer. Confirm new card appears and waterfall updates.
7. Navigate to Memo: confirm iframe renders HTML, Download button saves file.

- [ ] **Step 5: Final commit**

```bash
cd "FLI Holdings"
git add -A
git commit -m "feat(dashboard): complete RGA Copilot dashboard — API + React + What-If Lab"
```
