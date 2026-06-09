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
        recommendations=recs,
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
