# Nómina & Break-Even Scenarios Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two nómina what-if scenarios and a break-even ticket solver to `scenario_builder.py`, with a new `BreakEvenResult` Pydantic model.

**Architecture:** `BreakEvenResult` goes in `models.py`. Three new functions go in `scenario_builder.py`. `build_default_scenarios` is updated to return 5 scenarios. `solve_break_even_ticket` is call-only (requires user-supplied inputs). All changes are pure Python/math — no LLM calls.

**Tech Stack:** Python 3.11, Pydantic v2, pytest. Run tests from `rga-copilot/` with `.venv/bin/pytest tests/test_scenario_builder.py -v`.

---

### Task 1: Add `BreakEvenResult` model

**Files:**
- Modify: `rga-copilot/agents/synth/models.py`
- Test: `rga-copilot/tests/test_scenario_builder.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_scenario_builder.py` (after existing imports):

```python
from agents.synth.models import Scenario, BreakEvenResult

def test_break_even_result_model():
    r = BreakEvenResult(
        sucursal="D",
        target_ebitda=200_000.0,
        current_ebitda=96_850.0,
        current_ticket=350.0,
        required_ticket=425.0,
        ticket_delta_pct=(425.0 - 350.0) / 350.0,
        transacciones=1_200,
    )
    assert r.sucursal == "D"
    assert r.required_ticket == pytest.approx(425.0)
    assert r.ticket_delta_pct == pytest.approx(0.2143, abs=1e-3)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd rga-copilot && .venv/bin/pytest tests/test_scenario_builder.py::test_break_even_result_model -v
```

Expected: `ImportError` — `cannot import name 'BreakEvenResult'`

- [ ] **Step 3: Add `BreakEvenResult` to `models.py`**

Add after the `Scenario` class in `rga-copilot/agents/synth/models.py`:

```python
class BreakEvenResult(BaseModel):
    sucursal: str
    target_ebitda: float        # user-supplied target (MXN)
    current_ebitda: float       # branch EBITDA for the period
    current_ticket: float       # avg ticket today (MXN)
    required_ticket: float      # ticket needed to hit target_ebitda
    ticket_delta_pct: float     # (required_ticket - current_ticket) / current_ticket
    transacciones: int          # held fixed in the solve
```

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/bin/pytest tests/test_scenario_builder.py::test_break_even_result_model -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add rga-copilot/agents/synth/models.py rga-copilot/tests/test_scenario_builder.py
git commit -m "feat(models): add BreakEvenResult Pydantic model"
```

---

### Task 2: Expand test fixture for new scenarios

**Files:**
- Modify: `rga-copilot/tests/test_scenario_builder.py`

The existing `QUANT_KPIS` fixture is missing fields the new functions need. Replace `QUANT_KPIS` and `FakeQuantOutput` entirely.

- [ ] **Step 1: Replace `QUANT_KPIS` in `tests/test_scenario_builder.py`**

Replace the existing `QUANT_KPIS` dict with:

```python
QUANT_KPIS = {
    "consolidado": {
        "ebitda_total": 2_000_000.0,
        "ingresos_total": 10_000_000.0,
        "nomina_total": 1_200_000.0,   # sum of all branch + corporate nomina
    },
    "por_categoria": [
        {"categoria": "MAKIS",     "ingresos": 5_000_000.0, "costo": 1_500_000.0, "margen_bruto": 0.70, "pct_total_ingresos": 0.50},
        {"categoria": "BEBIDAS",   "ingresos": 3_000_000.0, "costo":   900_000.0, "margen_bruto": 0.70, "pct_total_ingresos": 0.30},
        {"categoria": "DESTILADOS","ingresos": 2_000_000.0, "costo":   800_000.0, "margen_bruto": 0.60, "pct_total_ingresos": 0.20},
    ],
    "por_sucursal": [
        {
            "sucursal": "ANT", "ebitda": 900_000.0, "ingresos": 3_500_000.0,
            "nomina": 400_000.0, "gastos_operativos": 200_000.0,
            "margen_bruto": 0.69, "ticket_promedio": 500.0, "transacciones": 7_000,
        },
        {
            "sucursal": "SOK", "ebitda": 700_000.0, "ingresos": 2_500_000.0,
            "nomina": 350_000.0, "gastos_operativos": 150_000.0,
            "margen_bruto": 0.68, "ticket_promedio": 420.0, "transacciones": 5_952,
        },
        {
            "sucursal": "MOR", "ebitda": -100_000.0, "ingresos": 500_000.0,
            "nomina": 200_000.0, "gastos_operativos": 80_000.0,
            "margen_bruto": 0.56, "ticket_promedio": 250.0, "transacciones": 2_000,
        },
        {
            "sucursal": "CAM", "ebitda": 300_000.0, "ingresos": 2_000_000.0,
            "nomina": 150_000.0, "gastos_operativos": 100_000.0,
            "margen_bruto": 0.275, "ticket_promedio": 380.0, "transacciones": 5_263,
        },
        {
            "sucursal": "JUR", "ebitda": 200_000.0, "ingresos": 1_500_000.0,
            "nomina": 100_000.0, "gastos_operativos": 70_000.0,
            "margen_bruto": 0.245, "ticket_promedio": 300.0, "transacciones": 5_000,
        },
    ],
}
```

- [ ] **Step 2: Run existing tests to confirm no regressions**

```bash
.venv/bin/pytest tests/test_scenario_builder.py -v
```

Expected: all existing tests PASS (fixture fields are additive — nothing removed).

- [ ] **Step 3: Commit**

```bash
git add rga-copilot/tests/test_scenario_builder.py
git commit -m "test(scenarios): expand fixture with nomina/gastos/ticket fields"
```

---

### Task 3: Add `build_scenario_reduccion_nomina`

**Files:**
- Modify: `rga-copilot/agents/synth/scenario_builder.py`
- Test: `rga-copilot/tests/test_scenario_builder.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_scenario_builder.py`:

```python
from agents.synth.scenario_builder import (
    build_scenario_costo_insumo,
    build_scenario_cierre_sucursal,
    build_scenario_shift_mix,
    build_scenario_reduccion_nomina,
    build_default_scenarios,
)

def test_reduccion_nomina_impact():
    # ANT nomina = 400_000; 10% reduction → +40_000 impact
    sc = build_scenario_reduccion_nomina(Q, sucursal="ANT", delta_pct=0.10)
    assert sc.variable == "reduccion_nomina"
    assert sc.affected_target == "ANT"
    assert sc.impact_on_ebitda == pytest.approx(40_000.0)
    assert sc.ebitda_post == pytest.approx(2_040_000.0)
    assert sc.base_ebitda == pytest.approx(2_000_000.0)

def test_reduccion_nomina_unknown_sucursal():
    with pytest.raises(ValueError, match="Sucursal"):
        build_scenario_reduccion_nomina(Q, sucursal="ZZZ")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/test_scenario_builder.py::test_reduccion_nomina_impact tests/test_scenario_builder.py::test_reduccion_nomina_unknown_sucursal -v
```

Expected: `ImportError` — `cannot import name 'build_scenario_reduccion_nomina'`

- [ ] **Step 3: Implement in `scenario_builder.py`**

Add after `build_scenario_shift_mix`, before `build_default_scenarios`:

```python
def build_scenario_reduccion_nomina(
    quant,
    sucursal: str,
    delta_pct: float = 0.10,
) -> Scenario:
    """Reduce payroll at `sucursal` by `delta_pct` — positive EBITDA impact."""
    kpis = quant.kpis
    base_ebitda = kpis["consolidado"]["ebitda_total"]

    branch_map = {b["sucursal"]: b for b in kpis["por_sucursal"]}
    if sucursal not in branch_map:
        raise ValueError(f"Sucursal '{sucursal}' not found. Available: {list(branch_map)}")

    nomina_sucursal = branch_map[sucursal]["nomina"]
    impact = nomina_sucursal * delta_pct   # saving → positive

    return Scenario(
        name=f"Reducción nómina {sucursal} -{delta_pct:.0%}",
        variable="reduccion_nomina",
        delta_pct=delta_pct,
        affected_target=sucursal,
        base_ebitda=base_ebitda,
        impact_on_ebitda=impact,
        ebitda_post=base_ebitda + impact,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_scenario_builder.py::test_reduccion_nomina_impact tests/test_scenario_builder.py::test_reduccion_nomina_unknown_sucursal -v
```

Expected: both PASS

- [ ] **Step 5: Commit**

```bash
git add rga-copilot/agents/synth/scenario_builder.py rga-copilot/tests/test_scenario_builder.py
git commit -m "feat(scenarios): add build_scenario_reduccion_nomina"
```

---

### Task 4: Add `build_scenario_incremento_salarial`

**Files:**
- Modify: `rga-copilot/agents/synth/scenario_builder.py`
- Test: `rga-copilot/tests/test_scenario_builder.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_scenario_builder.py`:

```python
from agents.synth.scenario_builder import (
    build_scenario_costo_insumo,
    build_scenario_cierre_sucursal,
    build_scenario_shift_mix,
    build_scenario_reduccion_nomina,
    build_scenario_incremento_salarial,
    build_default_scenarios,
)

def test_incremento_salarial_impact():
    # consolidado nomina_total = 1_200_000; 10% increase → -120_000 impact
    sc = build_scenario_incremento_salarial(Q, delta_pct=0.10)
    assert sc.variable == "incremento_salarial"
    assert sc.affected_target == "todas las sucursales"
    assert sc.impact_on_ebitda == pytest.approx(-120_000.0)
    assert sc.ebitda_post == pytest.approx(1_880_000.0)
    assert sc.base_ebitda == pytest.approx(2_000_000.0)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/test_scenario_builder.py::test_incremento_salarial_impact -v
```

Expected: `ImportError` — `cannot import name 'build_scenario_incremento_salarial'`

- [ ] **Step 3: Implement in `scenario_builder.py`**

Add after `build_scenario_reduccion_nomina`:

```python
def build_scenario_incremento_salarial(
    quant,
    delta_pct: float = 0.10,
) -> Scenario:
    """Mandatory salary increase applied to all branches — negative EBITDA impact."""
    kpis = quant.kpis
    base_ebitda  = kpis["consolidado"]["ebitda_total"]
    nomina_total = kpis["consolidado"]["nomina_total"]
    impact = -nomina_total * delta_pct   # cost increase → negative

    return Scenario(
        name=f"Incremento salarial +{delta_pct:.0%} (todas las sucursales)",
        variable="incremento_salarial",
        delta_pct=delta_pct,
        affected_target="todas las sucursales",
        base_ebitda=base_ebitda,
        impact_on_ebitda=impact,
        ebitda_post=base_ebitda + impact,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/bin/pytest tests/test_scenario_builder.py::test_incremento_salarial_impact -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add rga-copilot/agents/synth/scenario_builder.py rga-copilot/tests/test_scenario_builder.py
git commit -m "feat(scenarios): add build_scenario_incremento_salarial"
```

---

### Task 5: Add `solve_break_even_ticket`

**Files:**
- Modify: `rga-copilot/agents/synth/scenario_builder.py`
- Test: `rga-copilot/tests/test_scenario_builder.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_scenario_builder.py`:

```python
from agents.synth.models import Scenario, BreakEvenResult
from agents.synth.scenario_builder import (
    build_scenario_costo_insumo,
    build_scenario_cierre_sucursal,
    build_scenario_shift_mix,
    build_scenario_reduccion_nomina,
    build_scenario_incremento_salarial,
    solve_break_even_ticket,
    build_default_scenarios,
)

def test_break_even_ticket_above_current():
    # MOR: ebitda=-100_000, gastos=80_000, nomina=200_000, margen=0.56, transacciones=2_000, ticket=250
    # target_ebitda=0: ticket_req = (0 + 80_000 + 200_000) / (2_000 * 0.56) = 280_000 / 1_120 = 250
    # Wait — that means current ticket IS break-even. Let me recalc:
    # Actually current ebitda = ingresos * margen - gastos - nomina
    #   = (250 * 2_000 * 0.56) - 80_000 - 200_000 = 280_000 - 280_000 = 0
    # But fixture says ebitda = -100_000. Use fixture values directly.
    # ticket_req(target=0) = (0 + 80_000 + 200_000) / (2_000 * 0.56) = 250.0
    # ticket_req(target=50_000) = (50_000 + 80_000 + 200_000) / (2_000 * 0.56) = 330_000/1_120 ≈ 294.64
    r = solve_break_even_ticket(Q, sucursal="MOR", target_ebitda=50_000.0)
    assert isinstance(r, BreakEvenResult)
    assert r.sucursal == "MOR"
    assert r.target_ebitda == pytest.approx(50_000.0)
    assert r.current_ticket == pytest.approx(250.0)
    assert r.required_ticket == pytest.approx(294.64, abs=0.1)
    assert r.ticket_delta_pct == pytest.approx((294.64 - 250.0) / 250.0, abs=1e-2)
    assert r.transacciones == 2_000

def test_break_even_ticket_zero_transactions_raises():
    bad_quant_kpis = {
        "consolidado": {"ebitda_total": 0.0, "nomina_total": 0.0},
        "por_categoria": [],
        "por_sucursal": [
            {"sucursal": "X", "ebitda": 0.0, "ingresos": 0.0,
             "nomina": 0.0, "gastos_operativos": 0.0,
             "margen_bruto": 0.5, "ticket_promedio": 0.0, "transacciones": 0},
        ],
    }
    class FakeZero:
        kpis = bad_quant_kpis
    with pytest.raises(ValueError, match="transacciones"):
        solve_break_even_ticket(FakeZero(), sucursal="X", target_ebitda=0.0)

def test_break_even_ticket_zero_margin_raises():
    bad_quant_kpis = {
        "consolidado": {"ebitda_total": 0.0, "nomina_total": 0.0},
        "por_categoria": [],
        "por_sucursal": [
            {"sucursal": "X", "ebitda": 0.0, "ingresos": 100_000.0,
             "nomina": 0.0, "gastos_operativos": 0.0,
             "margen_bruto": 0.0, "ticket_promedio": 200.0, "transacciones": 500},
        ],
    }
    class FakeZeroMargin:
        kpis = bad_quant_kpis
    with pytest.raises(ValueError, match="margen_bruto"):
        solve_break_even_ticket(FakeZeroMargin(), sucursal="X", target_ebitda=0.0)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/test_scenario_builder.py::test_break_even_ticket_above_current tests/test_scenario_builder.py::test_break_even_ticket_zero_transactions_raises tests/test_scenario_builder.py::test_break_even_ticket_zero_margin_raises -v
```

Expected: `ImportError` — `cannot import name 'solve_break_even_ticket'`

- [ ] **Step 3: Implement in `scenario_builder.py`**

Add after `build_scenario_incremento_salarial`, before `build_default_scenarios`. Also add `BreakEvenResult` to the import at the top of the file:

```python
# Change the import line at the top of scenario_builder.py from:
from agents.synth.models import Scenario
# to:
from agents.synth.models import BreakEvenResult, Scenario
```

Then add the function:

```python
def solve_break_even_ticket(
    quant,
    sucursal: str,
    target_ebitda: float = 0.0,
) -> BreakEvenResult:
    """
    Solve for the avg ticket a branch needs to reach `target_ebitda`.

    Assumptions: gross margin % and transaction count are held constant.
    Math: ticket_req = (target_ebitda + gastos + nomina) / (transacciones * margen_bruto)
    """
    kpis = quant.kpis
    branch_map = {b["sucursal"]: b for b in kpis["por_sucursal"]}
    if sucursal not in branch_map:
        raise ValueError(f"Sucursal '{sucursal}' not found. Available: {list(branch_map)}")

    b = branch_map[sucursal]
    transacciones  = b["transacciones"]
    margen_bruto   = b["margen_bruto"]
    gastos         = b["gastos_operativos"]
    nomina         = b["nomina"]
    current_ticket = b["ticket_promedio"]
    current_ebitda = b["ebitda"]

    if transacciones == 0:
        raise ValueError(f"Sucursal '{sucursal}' has transacciones=0; cannot solve.")
    if margen_bruto == 0:
        raise ValueError(f"Sucursal '{sucursal}' has margen_bruto=0; cannot solve.")

    required_ticket = (target_ebitda + gastos + nomina) / (transacciones * margen_bruto)
    ticket_delta_pct = (required_ticket - current_ticket) / current_ticket

    return BreakEvenResult(
        sucursal=sucursal,
        target_ebitda=target_ebitda,
        current_ebitda=current_ebitda,
        current_ticket=current_ticket,
        required_ticket=required_ticket,
        ticket_delta_pct=ticket_delta_pct,
        transacciones=transacciones,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_scenario_builder.py::test_break_even_ticket_above_current tests/test_scenario_builder.py::test_break_even_ticket_zero_transactions_raises tests/test_scenario_builder.py::test_break_even_ticket_zero_margin_raises -v
```

Expected: all 3 PASS

- [ ] **Step 5: Commit**

```bash
git add rga-copilot/agents/synth/scenario_builder.py rga-copilot/tests/test_scenario_builder.py
git commit -m "feat(scenarios): add solve_break_even_ticket"
```

---

### Task 6: Update `build_default_scenarios` to return 5

**Files:**
- Modify: `rga-copilot/agents/synth/scenario_builder.py`
- Test: `rga-copilot/tests/test_scenario_builder.py`

- [ ] **Step 1: Update failing test**

Replace `test_build_default_scenarios_returns_three` in `tests/test_scenario_builder.py`:

```python
def test_build_default_scenarios_returns_five():
    scenarios = build_default_scenarios(Q)
    assert len(scenarios) == 5
    variables = {s.variable for s in scenarios}
    assert variables == {
        "costo_insumo", "cierre_sucursal", "shift_mix",
        "reduccion_nomina", "incremento_salarial",
    }

def test_build_default_scenarios_reduccion_picks_highest_nomina_ratio():
    scenarios = build_default_scenarios(Q)
    reduccion = next(s for s in scenarios if s.variable == "reduccion_nomina")
    # Highest nomina/ingresos: MOR = 200_000/500_000=0.40, SOK=350_000/2_500_000=0.14,
    # ANT=400_000/3_500_000=0.114, CAM=150_000/2_000_000=0.075, JUR=100_000/1_500_000=0.067
    # → MOR wins
    assert reduccion.affected_target == "MOR"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/test_scenario_builder.py::test_build_default_scenarios_returns_five tests/test_scenario_builder.py::test_build_default_scenarios_reduccion_picks_highest_nomina_ratio -v
```

Expected: FAIL — `AssertionError: 3 != 5`

- [ ] **Step 3: Update `build_default_scenarios` in `scenario_builder.py`**

Replace the existing `build_default_scenarios` function entirely:

```python
def build_default_scenarios(quant) -> list[Scenario]:
    """
    Build five predefined scenarios using real data to pick relevant targets:
    1. Raise cost of the highest-cost category by 15%.
    2. Close the branch with the lowest (possibly negative) EBITDA.
    3. Shift 5% of revenue from lowest-margin category → highest-margin category.
    4. Reduce payroll 10% at the branch with the highest nomina/ingresos ratio.
    5. Mandatory 10% salary increase across all branches.
    """
    kpis = quant.kpis
    cats     = kpis["por_categoria"]
    branches = kpis["por_sucursal"]

    if not cats:
        raise ValueError("Cannot build scenarios: por_categoria is empty for this period.")
    if not branches:
        raise ValueError("Cannot build scenarios: por_sucursal is empty for this period.")

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
        cat_from, cat_to = cats[0]["categoria"], cats[-1]["categoria"]
    sc3 = build_scenario_shift_mix(quant, cat_from=cat_from, cat_to=cat_to, delta_pct=0.05)

    # Scenario 4: reducción nómina — branch with highest nomina/ingresos ratio
    most_bloated = max(
        branches,
        key=lambda b: b["nomina"] / b["ingresos"] if b["ingresos"] else 0.0,
    )["sucursal"]
    sc4 = build_scenario_reduccion_nomina(quant, sucursal=most_bloated, delta_pct=0.10)

    # Scenario 5: mandatory salary increase across all branches
    sc5 = build_scenario_incremento_salarial(quant, delta_pct=0.10)

    return [sc1, sc2, sc3, sc4, sc5]
```

- [ ] **Step 4: Run all scenario builder tests**

```bash
.venv/bin/pytest tests/test_scenario_builder.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add rga-copilot/agents/synth/scenario_builder.py rga-copilot/tests/test_scenario_builder.py
git commit -m "feat(scenarios): build_default_scenarios returns 5 (add nomina scenarios)"
```

---

### Task 7: Update smoke test and verify end-to-end

**Files:**
- Modify: `rga-copilot/scripts/smoke_test_synth.py`

- [ ] **Step 1: Update `smoke_test_synth.py`**

Replace the scenarios block and add a break-even call. The full updated file:

```python
"""
Smoke test: full pipeline with real data.
Run from rga-copilot/: .venv/bin/python scripts/smoke_test_synth.py

Requires:
  - .env with ANTHROPIC_API_KEY
  - ../TEC SG - GN (Interno).xlsx  (sheets: BD 2026, GASTOS 2026, NÓMINA 2026, ER NIVEL 2026)
"""

import io
import logging
import sys
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
sys.path.insert(0, os.path.dirname(__file__) + "/..")

from orchestrator import run_analysis
from agents.synth.scenario_builder import solve_break_even_ticket

XLSX   = "../TEC SG - GN (Interno).xlsx"
YEAR   = 2026
QUAL   = ["agents/qual/Grupo_NAMA_Overview_RGA.md"]
PERIOD = "ENERO 2026"

print(f"Running full pipeline for {PERIOD}...")
result = run_analysis(
    xlsx_path=XLSX,
    year=YEAR,
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
print(f"\nScenarios ({len(result.synth.scenarios)}):")
for sc in result.synth.scenarios:
    sign = "+" if sc.impact_on_ebitda >= 0 else ""
    print(f"  {sc.name}: impact ${sign}{sc.impact_on_ebitda:,.0f}")

assert len(result.synth.scenarios) == 5, f"Expected 5 scenarios, got {len(result.synth.scenarios)}"

# Break-even solve: sucursal D, target EBITDA = 200_000
bev = solve_break_even_ticket(result.quant, sucursal="D", target_ebitda=200_000.0)
print(f"\nBreak-even D (target EBITDA $200k):")
print(f"  current ticket:  ${bev.current_ticket:,.2f}")
print(f"  required ticket: ${bev.required_ticket:,.2f}")
print(f"  delta:           +{bev.ticket_delta_pct:.1%}")
assert bev.required_ticket > bev.current_ticket, "Required ticket should exceed current for positive target"

print(f"\nMemo PDF: {result.synth.memo_pdf_path}")
assert os.path.exists(result.synth.memo_pdf_path), "PDF file was not created!"
print("\nSMOKE TEST PASSED")
```

- [ ] **Step 2: Run smoke test**

```bash
cd rga-copilot && .venv/bin/python scripts/smoke_test_synth.py 2>&1 | grep -E "EBITDA|Scenarios|impact|Break-even|PASSED|FAILED|Error|Traceback"
```

Expected output includes:
```
EBITDA total: $2,235,605
Scenarios (5):
  Costo insumo Alimentos +15%: impact $-310,080
  ...
  Reducción nómina ... -10%: impact $+...
  Incremento salarial +10% ...: impact $-...
Break-even D (target EBITDA $200k):
  current ticket:  $...
  required ticket: $...
  delta:           +...%
SMOKE TEST PASSED
```

- [ ] **Step 3: Commit**

```bash
git add rga-copilot/scripts/smoke_test_synth.py
git commit -m "test(smoke): assert 5 scenarios + break-even ticket solve"
```
