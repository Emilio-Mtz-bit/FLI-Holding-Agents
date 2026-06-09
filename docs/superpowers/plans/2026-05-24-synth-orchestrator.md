# SynthAgent + Orquestador — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `agents/synth/` (SynthAgent with deterministic scenarios + memo PDF) and `orchestrator.py` that wire the existing QuantAgent and QualAgent into a single `run_analysis()` call.

**Architecture:** SynthAgent receives `QuantOutput` + `QualOutput`, makes one Claude call to extract top-3 signals + next steps, runs three deterministic what-if scenarios, renders a Jinja2 HTML memo, then exports it to PDF with WeasyPrint. The orchestrator owns Alert-model normalization (quant → qual format) and calls pipeline → quant → qual → synth in sequence.

**Tech Stack:** Python 3.11+, Pydantic v2, Anthropic SDK (claude-sonnet-4-6), Jinja2, WeasyPrint, pandas (existing).

---

## Known Gaps in Upstream Agents

| Gap | Scope decision |
|-----|----------------|
| `QualAgent.hypotheses` always `[]` — RAG loop not implemented | Synth degrades gracefully: uses `qual.signals["riesgos"]` + `qual.summary` when hypotheses list is empty |
| `QuantOutput` has no `forecast` field — `forecaster.py` not built | Memo forecast section is conditional; Synth does not depend on it |
| Two `Alert` models coexist (quant vs qual) | Orchestrator owns adapter; neither agent is changed |

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `rga-copilot/agents/quant/kpi_calculator.py` | Add `CategoryKPI` dataclass + `calc_category_kpis()` + `por_categoria` field on `PeriodKPIs` |
| Modify | `rga-copilot/agents/quant/agent.py` | Serialize `por_categoria` in `_serialize_kpis()` |
| Create | `rga-copilot/agents/synth/__init__.py` | Package marker |
| Create | `rga-copilot/agents/synth/models.py` | `Signal`, `Scenario`, `Recommendation`, `SynthOutput`, `AnalysisResult` |
| Create | `rga-copilot/agents/synth/scenario_builder.py` | Three deterministic what-if scenarios, no LLM |
| Create | `rga-copilot/agents/synth/templates/memo.html.j2` | Jinja2 HTML memo template |
| Create | `rga-copilot/agents/synth/memo_generator.py` | Render template → HTML string + WeasyPrint → PDF |
| Create | `rga-copilot/agents/synth/prompts/signal_synthesis.txt` | Prompt for Claude: quant+qual → 3 signals + next steps |
| Create | `rga-copilot/agents/synth/agent.py` | `SynthAgent.run(quant, qual) → SynthOutput` |
| Create | `rga-copilot/orchestrator.py` | Alert adapter + `run_analysis(csv, xlsx, qual_docs, period)` |
| Create | `rga-copilot/tests/test_category_kpis.py` | Unit tests for `calc_category_kpis` |
| Create | `rga-copilot/tests/test_scenario_builder.py` | Unit tests for all 3 scenario functions |
| Create | `rga-copilot/tests/test_memo_generator.py` | Unit tests for HTML render + PDF path |
| Create | `rga-copilot/tests/test_synth_agent.py` | Unit tests for SynthAgent with mocked Claude |
| Create | `rga-copilot/tests/test_orchestrator.py` | Unit tests for alert adapter + orchestrator |
| Create | `rga-copilot/scripts/smoke_test_synth.py` | End-to-end smoke test with real data |

---

## Task 1: Add Dependencies

**Files:**
- Modify: `rga-copilot/requirements.txt`

- [ ] **Step 1: Check macOS system dependencies for WeasyPrint**

Run:
```bash
brew list cairo pango gdk-pixbuf libffi 2>/dev/null | wc -l
```

If output is `0` or missing packages, install:
```bash
brew install cairo pango gdk-pixbuf libffi
```

WeasyPrint on macOS requires these system libs. Without them, `import weasyprint` raises `OSError: cannot load library 'libgobject-2.0-0'`.

- [ ] **Step 2: Add Jinja2 and WeasyPrint to requirements.txt**

Edit `rga-copilot/requirements.txt` to add at end:
```
jinja2>=3.1.0
weasyprint>=61.0
pandas>=2.0.0
scikit-learn>=1.4.0
```

- [ ] **Step 3: Install in active virtualenv**

Run from `rga-copilot/`:
```bash
pip install jinja2 weasyprint pandas scikit-learn
```

Expected: no errors. Verify with:
```bash
python -c "import jinja2, weasyprint; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add rga-copilot/requirements.txt
git commit -m "chore: add jinja2, weasyprint, scikit-learn to requirements"
```

---

## Task 2: Extend kpi_calculator.py with CategoryKPI

`scenario_builder.py` needs full category costs (not just top-20 products). Fix requires adding `calc_category_kpis()` to `kpi_calculator.py` and threading it through `PeriodKPIs`.

**Files:**
- Modify: `rga-copilot/agents/quant/kpi_calculator.py`
- Modify: `rga-copilot/agents/quant/agent.py`
- Create: `rga-copilot/tests/test_category_kpis.py`

- [ ] **Step 1: Write failing test**

Create `rga-copilot/tests/test_category_kpis.py`:
```python
"""Unit tests for calc_category_kpis."""
import pandas as pd
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.quant.kpi_calculator import LocalDB, calc_category_kpis, build_period_kpis


def _make_db() -> LocalDB:
    bd = pd.DataFrame({
        "MES": ["ENERO 2026"] * 4,
        "SUCURSAL": ["ANT", "ANT", "MOR", "MOR"],
        "SUBCATEGORÍA 1": ["MAKIS", "MAKIS", "BEBIDAS", "BEBIDAS"],
        "SUBCATEGORÍA 2": ["MAKI A", "MAKI B", "SODA", "JUGO"],
        "SUBTOTAL": [1000.0, 500.0, 300.0, 200.0],
        "COSTO TOTAL SIN IVA": [300.0, 150.0, 120.0, 80.0],
        "UTILIDAD BRUTA": [700.0, 350.0, 180.0, 120.0],
        "MARGEN BRUTO": [0.70, 0.70, 0.60, 0.60],
        "CANTIDAD": [10, 5, 20, 15],
    })
    gastos = pd.DataFrame({"MES GASTO": [], "SUCURSAL": [], "SUBTOTAL": []})
    nomina = pd.DataFrame({"MES NÓMINA": [], "SUCURSAL": [], "SUBTOTAL": []})
    return LocalDB(bd=bd, gastos=gastos, nomina=nomina)


def test_calc_category_kpis_returns_correct_count():
    db = _make_db()
    cats = calc_category_kpis(db, "ENERO 2026")
    assert len(cats) == 2


def test_calc_category_kpis_makis_values():
    db = _make_db()
    cats = {c.categoria: c for c in calc_category_kpis(db, "ENERO 2026")}
    makis = cats["MAKIS"]
    assert makis.ingresos == pytest.approx(1500.0)
    assert makis.costo == pytest.approx(450.0)
    assert makis.margen_bruto == pytest.approx(0.70, abs=1e-6)
    assert makis.pct_total_ingresos == pytest.approx(1500.0 / 2000.0)


def test_build_period_kpis_has_por_categoria():
    db = _make_db()
    kpis = build_period_kpis(db, "ENERO 2026")
    assert hasattr(kpis, "por_categoria")
    assert len(kpis.por_categoria) == 2
```

- [ ] **Step 2: Run test — expect AttributeError**

Run from `rga-copilot/`:
```bash
python -m pytest tests/test_category_kpis.py -v 2>&1 | tail -15
```
Expected: `FAILED` — `cannot import name 'calc_category_kpis'` or `AttributeError: 'PeriodKPIs' object has no attribute 'por_categoria'`.

- [ ] **Step 3: Add CategoryKPI and calc_category_kpis to kpi_calculator.py**

In `rga-copilot/agents/quant/kpi_calculator.py`, after the `ProductKPI` dataclass (around line 56), add:
```python
@dataclass
class CategoryKPI:
    categoria: str
    ingresos: float
    costo: float
    margen_bruto: float          # (ingresos - costo) / ingresos
    pct_total_ingresos: float    # share of period total revenue
```

Add the `por_categoria` field to `PeriodKPIs` (line 58–64):
```python
@dataclass
class PeriodKPIs:
    period: str
    consolidado: dict
    por_sucursal: list[BranchKPI]
    top_productos: list[ProductKPI]
    pct_mix_categoria: dict[str, float]
    por_categoria: list[CategoryKPI]   # ← new
```

Add function after `calc_category_mix` (around line 178):
```python
def calc_category_kpis(db: LocalDB, period: str) -> list[CategoryKPI]:
    """Full category aggregation — all rows, not just top-N products."""
    bd = _filter_period(db.bd, period)
    agg = (
        bd.groupby("SUBCATEGORÍA 1")
        .agg(
            ingresos=("SUBTOTAL", "sum"),
            costo=("COSTO TOTAL SIN IVA", "sum"),
        )
        .reset_index()
    )
    total = agg["ingresos"].sum()
    result = []
    for _, r in agg.iterrows():
        ing = float(r["ingresos"])
        costo = float(r["costo"])
        result.append(CategoryKPI(
            categoria=str(r["SUBCATEGORÍA 1"]),
            ingresos=ing,
            costo=costo,
            margen_bruto=(ing - costo) / ing if ing else 0.0,
            pct_total_ingresos=ing / total if total else 0.0,
        ))
    return sorted(result, key=lambda x: x.ingresos, reverse=True)
```

Update `build_period_kpis` at the bottom:
```python
def build_period_kpis(db: LocalDB, period: str) -> PeriodKPIs:
    branch_kpis   = calc_branch_kpis(db, period)
    top_productos  = calc_top_products(db, period)
    mix            = calc_category_mix(db, period)
    consolidado    = calc_consolidado(branch_kpis)
    por_categoria  = calc_category_kpis(db, period)      # ← new
    return PeriodKPIs(
        period=period,
        consolidado=consolidado,
        por_sucursal=branch_kpis,
        top_productos=top_productos,
        pct_mix_categoria=mix,
        por_categoria=por_categoria,                      # ← new
    )
```

- [ ] **Step 4: Update _serialize_kpis in agents/quant/agent.py**

Replace `_serialize_kpis` (lines 116–123):
```python
def _serialize_kpis(kpis: PeriodKPIs) -> dict:
    return {
        "period": kpis.period,
        "consolidado": kpis.consolidado,
        "por_sucursal": [vars(b) for b in kpis.por_sucursal],
        "pct_mix_categoria": kpis.pct_mix_categoria,
        "por_categoria": [vars(c) for c in kpis.por_categoria],   # ← new
    }
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
python -m pytest tests/test_category_kpis.py -v 2>&1 | tail -10
```
Expected: `3 passed`.

- [ ] **Step 6: Verify existing quant test still passes**

```bash
python -m pytest tests/ -v -k "not smoke" 2>&1 | tail -10
```
Expected: all existing tests pass (no regressions).

- [ ] **Step 7: Commit**

```bash
git add rga-copilot/agents/quant/kpi_calculator.py \
        rga-copilot/agents/quant/agent.py \
        rga-copilot/tests/test_category_kpis.py
git commit -m "feat(quant): add CategoryKPI + calc_category_kpis, thread into PeriodKPIs"
```

---

## Task 3: Synth Models

**Files:**
- Create: `rga-copilot/agents/synth/__init__.py`
- Create: `rga-copilot/agents/synth/models.py`

- [ ] **Step 1: Write failing import test**

Add inline to a temp file — just verify models import cleanly after creation:
```bash
python -c "from agents.synth.models import Signal, Scenario, Recommendation, SynthOutput, AnalysisResult; print('OK')"
```
Expected now: `ModuleNotFoundError`. After implementation: `OK`.

- [ ] **Step 2: Create __init__.py**

Create `rga-copilot/agents/synth/__init__.py` (empty):
```python
```

- [ ] **Step 3: Create models.py**

Create `rga-copilot/agents/synth/models.py`:
```python
"""
Pydantic contracts for SynthAgent.

Signal       — one of the top-3 synthesized signals (quant + qual evidence).
Scenario     — deterministic what-if result (no LLM).
Recommendation — derived from Signal, for the 2x2 matrix.
SynthOutput  — full output of SynthAgent.run().
AnalysisResult — top-level orchestrator output.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from agents.quant.agent import QuantOutput
from agents.qual.models import QualOutput


ImpactLevel = Literal["alto", "medio", "bajo"]
EaseLevel   = Literal["alta", "media", "baja"]


class Signal(BaseModel):
    rank: int                      # 1 = highest impact
    titulo: str                    # e.g. "Sucursal MOR: EBITDA negativo persistente"
    evidencia_quant: str           # specific numbers from QuantOutput
    evidencia_qual: str            # from QualOutput.signals / hypotheses / summary
    recomendacion: str             # one concrete action
    impacto: ImpactLevel
    facilidad: EaseLevel


class Scenario(BaseModel):
    name: str                      # human label, e.g. "Costo insumo MAKIS +15%"
    variable: str                  # machine key: "costo_insumo" | "cierre_sucursal" | "shift_mix"
    delta_pct: float               # magnitude of the lever (0.15 = 15 %)
    affected_target: str           # category name or sucursal code
    base_ebitda: float             # consolidated EBITDA before scenario (MXN)
    impact_on_ebitda: float        # change (negative = loss)
    ebitda_post: float             # = base_ebitda + impact_on_ebitda


class Recommendation(BaseModel):
    accion: str
    impacto: ImpactLevel
    facilidad: EaseLevel
    fuente: str                    # e.g. "signal_1"


class SynthOutput(BaseModel):
    signals: list[Signal]
    scenarios: list[Scenario]
    recommendations: list[Recommendation]
    next_steps: str                # Claude-generated paragraph
    memo_html: str
    memo_pdf_path: str


class AnalysisResult(BaseModel):
    period: str
    quant: QuantOutput
    qual: QualOutput
    synth: SynthOutput
```

- [ ] **Step 4: Verify import works**

```bash
cd rga-copilot && python -c "from agents.synth.models import Signal, Scenario, Recommendation, SynthOutput, AnalysisResult; print('OK')"
```
Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add rga-copilot/agents/synth/
git commit -m "feat(synth): add Pydantic models — Signal, Scenario, SynthOutput, AnalysisResult"
```

---

## Task 4: scenario_builder.py

Pure Python, no LLM. Three scenarios using `QuantOutput.kpis["por_categoria"]` and `kpis["por_sucursal"]`.

**Files:**
- Create: `rga-copilot/agents/synth/scenario_builder.py`
- Create: `rga-copilot/tests/test_scenario_builder.py`

- [ ] **Step 1: Write failing tests**

Create `rga-copilot/tests/test_scenario_builder.py`:
```python
"""Unit tests for scenario_builder — no Claude calls, pure maths."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.synth.models import Scenario
from agents.synth.scenario_builder import (
    build_scenario_costo_insumo,
    build_scenario_cierre_sucursal,
    build_scenario_shift_mix,
    build_default_scenarios,
)

# ---------------------------------------------------------------------------
# Minimal QuantOutput fixture (dict, matching QuantOutput.kpis structure)
# ---------------------------------------------------------------------------

QUANT_KPIS = {
    "consolidado": {
        "ebitda_total": 2_000_000.0,
        "ingresos_total": 10_000_000.0,
    },
    "por_categoria": [
        {"categoria": "MAKIS",    "ingresos": 5_000_000.0, "costo": 1_500_000.0, "margen_bruto": 0.70, "pct_total_ingresos": 0.50},
        {"categoria": "BEBIDAS",  "ingresos": 3_000_000.0, "costo":   900_000.0, "margen_bruto": 0.70, "pct_total_ingresos": 0.30},
        {"categoria": "DESTILADOS","ingresos": 2_000_000.0,"costo":   800_000.0, "margen_bruto": 0.60, "pct_total_ingresos": 0.20},
    ],
    "por_sucursal": [
        {"sucursal": "ANT", "ebitda": 900_000.0,   "ingresos": 3_500_000.0},
        {"sucursal": "SOK", "ebitda": 700_000.0,   "ingresos": 2_500_000.0},
        {"sucursal": "MOR", "ebitda": -100_000.0,  "ingresos": 500_000.0},
        {"sucursal": "CAM", "ebitda": 300_000.0,   "ingresos": 2_000_000.0},
        {"sucursal": "JUR", "ebitda": 200_000.0,   "ingresos": 1_500_000.0},
    ],
}


class FakeQuantOutput:
    """Minimal stand-in for QuantOutput — only kpis dict needed."""
    def __init__(self):
        self.kpis = QUANT_KPIS
        self.period = "ENERO 2026"


Q = FakeQuantOutput()


def test_scenario_costo_insumo_impact():
    sc = build_scenario_costo_insumo(Q, categoria="MAKIS", delta_pct=0.15)
    # cost of MAKIS = 1_500_000; impact = -0.15 * 1_500_000 = -225_000
    assert sc.variable == "costo_insumo"
    assert sc.impact_on_ebitda == pytest.approx(-225_000.0)
    assert sc.ebitda_post == pytest.approx(2_000_000.0 - 225_000.0)
    assert sc.base_ebitda == pytest.approx(2_000_000.0)


def test_scenario_cierre_sucursal_negative_ebitda():
    # Closing MOR (ebitda = -100_000) → we gain 100_000
    sc = build_scenario_cierre_sucursal(Q, sucursal="MOR")
    assert sc.variable == "cierre_sucursal"
    assert sc.impact_on_ebitda == pytest.approx(100_000.0)   # gain
    assert sc.ebitda_post == pytest.approx(2_100_000.0)


def test_scenario_shift_mix_impact():
    # Shift 10% total revenue from DESTILADOS (margen 0.60) → MAKIS (margen 0.70)
    # delta_revenue = 10_000_000 * 0.10 = 1_000_000
    # impact = 1_000_000 * (0.70 - 0.60) = 100_000
    sc = build_scenario_shift_mix(Q, cat_from="DESTILADOS", cat_to="MAKIS", delta_pct=0.10)
    assert sc.variable == "shift_mix"
    assert sc.impact_on_ebitda == pytest.approx(100_000.0)
    assert sc.ebitda_post == pytest.approx(2_100_000.0)


def test_build_default_scenarios_returns_three():
    scenarios = build_default_scenarios(Q)
    assert len(scenarios) == 3
    variables = {s.variable for s in scenarios}
    assert variables == {"costo_insumo", "cierre_sucursal", "shift_mix"}
```

- [ ] **Step 2: Run test — expect ImportError**

```bash
cd rga-copilot && python -m pytest tests/test_scenario_builder.py -v 2>&1 | tail -8
```
Expected: `FAILED` — `cannot import name 'build_scenario_costo_insumo'`.

- [ ] **Step 3: Implement scenario_builder.py**

Create `rga-copilot/agents/synth/scenario_builder.py`:
```python
"""
Deterministic what-if scenario calculations. No LLM.

All functions receive a QuantOutput (or duck-typed object with .kpis dict)
and return a Scenario model.

Scenario 1 — costo_insumo:
    A cost increase of delta_pct on all COGS in a category.
    impact = -delta_pct * costo_categoria

Scenario 2 — cierre_sucursal:
    Permanently close a branch.
    impact = -branch.ebitda  (losing that branch's EBITDA contribution)
    Note: if branch EBITDA is negative, closure is positive impact.

Scenario 3 — shift_mix:
    Shift delta_pct of total revenue from cat_from → cat_to.
    impact = delta_pct * ingresos_total * (margin_to - margin_from)
"""

from __future__ import annotations

from agents.synth.models import Scenario


def build_scenario_costo_insumo(
    quant,
    categoria: str,
    delta_pct: float = 0.15,
) -> Scenario:
    """Raise cost of inputs for `categoria` by `delta_pct`."""
    kpis = quant.kpis
    base_ebitda = kpis["consolidado"]["ebitda_total"]

    cat_map = {c["categoria"]: c for c in kpis["por_categoria"]}
    if categoria not in cat_map:
        raise ValueError(f"Categoría '{categoria}' not found in por_categoria. "
                         f"Available: {list(cat_map)}")

    costo_categoria = cat_map[categoria]["costo"]
    impact = -delta_pct * costo_categoria

    return Scenario(
        name=f"Costo insumo {categoria} +{delta_pct:.0%}",
        variable="costo_insumo",
        delta_pct=delta_pct,
        affected_target=categoria,
        base_ebitda=base_ebitda,
        impact_on_ebitda=impact,
        ebitda_post=base_ebitda + impact,
    )


def build_scenario_cierre_sucursal(
    quant,
    sucursal: str,
) -> Scenario:
    """Close branch `sucursal` — remove its EBITDA contribution."""
    kpis = quant.kpis
    base_ebitda = kpis["consolidado"]["ebitda_total"]

    branch_map = {b["sucursal"]: b for b in kpis["por_sucursal"]}
    if sucursal not in branch_map:
        raise ValueError(f"Sucursal '{sucursal}' not found. Available: {list(branch_map)}")

    branch_ebitda = branch_map[sucursal]["ebitda"]
    # Closing the branch means we lose its EBITDA contribution.
    # impact = -branch_ebitda (positive when branch was losing money)
    impact = -branch_ebitda

    return Scenario(
        name=f"Cierre sucursal {sucursal}",
        variable="cierre_sucursal",
        delta_pct=1.0,
        affected_target=sucursal,
        base_ebitda=base_ebitda,
        impact_on_ebitda=impact,
        ebitda_post=base_ebitda + impact,
    )


def build_scenario_shift_mix(
    quant,
    cat_from: str,
    cat_to: str,
    delta_pct: float = 0.05,
) -> Scenario:
    """
    Shift delta_pct of total revenue from cat_from → cat_to.
    Revenue is constant; only the margin difference matters for EBITDA.
    """
    kpis = quant.kpis
    base_ebitda = kpis["consolidado"]["ebitda_total"]
    ingresos_total = kpis["consolidado"]["ingresos_total"]

    cat_map = {c["categoria"]: c for c in kpis["por_categoria"]}
    for cat in (cat_from, cat_to):
        if cat not in cat_map:
            raise ValueError(f"Categoría '{cat}' not found. Available: {list(cat_map)}")

    margin_from = cat_map[cat_from]["margen_bruto"]
    margin_to   = cat_map[cat_to]["margen_bruto"]
    delta_revenue = ingresos_total * delta_pct
    impact = delta_revenue * (margin_to - margin_from)

    return Scenario(
        name=f"Mix shift {delta_pct:.0%}: {cat_from} → {cat_to}",
        variable="shift_mix",
        delta_pct=delta_pct,
        affected_target=f"{cat_from}→{cat_to}",
        base_ebitda=base_ebitda,
        impact_on_ebitda=impact,
        ebitda_post=base_ebitda + impact,
    )


def build_default_scenarios(quant) -> list[Scenario]:
    """
    Build three predefined scenarios using real data to pick relevant targets:
    1. Raise cost of the highest-cost category by 15%.
    2. Close the branch with the lowest (possibly negative) EBITDA.
    3. Shift 5% of revenue from lowest-margin category → highest-margin category.
    """
    kpis = quant.kpis
    cats = kpis["por_categoria"]
    branches = kpis["por_sucursal"]

    # Scenario 1: highest-cost category
    highest_cost_cat = max(cats, key=lambda c: c["costo"])["categoria"]
    sc1 = build_scenario_costo_insumo(quant, categoria=highest_cost_cat, delta_pct=0.15)

    # Scenario 2: worst EBITDA branch
    worst_branch = min(branches, key=lambda b: b["ebitda"])["sucursal"]
    sc2 = build_scenario_cierre_sucursal(quant, sucursal=worst_branch)

    # Scenario 3: shift from lowest-margin → highest-margin category
    sorted_by_margin = sorted(cats, key=lambda c: c["margen_bruto"])
    cat_from = sorted_by_margin[0]["categoria"]
    cat_to   = sorted_by_margin[-1]["categoria"]
    if cat_from == cat_to:
        # All same margin — pick first and last alphabetically as fallback
        cat_from, cat_to = cats[0]["categoria"], cats[-1]["categoria"]
    sc3 = build_scenario_shift_mix(quant, cat_from=cat_from, cat_to=cat_to, delta_pct=0.05)

    return [sc1, sc2, sc3]
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd rga-copilot && python -m pytest tests/test_scenario_builder.py -v 2>&1 | tail -10
```
Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add rga-copilot/agents/synth/scenario_builder.py \
        rga-copilot/tests/test_scenario_builder.py
git commit -m "feat(synth): deterministic scenario builder — 3 what-if scenarios, no LLM"
```

---

## Task 5: Jinja2 Memo Template

**Files:**
- Create: `rga-copilot/agents/synth/templates/memo.html.j2`

- [ ] **Step 1: Create templates directory and template**

```bash
mkdir -p rga-copilot/agents/synth/templates
```

Create `rga-copilot/agents/synth/templates/memo.html.j2`:
```html
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Memo Ejecutivo — {{ period }}</title>
<style>
  body {
    font-family: 'Arial', sans-serif;
    font-size: 11pt;
    max-width: 860px;
    margin: auto;
    padding: 40px 48px;
    color: #1a1a1a;
    line-height: 1.5;
  }
  h1 { color: #1a3c5e; font-size: 20pt; margin-bottom: 4px; }
  .subtitle { color: #555; font-size: 10pt; margin-top: 0; margin-bottom: 24px; }
  h2 {
    color: #1a3c5e;
    font-size: 13pt;
    border-bottom: 2px solid #1a3c5e;
    padding-bottom: 4px;
    margin-top: 32px;
  }
  h3 { color: #2a5a8e; font-size: 11pt; margin-bottom: 4px; }
  .signal-card {
    border: 1px solid #2a5a8e;
    border-left: 4px solid #2a5a8e;
    border-radius: 4px;
    padding: 14px 18px;
    margin: 14px 0;
    background: #f8fbff;
  }
  .signal-card.rank-1 { border-left-color: #c0392b; }
  .signal-card.rank-2 { border-left-color: #d35400; }
  .signal-card.rank-3 { border-left-color: #2a5a8e; }
  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 9pt;
    font-weight: bold;
    margin-right: 6px;
  }
  .badge-alto   { background: #c0392b; color: white; }
  .badge-medio  { background: #d35400; color: white; }
  .badge-bajo   { background: #7f8c8d; color: white; }
  .badge-alta   { background: #27ae60; color: white; }
  .badge-media  { background: #f39c12; color: white; }
  .badge-baja   { background: #7f8c8d; color: white; }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0;
    font-size: 10pt;
  }
  th {
    background: #1a3c5e;
    color: white;
    padding: 8px 12px;
    text-align: left;
  }
  td {
    border: 1px solid #ddd;
    padding: 7px 12px;
    vertical-align: top;
  }
  tr:nth-child(even) td { background: #f5f5f5; }
  .impact-pos { color: #27ae60; font-weight: bold; }
  .impact-neg { color: #c0392b; font-weight: bold; }
  .footer {
    margin-top: 48px;
    border-top: 1px solid #ccc;
    padding-top: 10px;
    font-size: 8pt;
    color: #888;
  }
  blockquote {
    border-left: 3px solid #2a5a8e;
    margin: 0;
    padding: 8px 16px;
    background: #f0f4f8;
    font-style: italic;
  }
</style>
</head>
<body>

<h1>Memo Ejecutivo Financiero</h1>
<p class="subtitle">
  <strong>Empresa:</strong> {{ company }} &nbsp;|&nbsp;
  <strong>Período:</strong> {{ period }} &nbsp;|&nbsp;
  <strong>Generado:</strong> {{ generated_date }}
</p>

<!-- ====================================================== -->
<h2>1. Resumen del Período</h2>
<p>{{ quant_narrative }}</p>

{% if qual_summary %}
<blockquote>{{ qual_summary }}</blockquote>
{% endif %}

<!-- ====================================================== -->
<h2>2. Top 3 Señales Priorizadas</h2>

{% for s in signals %}
<div class="signal-card rank-{{ s.rank }}">
  <h3>{{ s.rank }}. {{ s.titulo }}</h3>
  <p><strong>Evidencia cuantitativa:</strong> {{ s.evidencia_quant }}</p>
  <p><strong>Contexto cualitativo:</strong> {{ s.evidencia_qual }}</p>
  <p><strong>Recomendación:</strong> {{ s.recomendacion }}</p>
  <div>
    Impacto: <span class="badge badge-{{ s.impacto }}">{{ s.impacto | upper }}</span>
    Facilidad: <span class="badge badge-{{ s.facilidad }}">{{ s.facilidad | upper }}</span>
  </div>
</div>
{% endfor %}

<!-- ====================================================== -->
<h2>3. Escenarios Simulados (What-If)</h2>
<table>
  <tr>
    <th>Escenario</th>
    <th>EBITDA Base (MXN)</th>
    <th>Impacto (MXN)</th>
    <th>EBITDA Post (MXN)</th>
    <th>Variación</th>
  </tr>
  {% for sc in scenarios %}
  {% set pct_change = (sc.impact_on_ebitda / sc.base_ebitda * 100) if sc.base_ebitda != 0 else 0 %}
  <tr>
    <td>{{ sc.name }}</td>
    <td>${{ "{:,.0f}".format(sc.base_ebitda) }}</td>
    <td class="{{ 'impact-pos' if sc.impact_on_ebitda >= 0 else 'impact-neg' }}">
      {{ '+' if sc.impact_on_ebitda >= 0 else '' }}${{ "{:,.0f}".format(sc.impact_on_ebitda) }}
    </td>
    <td>${{ "{:,.0f}".format(sc.ebitda_post) }}</td>
    <td class="{{ 'impact-pos' if pct_change >= 0 else 'impact-neg' }}">
      {{ '+' if pct_change >= 0 else '' }}{{ "{:.1f}".format(pct_change) }}%
    </td>
  </tr>
  {% endfor %}
</table>

<!-- ====================================================== -->
<h2>4. Recomendaciones Priorizadas</h2>
<table>
  <tr>
    <th>#</th>
    <th>Acción recomendada</th>
    <th>Impacto</th>
    <th>Facilidad</th>
  </tr>
  {% for r in recommendations %}
  <tr>
    <td>{{ loop.index }}</td>
    <td>{{ r.accion }}</td>
    <td><span class="badge badge-{{ r.impacto }}">{{ r.impacto | upper }}</span></td>
    <td><span class="badge badge-{{ r.facilidad }}">{{ r.facilidad | upper }}</span></td>
  </tr>
  {% endfor %}
</table>

<!-- ====================================================== -->
<h2>5. Próximos Pasos</h2>
<p>{{ next_steps }}</p>

<!-- ====================================================== -->
<div class="footer">
  Generado por RGA Copilot · Equipo 5 Tecnológico de Monterrey Campus Guadalajara ·
  Análisis basado en datos {{ period }}. Las proyecciones son indicativas.
</div>

</body>
</html>
```

- [ ] **Step 2: Verify Jinja2 can render it**

```bash
cd rga-copilot && python - <<'EOF'
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
env = Environment(loader=FileSystemLoader(str(Path("agents/synth/templates"))))
tmpl = env.get_template("memo.html.j2")
html = tmpl.render(
    company="Test", period="ENERO 2026", generated_date="2026-05-24",
    quant_narrative="Narrativa quant.", qual_summary="Resumen cual.",
    signals=[{"rank":1,"titulo":"Test","evidencia_quant":"Q","evidencia_qual":"C","recomendacion":"R","impacto":"alto","facilidad":"alta"}],
    scenarios=[{"name":"Sc1","base_ebitda":1_000_000,"impact_on_ebitda":-50_000,"ebitda_post":950_000}],
    recommendations=[{"accion":"Acción 1","impacto":"alto","facilidad":"alta"}],
    next_steps="Paso siguiente.",
)
assert "<h1>Memo Ejecutivo" in html
assert "ENERO 2026" in html
print("Template OK — ", len(html), "chars")
EOF
```
Expected: `Template OK — NNNN chars`.

- [ ] **Step 3: Commit**

```bash
git add rga-copilot/agents/synth/templates/
git commit -m "feat(synth): add Jinja2 memo HTML template"
```

---

## Task 6: memo_generator.py

**Files:**
- Create: `rga-copilot/agents/synth/memo_generator.py`
- Create: `rga-copilot/tests/test_memo_generator.py`

- [ ] **Step 1: Write failing test**

Create `rga-copilot/tests/test_memo_generator.py`:
```python
"""Tests for MemoGenerator — mock WeasyPrint to avoid system dep in CI."""
import os
import sys
import tempfile
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.synth.models import Signal, Scenario, Recommendation
from agents.synth.memo_generator import MemoGenerator


def _make_sample_data():
    signals = [
        Signal(rank=1, titulo="Sucursal MOR EBITDA negativo",
               evidencia_quant="EBITDA $-100,000", evidencia_qual="Alta rotación personal",
               recomendacion="Revisar estructura de costos", impacto="alto", facilidad="media"),
    ]
    scenarios = [
        Scenario(name="Costo MAKIS +15%", variable="costo_insumo", delta_pct=0.15,
                 affected_target="MAKIS", base_ebitda=2_000_000, impact_on_ebitda=-225_000,
                 ebitda_post=1_775_000),
    ]
    recommendations = [
        Recommendation(accion="Revisar estructura de costos", impacto="alto",
                       facilidad="media", fuente="signal_1"),
    ]
    return signals, scenarios, recommendations


def test_memo_generator_returns_html():
    gen = MemoGenerator()
    signals, scenarios, recs = _make_sample_data()
    html = gen.render_html(
        company="Grupo Nama",
        period="ENERO 2026",
        quant_narrative="Ingresos $9M.",
        qual_summary="Empresa sólida.",
        signals=signals,
        scenarios=scenarios,
        recommendations=recommendations,
        next_steps="Continuar monitoreo.",
    )
    assert "<h1>Memo Ejecutivo" in html
    assert "ENERO 2026" in html
    assert "Sucursal MOR EBITDA negativo" in html
    assert "Revisar estructura de costos" in html


def test_memo_generator_write_pdf_creates_file(tmp_path, monkeypatch):
    """Monkeypatch WeasyPrint so test runs without system cairo libs."""
    import agents.synth.memo_generator as mod

    class FakeHTML:
        def __init__(self, string): pass
        def write_pdf(self, path): open(path, "wb").write(b"%PDF-fake")

    monkeypatch.setattr(mod, "HTML", FakeHTML)

    gen = MemoGenerator()
    signals, scenarios, recs = _make_sample_data()
    html = gen.render_html(
        company="Grupo Nama", period="ENERO 2026",
        quant_narrative="Q", qual_summary="C",
        signals=signals, scenarios=scenarios,
        recommendations=recs, next_steps="Next.",
    )
    pdf_path = gen.write_pdf(html, out_dir=str(tmp_path), period="ENERO 2026")
    assert pdf_path.endswith(".pdf")
    assert os.path.exists(pdf_path)
```

- [ ] **Step 2: Run test — expect ImportError**

```bash
cd rga-copilot && python -m pytest tests/test_memo_generator.py -v 2>&1 | tail -10
```
Expected: `FAILED` — `cannot import name 'MemoGenerator'`.

- [ ] **Step 3: Implement memo_generator.py**

Create `rga-copilot/agents/synth/memo_generator.py`:
```python
"""
MemoGenerator — renders the Jinja2 HTML template and exports to PDF via WeasyPrint.

No LLM calls. Receives pre-computed data from SynthAgent.
"""

from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML   # imported at module level so tests can monkeypatch

from agents.synth.models import Recommendation, Scenario, Signal

_TEMPLATES_DIR = Path(__file__).parent / "templates"


class MemoGenerator:
    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=False,
        )

    def render_html(
        self,
        *,
        company: str,
        period: str,
        quant_narrative: str,
        qual_summary: str,
        signals: list[Signal],
        scenarios: list[Scenario],
        recommendations: list[Recommendation],
        next_steps: str,
        generated_date: str | None = None,
    ) -> str:
        tmpl = self._env.get_template("memo.html.j2")
        return tmpl.render(
            company=company,
            period=period,
            generated_date=generated_date or date.today().isoformat(),
            quant_narrative=quant_narrative,
            qual_summary=qual_summary,
            signals=[s.model_dump() for s in signals],
            scenarios=[s.model_dump() for s in scenarios],
            recommendations=[r.model_dump() for r in recommendations],
            next_steps=next_steps,
        )

    def write_pdf(self, html: str, *, out_dir: str, period: str) -> str:
        """Render html → PDF and return absolute file path."""
        os.makedirs(out_dir, exist_ok=True)
        safe_period = re.sub(r"\s+", "_", period.upper())
        filename = f"memo_{safe_period}.pdf"
        out_path = os.path.join(out_dir, filename)
        HTML(string=html).write_pdf(out_path)
        return out_path
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd rga-copilot && python -m pytest tests/test_memo_generator.py -v 2>&1 | tail -10
```
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add rga-copilot/agents/synth/memo_generator.py \
        rga-copilot/tests/test_memo_generator.py
git commit -m "feat(synth): MemoGenerator — Jinja2 render + WeasyPrint PDF export"
```

---

## Task 7: Signal Synthesis Prompt

**Files:**
- Create: `rga-copilot/agents/synth/prompts/signal_synthesis.txt`

- [ ] **Step 1: Create prompts directory and prompt file**

```bash
mkdir -p rga-copilot/agents/synth/prompts
```

Create `rga-copilot/agents/synth/prompts/signal_synthesis.txt`:
```
Eres un analista financiero senior de RGA (Roque Gardea Asociados).
Estás analizando los resultados del cliente: {company}, período: {period}.

A continuación recibes:
1. ANÁLISIS CUANTITATIVO (KPIs, alertas, top productos)
2. ANÁLISIS CUALITATIVO (señales, sentiment, hipótesis/resumen)

Tu tarea: identificar las 3 señales de mayor impacto estratégico, cruzando evidencia cuantitativa con contexto cualitativo.

INSTRUCCIONES:
- Cita cifras exactas del JSON cuantitativo. No inventes números.
- Para evidencia_qual: usa hypotheses si existen; si están vacías, usa riesgos y summary del análisis cualitativo.
- impacto: "alto" si afecta EBITDA >5% o implica riesgo de continuidad. "medio" si afecta margen sin riesgo inmediato. "bajo" en cualquier otro caso.
- facilidad: "alta" si la acción es operativa y ejecutable en <4 semanas. "media" si requiere inversión o cambio de proceso. "baja" si requiere reestructura estratégica.
- next_steps: párrafo de 3–4 oraciones con acciones concretas para las próximas 4 semanas. En español.

REGLA CRÍTICA: Si hypotheses está vacío [], usa los campos "riesgos" de signals_qual para la columna evidencia_qual.

Devuelve ÚNICAMENTE JSON con esta estructura (sin markdown, sin texto extra):
{{
  "signals": [
    {{
      "rank": 1,
      "titulo": "string (máx 60 chars)",
      "evidencia_quant": "string con cifras específicas del JSON",
      "evidencia_qual": "string con contexto cualitativo",
      "recomendacion": "string (una acción concreta)",
      "impacto": "alto|medio|bajo",
      "facilidad": "alta|media|baja"
    }},
    {{ "rank": 2, ... }},
    {{ "rank": 3, ... }}
  ],
  "next_steps": "string (párrafo 3–4 oraciones)"
}}

--- ANÁLISIS CUANTITATIVO ---
{quant_json}

--- ANÁLISIS CUALITATIVO ---
{qual_json}
```

- [ ] **Step 2: Verify file loads without error**

```bash
cd rga-copilot && python -c "
from pathlib import Path
p = Path('agents/synth/prompts/signal_synthesis.txt')
tmpl = p.read_text(encoding='utf-8')
assert '{quant_json}' in tmpl and '{qual_json}' in tmpl
print('Prompt template OK —', len(tmpl), 'chars')
"
```
Expected: `Prompt template OK — NNN chars`.

- [ ] **Step 3: Commit**

```bash
git add rga-copilot/agents/synth/prompts/
git commit -m "feat(synth): add signal synthesis prompt template"
```

---

## Task 8: SynthAgent

**Files:**
- Create: `rga-copilot/agents/synth/agent.py`
- Create: `rga-copilot/tests/test_synth_agent.py`

- [ ] **Step 1: Write failing test**

Create `rga-copilot/tests/test_synth_agent.py`:
```python
"""
Tests for SynthAgent — mocks Claude, WeasyPrint.
"""
import json
import os
import sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch
from agents.synth.agent import SynthAgent
from agents.synth.models import SynthOutput, Signal, Scenario


# ---------------------------------------------------------------------------
# Minimal QuantOutput + QualOutput fixtures
# ---------------------------------------------------------------------------

def _make_quant():
    q = MagicMock()
    q.period = "ENERO 2026"
    q.narrative = "Ingresos $8.9M, EBITDA $1.8M."
    q.alerts = []
    q.kpis = {
        "consolidado": {"ebitda_total": 2_000_000.0, "ingresos_total": 10_000_000.0},
        "por_categoria": [
            {"categoria": "MAKIS",    "ingresos": 5_000_000.0, "costo": 1_500_000.0, "margen_bruto": 0.70, "pct_total_ingresos": 0.50},
            {"categoria": "BEBIDAS",  "ingresos": 3_000_000.0, "costo":   900_000.0, "margen_bruto": 0.70, "pct_total_ingresos": 0.30},
            {"categoria": "DESTILADOS","ingresos": 2_000_000.0,"costo":   800_000.0, "margen_bruto": 0.60, "pct_total_ingresos": 0.20},
        ],
        "por_sucursal": [
            {"sucursal": "ANT", "ebitda": 900_000.0,  "ingresos": 3_500_000.0},
            {"sucursal": "MOR", "ebitda": -100_000.0, "ingresos": 500_000.0},
        ],
    }
    q.top_products = []
    return q


def _make_qual():
    q = MagicMock()
    q.signals = {
        "tipo_empresa": "Restaurante japonés",
        "posicionamiento": "Casual fine dining",
        "fortalezas": ["Crecimiento rápido"],
        "riesgos": ["Alta rotación de personal", "Costos importados"],
        "factores_crecimiento": ["Expansión Morelia"],
        "temas_topicos": ["Cocina japonesa"],
        "sentiment_score": 0.65,
    }
    q.sentiment = 0.65
    q.hypotheses = []     # empty — tests graceful degradation
    q.summary = "Empresa sólida con riesgos de escala."
    return q


CLAUDE_RESPONSE = json.dumps({
    "signals": [
        {
            "rank": 1,
            "titulo": "Sucursal MOR: EBITDA negativo",
            "evidencia_quant": "EBITDA -$100,000",
            "evidencia_qual": "Alta rotación de personal",
            "recomendacion": "Revisar estructura de costos en MOR",
            "impacto": "alto",
            "facilidad": "media",
        },
        {
            "rank": 2,
            "titulo": "Costo insumos importados presiona márgenes",
            "evidencia_quant": "DESTILADOS margen 60%",
            "evidencia_qual": "Costos importados volátiles",
            "recomendacion": "Negociar contratos de precio fijo con proveedores",
            "impacto": "medio",
            "facilidad": "media",
        },
        {
            "rank": 3,
            "titulo": "MAKIS lidera contribución marginal",
            "evidencia_quant": "Ingresos $5M, costo $1.5M",
            "evidencia_qual": "Expansión Morelia como validación",
            "recomendacion": "Ampliar oferta MAKIS en sucursales débiles",
            "impacto": "medio",
            "facilidad": "alta",
        },
    ],
    "next_steps": "Priorizar auditoría de MOR en próximas 2 semanas.",
})


def test_synth_agent_run_returns_synth_output(tmp_path):
    fake_message = MagicMock()
    fake_message.content = [MagicMock(text=CLAUDE_RESPONSE)]

    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_message

    quant = _make_quant()
    qual  = _make_qual()

    with patch("agents.synth.memo_generator.HTML") as fake_html:
        fake_html.return_value.write_pdf = lambda path: open(path, "wb").write(b"%PDF")
        agent = SynthAgent(company="Grupo Nama", claude_client=fake_client,
                           memo_out_dir=str(tmp_path))
        result = agent.run(quant, qual)

    assert isinstance(result, SynthOutput)
    assert len(result.signals) == 3
    assert result.signals[0].rank == 1
    assert result.signals[0].impacto == "alto"
    assert len(result.scenarios) == 3
    assert result.memo_html != ""
    assert result.memo_pdf_path.endswith(".pdf")
    assert result.next_steps != ""


def test_synth_agent_recommendations_derived_from_signals(tmp_path):
    fake_message = MagicMock()
    fake_message.content = [MagicMock(text=CLAUDE_RESPONSE)]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_message

    with patch("agents.synth.memo_generator.HTML") as fake_html:
        fake_html.return_value.write_pdf = lambda path: open(path, "wb").write(b"%PDF")
        agent = SynthAgent(company="Grupo Nama", claude_client=fake_client,
                           memo_out_dir=str(tmp_path))
        result = agent.run(_make_quant(), _make_qual())

    assert len(result.recommendations) == 3
    assert result.recommendations[0].fuente == "signal_1"
    assert result.recommendations[0].impacto == "alto"
```

- [ ] **Step 2: Run test — expect ImportError**

```bash
cd rga-copilot && python -m pytest tests/test_synth_agent.py -v 2>&1 | tail -10
```
Expected: `FAILED` — `cannot import name 'SynthAgent'`.

- [ ] **Step 3: Implement agent.py**

Create `rga-copilot/agents/synth/agent.py`:
```python
"""
SynthAgent — synthesizes QuantOutput + QualOutput into SynthOutput.

One Claude call extracts top-3 signals + next_steps.
Deterministic scenario builder runs without LLM.
MemoGenerator renders HTML + PDF.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

from agents.quant.agent import QuantOutput
from agents.qual.models import QualOutput
from agents.synth.memo_generator import MemoGenerator
from agents.synth.models import Recommendation, Signal, SynthOutput
from agents.synth.scenario_builder import build_default_scenarios

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent / "prompts" / "signal_synthesis.txt"
_PROMPT_TEMPLATE = _PROMPT_PATH.read_text(encoding="utf-8")


class SynthAgent:
    def __init__(
        self,
        company: str = "Grupo Nama",
        model: str = "claude-sonnet-4-6",
        claude_client=None,
        memo_out_dir: str = "data/outputs",
    ) -> None:
        self._company = company
        self._model = model
        self._client = claude_client or anthropic.Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"]
        )
        self._memo_gen = MemoGenerator()
        self._memo_out_dir = memo_out_dir

    # ------------------------------------------------------------------

    def run(self, quant: QuantOutput, qual: QualOutput) -> SynthOutput:
        signals, next_steps = self._extract_signals(quant, qual)
        scenarios = build_default_scenarios(quant)
        recommendations = self._derive_recommendations(signals)
        html = self._memo_gen.render_html(
            company=self._company,
            period=quant.period,
            quant_narrative=quant.narrative,
            qual_summary=qual.summary,
            signals=signals,
            scenarios=scenarios,
            recommendations=recommendations,
            next_steps=next_steps,
        )
        pdf_path = self._memo_gen.write_pdf(
            html, out_dir=self._memo_out_dir, period=quant.period
        )
        return SynthOutput(
            signals=signals,
            scenarios=scenarios,
            recommendations=recommendations,
            next_steps=next_steps,
            memo_html=html,
            memo_pdf_path=pdf_path,
        )

    # ------------------------------------------------------------------

    def _extract_signals(
        self, quant: QuantOutput, qual: QualOutput
    ) -> tuple[list[Signal], str]:
        prompt = _PROMPT_TEMPLATE.format(
            company=self._company,
            period=quant.period,
            quant_json=json.dumps(
                {"kpis": quant.kpis, "alerts": [a.model_dump() for a in quant.alerts],
                 "narrative": quant.narrative},
                ensure_ascii=False, indent=2,
            ),
            qual_json=json.dumps(
                {"signals": qual.signals, "sentiment": qual.sentiment,
                 "hypotheses": qual.hypotheses, "summary": qual.summary},
                ensure_ascii=False, indent=2,
            ),
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=1500,
            system=[{
                "type": "text",
                "text": "Responde únicamente con JSON válido. Sin markdown. Sin texto adicional.",
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()

        # Strip accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0].strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("Claude returned malformed JSON in signal extraction: %r", raw[:200])
            parsed = {"signals": [], "next_steps": ""}

        signals = [Signal(**s) for s in parsed.get("signals", [])]
        next_steps = parsed.get("next_steps", "")
        return signals, next_steps

    # ------------------------------------------------------------------

    @staticmethod
    def _derive_recommendations(signals: list[Signal]) -> list[Recommendation]:
        return [
            Recommendation(
                accion=s.recomendacion,
                impacto=s.impacto,
                facilidad=s.facilidad,
                fuente=f"signal_{s.rank}",
            )
            for s in signals
        ]
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd rga-copilot && python -m pytest tests/test_synth_agent.py -v 2>&1 | tail -10
```
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add rga-copilot/agents/synth/agent.py \
        rga-copilot/tests/test_synth_agent.py
git commit -m "feat(synth): SynthAgent — signal extraction via Claude + scenario builder + memo"
```

---

## Task 9: orchestrator.py

**Files:**
- Create: `rga-copilot/orchestrator.py`
- Create: `rga-copilot/tests/test_orchestrator.py`

**Note on Alert model mismatch:** `QuantOutput.alerts` uses `agents.quant.alert_detector.Alert` (fields: `level, tipo, sucursal, sku, mensaje, valor`). `QualAgent.run()` expects `list[agents.qual.models.Alert]` (fields: `sucursal, message, severity`). The orchestrator adapter converts between them here — neither agent is changed.

- [ ] **Step 1: Write failing tests**

Create `rga-copilot/tests/test_orchestrator.py`:
```python
"""
Tests for orchestrator.py — mocks pipeline + all three agents.
"""
import os
import sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch
from orchestrator import run_analysis, _normalize_alerts


# ---------------------------------------------------------------------------
# Alert adapter
# ---------------------------------------------------------------------------

def test_normalize_alerts_converts_red():
    from agents.quant.alert_detector import Alert as QuantAlert
    qa = QuantAlert(level="red", tipo="ebitda_negativo", sucursal="MOR",
                    sku=None, mensaje="EBITDA negativo en MOR.", valor=-100_000.0)
    result = _normalize_alerts([qa])
    assert len(result) == 1
    assert result[0].severity == "red"
    assert result[0].message == "EBITDA negativo en MOR."
    assert result[0].sucursal == "MOR"


def test_normalize_alerts_converts_warning_to_yellow():
    from agents.quant.alert_detector import Alert as QuantAlert
    qa = QuantAlert(level="warning", tipo="nomina_excesiva", sucursal="SOK",
                    sku=None, mensaje="Nómina excesiva.", valor=0.38)
    result = _normalize_alerts([qa])
    assert result[0].severity == "yellow"


def test_normalize_alerts_handles_none_sucursal():
    from agents.quant.alert_detector import Alert as QuantAlert
    qa = QuantAlert(level="warning", tipo="producto_margen_negativo", sucursal=None,
                    sku="MAKI X", mensaje="Margen negativo.", valor=-500.0)
    result = _normalize_alerts([qa])
    assert result[0].sucursal == ""


def test_run_analysis_wires_all_agents(tmp_path):
    """Full orchestrator mock — verify agents are called with correct types."""
    from agents.synth.models import SynthOutput, Signal, Scenario, Recommendation

    mock_db = MagicMock()
    mock_quant_out = MagicMock()
    mock_quant_out.period = "ENERO 2026"
    mock_quant_out.narrative = "Narrativa."
    mock_quant_out.alerts = []
    mock_quant_out.kpis = {
        "consolidado": {"ebitda_total": 1_000_000.0, "ingresos_total": 5_000_000.0},
        "por_categoria": [
            {"categoria": "MAKIS", "ingresos": 3_000_000.0, "costo": 900_000.0,
             "margen_bruto": 0.70, "pct_total_ingresos": 0.60},
            {"categoria": "BEBIDAS", "ingresos": 2_000_000.0, "costo": 700_000.0,
             "margen_bruto": 0.65, "pct_total_ingresos": 0.40},
        ],
        "por_sucursal": [
            {"sucursal": "ANT", "ebitda": 800_000.0, "ingresos": 3_000_000.0},
            {"sucursal": "MOR", "ebitda": 200_000.0, "ingresos": 2_000_000.0},
        ],
    }
    mock_quant_out.top_products = []

    mock_qual_out = MagicMock()
    mock_qual_out.signals = {}
    mock_qual_out.sentiment = 0.5
    mock_qual_out.hypotheses = []
    mock_qual_out.summary = ""

    fake_signal = Signal(rank=1, titulo="T1", evidencia_quant="Q", evidencia_qual="C",
                         recomendacion="R", impacto="alto", facilidad="alta")
    fake_scenario = Scenario(name="S1", variable="costo_insumo", delta_pct=0.15,
                             affected_target="MAKIS", base_ebitda=1_000_000,
                             impact_on_ebitda=-135_000, ebitda_post=865_000)
    fake_rec = Recommendation(accion="R", impacto="alto", facilidad="alta", fuente="signal_1")
    mock_synth_out = SynthOutput(
        signals=[fake_signal], scenarios=[fake_scenario], recommendations=[fake_rec],
        next_steps="Paso.", memo_html="<html></html>", memo_pdf_path="/tmp/memo.pdf",
    )

    with patch("orchestrator.load") as mock_load, \
         patch("orchestrator.clean") as mock_clean, \
         patch("orchestrator.QuantAgent") as MockQuant, \
         patch("orchestrator.QualAgent") as MockQual, \
         patch("orchestrator.SynthAgent") as MockSynth:

        mock_load.return_value = MagicMock()
        mock_clean.return_value = mock_db
        MockQuant.return_value.run.return_value = mock_quant_out
        MockQual.return_value.run.return_value = mock_qual_out
        MockSynth.return_value.run.return_value = mock_synth_out

        result = run_analysis(
            csv_path="fake.csv",
            xlsx_path="fake.xlsx",
            qual_docs=[],
            period="ENERO 2026",
        )

    assert result.period == "ENERO 2026"
    assert result.quant == mock_quant_out
    assert result.qual == mock_qual_out
    assert result.synth == mock_synth_out

    # Verify QualAgent received normalized (qual-type) alerts
    call_args = MockQual.return_value.run.call_args
    qual_alerts_arg = call_args[1].get("quant_alerts", call_args[0][1] if len(call_args[0]) > 1 else [])
    # alerts is empty list so normalization produces empty — just check call happened
    MockQual.return_value.run.assert_called_once()
```

- [ ] **Step 2: Run test — expect ImportError**

```bash
cd rga-copilot && python -m pytest tests/test_orchestrator.py -v 2>&1 | tail -10
```
Expected: `FAILED` — `No module named 'orchestrator'`.

- [ ] **Step 3: Implement orchestrator.py**

Create `rga-copilot/orchestrator.py`:
```python
"""
Orchestrator — top-level entry point for the RGA Copilot pipeline.

run_analysis(csv_path, xlsx_path, qual_docs, period) → AnalysisResult

Pipeline:
    load(csv, xlsx) → RawData
    clean(raw) → LocalDB
    QuantAgent.run(period, db) → QuantOutput
    _normalize_alerts(quant.alerts) → list[QualAlert]   ← Alert model adapter
    QualAgent.run(qual_docs, qual_alerts) → QualOutput
    SynthAgent.run(quant, qual) → SynthOutput
    → AnalysisResult

Alert model adapter:
    QuantAlert (agents.quant.alert_detector.Alert):
        level: "red"|"warning", tipo: str, sucursal: str|None,
        sku: str|None, mensaje: str, valor: float|None
    QualAlert (agents.qual.models.Alert):
        sucursal: str, message: str, severity: "red"|"yellow"
    Mapping: level=="red" → severity="red"; else → severity="yellow"
             mensaje → message; sucursal or "" → sucursal
"""

from __future__ import annotations

import logging
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

from agents.qual.agent import QualAgent
from agents.qual.embedder import ChromaStore, SentenceTransformerEmbedder
from agents.qual.models import Alert as QualAlert
from agents.qual.models import QualDoc
from agents.quant.agent import QuantAgent
from agents.quant.alert_detector import Alert as QuantAlert
from agents.synth.agent import SynthAgent
from agents.synth.models import AnalysisResult
from pipeline.cleaning import clean
from pipeline.ingestion import load

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Alert model adapter
# ---------------------------------------------------------------------------

def _normalize_alerts(quant_alerts: list[QuantAlert]) -> list[QualAlert]:
    """Convert QuantAgent Alert list to QualAgent Alert list."""
    return [
        QualAlert(
            sucursal=a.sucursal or "",
            message=a.mensaje,
            severity="red" if a.level == "red" else "yellow",
        )
        for a in quant_alerts
    ]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_analysis(
    csv_path: str,
    xlsx_path: str,
    qual_docs: list[str],
    period: str,
    company: str = "Grupo Nama",
    chroma_persist_path: str = "data/vector_store",
    memo_out_dir: str = "data/outputs",
) -> AnalysisResult:
    """
    Full analysis pipeline.

    Args:
        csv_path: Path to BD 2026 CSV file.
        xlsx_path: Path to GASTOS/NÓMINA Excel file.
        qual_docs: List of file paths (PDF, image, text) for qualitative analysis.
        period: Period string, e.g. "ENERO 2026".
        company: Client name for narratives.
        chroma_persist_path: Directory for ChromaDB vector store.
        memo_out_dir: Directory to write the PDF memo.

    Returns:
        AnalysisResult with quant, qual, and synth sub-results.
    """
    logger.info("Orchestrator: loading data for period=%s", period)
    raw = load(csv_path, xlsx_path)
    db  = clean(raw)

    logger.info("Orchestrator: running QuantAgent")
    quant_agent = QuantAgent(company=company)
    quant = quant_agent.run(period=period, db=db)

    logger.info("Orchestrator: running QualAgent (docs=%d, alerts=%d)",
                len(qual_docs), len(quant.alerts))
    claude_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    embedder = SentenceTransformerEmbedder()
    chroma_store = ChromaStore(
        persist_path=chroma_persist_path,
        collection_name=f"rga_{company.lower().replace(' ', '_')}",
        embedder=embedder,
    )
    qual_agent = QualAgent(
        schema_path="agents/qual/config/nama_signals.yaml",
        chroma_store=chroma_store,
        claude_client=claude_client,
    )
    qual_docs_typed = [QualDoc(path=p) for p in qual_docs]
    qual_alerts     = _normalize_alerts(quant.alerts)
    qual = qual_agent.run(docs=qual_docs_typed, quant_alerts=qual_alerts)

    logger.info("Orchestrator: running SynthAgent")
    synth_agent = SynthAgent(
        company=company,
        claude_client=claude_client,
        memo_out_dir=memo_out_dir,
    )
    synth = synth_agent.run(quant, qual)

    return AnalysisResult(period=period, quant=quant, qual=qual, synth=synth)
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd rga-copilot && python -m pytest tests/test_orchestrator.py -v 2>&1 | tail -12
```
Expected: `4 passed`.

- [ ] **Step 5: Run full test suite — verify no regressions**

```bash
cd rga-copilot && python -m pytest tests/ -v --ignore=tests/test_quant_agent.py 2>&1 | tail -15
```

(`test_quant_agent.py` is a script, not a proper pytest file — exclude it.)

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add rga-copilot/orchestrator.py \
        rga-copilot/tests/test_orchestrator.py
git commit -m "feat: add orchestrator — Alert adapter + run_analysis() wiring all agents"
```

---

## Task 10: Smoke Test End-to-End

Runs with real API keys and real Excel data. Not in CI — manual validation only.

**Files:**
- Create: `rga-copilot/scripts/smoke_test_synth.py`

- [ ] **Step 1: Create smoke test script**

Create `rga-copilot/scripts/smoke_test_synth.py`:
```python
"""
Smoke test: full pipeline with real data.
Run from rga-copilot/: python scripts/smoke_test_synth.py

Requires:
  - .env with ANTHROPIC_API_KEY
  - ../TEC SG - GN (Interno).xlsx
  - ../TEC SG 2 - Grupo Nama (Interno) - BD 2026.csv
"""

import logging
import sys
import os

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
sys.path.insert(0, os.path.dirname(__file__) + "/..")

from orchestrator import run_analysis

CSV  = "../TEC SG 2 - Grupo Nama (Interno) - BD 2026.csv"
XLSX = "../TEC SG - GN (Interno).xlsx"
QUAL = ["agents/qual/Grupo_NAMA_Overview_RGA.md"]
PERIOD = "ENERO 2026"

print(f"Running full pipeline for {PERIOD}...")
result = run_analysis(
    csv_path=CSV,
    xlsx_path=XLSX,
    qual_docs=QUAL,
    period=PERIOD,
)

print("\n=== AnalysisResult ===")
print(f"Period: {result.period}")
print(f"EBITDA total: ${result.quant.kpis['consolidado']['ebitda_total']:,.0f}")
print(f"Alerts: {len(result.quant.alerts)}")
print(f"Qual sentiment: {result.qual.sentiment:.2f}")
print(f"\nTop 3 signals:")
for s in result.synth.signals:
    print(f"  [{s.rank}] {s.titulo} — impacto={s.impacto}, facilidad={s.facilidad}")
print(f"\nScenarios:")
for sc in result.synth.scenarios:
    sign = "+" if sc.impact_on_ebitda >= 0 else ""
    print(f"  {sc.name}: impact ${sign}{sc.impact_on_ebitda:,.0f}")
print(f"\nMemo PDF: {result.synth.memo_pdf_path}")
assert os.path.exists(result.synth.memo_pdf_path), "PDF file was not created!"
print("\nSMOKE TEST PASSED")
```

- [ ] **Step 2: Run smoke test**

```bash
cd rga-copilot && python scripts/smoke_test_synth.py 2>&1
```

Expected output:
```
Running full pipeline for ENERO 2026...
=== AnalysisResult ===
Period: ENERO 2026
EBITDA total: $1,866,259
Alerts: N
Qual sentiment: 0.65

Top 3 signals:
  [1] <titulo> — impacto=alto, facilidad=<level>
  [2] ...
  [3] ...

Scenarios:
  <Scenario 1 name>: impact $-NNN,NNN
  ...
Memo PDF: data/outputs/memo_ENERO_2026.pdf

SMOKE TEST PASSED
```

- [ ] **Step 3: Verify PDF exists and is non-empty**

```bash
ls -lh rga-copilot/data/outputs/memo_ENERO_2026.pdf
```
Expected: file size > 10KB (a real WeasyPrint PDF is typically 50–200KB).

- [ ] **Step 4: Commit**

```bash
git add rga-copilot/scripts/smoke_test_synth.py
git commit -m "test: add smoke_test_synth.py for end-to-end pipeline validation"
```

---

## Self-Review Checklist

### Spec Coverage

| Spec requirement | Task |
|-----------------|------|
| Top 3 señales con evidencia cuanti+cuali | Task 8 — `_extract_signals()` |
| Escenarios what-if determinísticos | Task 4 — `scenario_builder.py` |
| Escenario 1: costo insumo +X% | `build_scenario_costo_insumo()` |
| Escenario 2: cierre sucursal | `build_scenario_cierre_sucursal()` |
| Escenario 3: cambio mix productos | `build_scenario_shift_mix()` |
| Memo ejecutivo 5 secciones | Task 5 — `memo.html.j2` |
| Exportación PDF | Task 6 — `write_pdf()` |
| Orquestador `run_analysis()` | Task 9 |
| Contratos Pydantic entre agentes | Tasks 2+3 — `AnalysisResult`, `SynthOutput` |
| Degradación cuando hypotheses vacío | Task 7 — prompt instructions + Task 8 agent |
| Alert model adapter | Task 9 — `_normalize_alerts()` |

### Known Gaps (Out of Scope)

| Gap | Where documented |
|-----|-----------------|
| `QuantOutput` missing `forecast` field | Memo forecast section is absent from template; conditional rendering not needed since data won't exist |
| `QualAgent.hypotheses` always `[]` | Prompt instructs Claude to use `riesgos` + `summary` when list is empty |
| FastAPI routes | Sprint 3 scope — not in this plan |
| React frontend | Sprint 4 scope — not in this plan |
