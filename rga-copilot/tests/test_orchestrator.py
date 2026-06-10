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
        signals=[fake_signal], scenarios=[fake_scenario], break_even_results=[],
        recommendations=[fake_rec],
        next_steps="Paso.", memo_html="<html></html>", memo_pdf_path="/tmp/memo.pdf",
    )

    with patch("orchestrator.load") as mock_load, \
         patch("orchestrator.clean") as mock_clean, \
         patch("orchestrator.QuantAgent") as MockQuant, \
         patch("orchestrator.QualAgent") as MockQual, \
         patch("orchestrator.SynthAgent") as MockSynth, \
         patch("orchestrator.ChromaStore") as MockChroma, \
         patch("orchestrator.SentenceTransformerEmbedder") as MockEmbed:

        mock_load.return_value = MagicMock()
        mock_clean.return_value = MagicMock()
        MockQuant.return_value.run.return_value = mock_quant_out
        MockQual.return_value.run.return_value = mock_qual_out
        MockSynth.return_value.run.return_value = mock_synth_out

        result = run_analysis(
            xlsx_path="fake.xlsx",
            year=2026,
            qual_docs=[],
            period="ENERO 2026",
        )

    assert result.period == "ENERO 2026"
    assert result.quant == mock_quant_out
    assert result.qual == mock_qual_out
    assert result.synth == mock_synth_out
    MockQual.return_value.run.assert_called_once()
