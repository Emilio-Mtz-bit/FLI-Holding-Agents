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
