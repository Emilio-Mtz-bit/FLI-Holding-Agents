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
