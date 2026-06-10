# RGA Copilot Dashboard — Design Spec
**Date:** 2026-06-10
**Status:** Approved

---

## Overview

Interactive web dashboard for the RGA Copilot pipeline. Users upload financial data, trigger the full analysis, and explore KPIs. The standout feature is the **What-If Lab**: fully customizable, slider-driven scenario analysis with instant EBITDA recalculation — no round-trips to the server.

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Frontend | React 18 + Vite |
| UI components | shadcn/ui + Tailwind CSS |
| Charts | Recharts |
| State | Zustand |
| Backend | FastAPI |
| Python bridge | Existing `orchestrator.py` (unchanged) |

---

## Repo Structure

```
FLI Holdings/
├── rga-copilot/          # unchanged Python pipeline
├── api/                  # NEW — FastAPI wrapper
│   ├── main.py           # app factory, CORS, mounts routes
│   ├── routes/
│   │   ├── run.py        # POST /api/run
│   │   └── jobs.py       # GET  /api/jobs/{id}
│   └── job_store.py      # in-memory job registry
└── dashboard/            # NEW — React + Vite + shadcn
    ├── src/
    │   ├── pages/
    │   │   ├── Setup.tsx
    │   │   ├── Overview.tsx
    │   │   ├── WhatIfLab.tsx
    │   │   └── Memo.tsx
    │   ├── lib/
    │   │   └── scenarios.ts   # client-side scenario math
    │   ├── store/
    │   │   └── analysis.ts    # Zustand store
    │   └── components/        # shared UI pieces
    ├── package.json
    └── vite.config.ts         # proxy /api → :8000
```

---

## API Surface

### `POST /api/run`
Accepts `multipart/form-data`:
- `xlsx` — Excel file (required)
- `qual_docs[]` — PDF/image files (optional, multiple)
- `period` — string, e.g. `"ENERO 2026"`
- `year` — int
- `company` — string, default `"Grupo Nama"`
- `break_even_target_ebitda` — float, default `1500000`

Returns: `{ "job_id": "<uuid>" }`

Spawns `orchestrator.run_analysis(...)` in a background thread. Stores result in `job_store`.

### `GET /api/jobs/{job_id}`
Returns:
```json
{
  "status": "pending|running|done|error",
  "result": { ...AnalysisResult... } | null,
  "error": "message" | null
}
```

`result` is the full serialized `AnalysisResult` including `quant.kpis`, `qual.signals`, `synth.memo_html`.

No scenario endpoints — all what-if math is client-side.

---

## Dashboard Pages

### Page 1 — Setup & Run
- Dropzone for Excel file
- Optional multi-file dropzone for qual docs
- Text input: Period (`ENERO 2026`)
- Number input: Year
- Slider: Break-even target EBITDA (default 1.5M)
- "Run Analysis" button
- Progress bar with step labels: `Loading → Quant → Qual → Synth → Done`
- Auto-navigates to Overview on completion

### Page 2 — Overview
- 4 hero metric cards: **Ingresos / EBITDA / Margen Bruto % / % Nómina**
- Red/green delta indicator on each card
- Per-branch sortable table (columns: sucursal, ingresos, EBITDA, margen bruto, ticket promedio, transacciones)
- Category mix donut chart
- Top 20 products table

### Page 3 — What-If Lab ⭐

**This is the primary differentiator.**

Layout: two-column split.

**Left — Scenarios Panel:**
- Base EBITDA badge always visible at top
- 5 default scenario cards loaded automatically from `quant.kpis`
- Each card:
  - Type label + affected target
  - Slider(s) for numeric parameters (delta %, target EBITDA)
  - Dropdown for categorical parameters (sucursal, categoria) — options drawn from real KPI data
  - Live impact badge: `+$X` green / `-$X` red
  - Toggle switch to include/exclude from combined total
- **"+ Add Custom Scenario"** button opens a drawer:
  - Step 1: choose scenario type (5 types)
  - Step 2: dropdowns auto-populated from `quant.kpis` data
  - Step 3: set numeric parameters via slider
  - Adds new card to panel
- No limit on number of custom scenarios

**Right — Live EBITDA Waterfall:**
- Recharts `ComposedChart` waterfall
- Bars: Base → Sc1 → Sc2 → … → Combined
- Updates on every slider change (no debounce needed — pure JS math)
- Toggle: **Stack view** (all scenarios combined) vs **Individual view** (each scenario isolated)
- Combined EBITDA = `base_ebitda + Σ(active scenario impacts)`

**Break-Even Section (below split):**
- Cards per branch showing:
  - Current ticket promedio
  - Required ticket to reach target EBITDA
  - Gap amount + percentage, color-coded
- Target EBITDA slider shared with Setup page (Zustand)

### Page 4 — Memo
- `<iframe>` rendering `synth.memo_html`
- "Download HTML" button

---

## Client-Side Scenario Math (`scenarios.ts`)

Exact JS mirror of `scenario_builder.py`:

```ts
costoInsumo(kpis, categoria: string, deltaPct: number): number
  // -deltaPct * kpis.por_categoria[categoria].costo

cierreSucursal(kpis, sucursal: string): number
  // -kpis.por_sucursal[sucursal].ebitda

shiftMix(kpis, catFrom: string, catTo: string, deltaPct: number): number
  // (catFrom.ingresos * deltaPct) * (catTo.margen_bruto - catFrom.margen_bruto)

reduccionNomina(kpis, sucursal: string, deltaPct: number): number
  // kpis.por_sucursal[sucursal].nomina * deltaPct

incrementoSalarial(kpis, deltaPct: number): number
  // -kpis.consolidado.nomina_total * deltaPct

breakEvenTicket(kpis, sucursal: string, targetEbitda: number): BreakEvenResult
  // required = (targetEbitda + gastos + nomina) / (transacciones * margen_bruto)
```

Each function is pure — no side effects. Scenario card re-renders call the function directly on slider change.

---

## State Management (Zustand)

Single `useAnalysisStore`:
- `jobId: string | null`
- `status: 'idle' | 'pending' | 'running' | 'done' | 'error'`
- `result: AnalysisResult | null`
- `scenarios: ScenarioCard[]` — active scenario cards with current params
- `breakEvenTarget: number` — shared across Lab + Setup

---

## Dev Setup

```bash
# Terminal 1 — API
cd api && uvicorn main:app --reload --port 8000

# Terminal 2 — Dashboard
cd dashboard && npm run dev  # proxies /api → :8000

# Or single command via Makefile
make dev
```

---

## Out of Scope
- Authentication / multi-user sessions
- Persistent job history (in-memory only — restart clears jobs)
- LLM narrative regeneration on custom scenarios
- Mobile layout
- PDF export of dashboard
