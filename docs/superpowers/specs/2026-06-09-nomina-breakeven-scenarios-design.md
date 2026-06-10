# Design: Nómina & Break-Even Scenarios

**Date:** 2026-06-09
**Scope:** Add two nómina what-if scenarios and a break-even ticket solver to the RGA Copilot pipeline.

---

## Context

`scenario_builder.py` currently produces 3 deterministic what-if scenarios (costo insumo, cierre sucursal, shift mix). This design adds 3 more functions to the same file and one new Pydantic model to `models.py`.

---

## Data Model

### New: `BreakEvenResult` in `agents/synth/models.py`

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

`Scenario` is unchanged. Break-even is a solver result with a different shape — it answers "what must change?" rather than "what happens if X changes?".

---

## New Functions in `agents/synth/scenario_builder.py`

### 1. `build_scenario_reduccion_nomina(quant, sucursal, delta_pct=0.10) -> Scenario`

Simulates reducing payroll at a single branch by `delta_pct`.

- `impact = +nomina_sucursal * delta_pct` (positive — cost saving)
- `variable = "reduccion_nomina"`
- `affected_target = sucursal`

### 2. `build_scenario_incremento_salarial(quant, delta_pct=0.10) -> Scenario`

Simulates a mandatory salary increase applied to all branches (e.g. new minimum wage).

- Sums all branch nominas plus corporate nomina from `kpis["consolidado"]["nomina_total"]`
- `impact = -nomina_total * delta_pct` (negative — cost increase)
- `variable = "incremento_salarial"`
- `affected_target = "todas las sucursales"`

### 3. `solve_break_even_ticket(quant, sucursal, target_ebitda=0.0) -> BreakEvenResult`

Solves for the average ticket a branch needs to reach `target_ebitda`, holding transaction count and gross margin % constant.

**Math:**
```
ebitda = (ticket × transacciones × margen_bruto_pct) − gastos − nomina

ticket_required = (target_ebitda + gastos + nomina) / (transacciones × margen_bruto_pct)
```

**Assumptions:**
- Gross margin % stays constant as ticket grows (COGS scales proportionally with revenue)
- Transaction count is fixed
- Gastos operativos and nómina are fixed

**Returns `BreakEvenResult`** — not a `Scenario`, since it's a solve not a shock.

**Edge cases:**
- `transacciones == 0` or `margen_bruto_pct == 0` → raise `ValueError`

---

## `build_default_scenarios` Update

Default set grows from 3 → 5 scenarios:

| # | Scenario | Auto-selection logic |
|---|----------|----------------------|
| 1 | Costo insumo +15% | highest-cost category (unchanged) |
| 2 | Cierre sucursal | worst EBITDA branch (unchanged) |
| 3 | Shift mix 5% | lowest → highest margin category (unchanged) |
| 4 | Reducción nómina 10% | branch with highest `nomina / ingresos` ratio |
| 5 | Incremento salarial 10% | always all branches |

`solve_break_even_ticket` is **not** in `build_default_scenarios` — it requires `target_ebitda` and `sucursal` from the user (UI inputs), so it is call-only.

---

## Files Changed

| File | Change |
|------|--------|
| `agents/synth/models.py` | Add `BreakEvenResult` model |
| `agents/synth/scenario_builder.py` | Add 3 functions, update `build_default_scenarios` |
| `agents/synth/agent.py` | No change (scenarios list grows automatically) |
| `scripts/smoke_test_synth.py` | Add assertion for 5 scenarios; add one `solve_break_even_ticket` call |

---

## Testing

- Smoke test: assert `len(result.synth.scenarios) == 5`
- Smoke test: call `solve_break_even_ticket(quant, "D", target_ebitda=200_000)` and assert `required_ticket > current_ticket`
- Unit test (optional): mock branch with known nomina/ticket/margin, verify math exactly
