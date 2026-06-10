"""Unit tests for scenario_builder — no Claude calls, pure maths."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.synth.models import Scenario, BreakEvenResult
from agents.synth.scenario_builder import (
    build_scenario_costo_insumo,
    build_scenario_cierre_sucursal,
    build_scenario_shift_mix,
    build_default_scenarios,
)

# ---------------------------------------------------------------------------
# Minimal QuantOutput fixture (duck-typed with .kpis dict)
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
