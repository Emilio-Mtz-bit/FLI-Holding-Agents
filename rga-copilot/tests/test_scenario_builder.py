"""Unit tests for scenario_builder — no Claude calls, pure maths."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.synth.models import Scenario, BreakEvenResult
from agents.synth.scenario_builder import (
    build_scenario_costo_insumo,
    build_scenario_cierre_sucursal,
    build_scenario_shift_mix,
    build_scenario_reduccion_nomina,
    build_scenario_incremento_salarial,
    build_default_scenarios,
    solve_break_even_ticket,
)

# ---------------------------------------------------------------------------
# Minimal QuantOutput fixture (duck-typed with .kpis dict)
# ---------------------------------------------------------------------------

QUANT_KPIS = {
    "consolidado": {
        "ebitda_total": 2_000_000.0,
        "ingresos_total": 10_000_000.0,
        "nomina_total": 1_200_000.0,
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
    # MOR has highest nomina/ingresos = 0.40
    assert reduccion.affected_target == "MOR"


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


def test_incremento_salarial_impact():
    # consolidado nomina_total = 1_200_000; 10% increase → -120_000 impact
    sc = build_scenario_incremento_salarial(Q, delta_pct=0.10)
    assert sc.variable == "incremento_salarial"
    assert sc.affected_target == "todas las sucursales"
    assert sc.impact_on_ebitda == pytest.approx(-120_000.0)
    assert sc.ebitda_post == pytest.approx(1_880_000.0)
    assert sc.base_ebitda == pytest.approx(2_000_000.0)


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


def test_break_even_ticket_above_current():
    # MOR: gastos=80_000, nomina=200_000, margen=0.56, transacciones=2_000, ticket=250
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
