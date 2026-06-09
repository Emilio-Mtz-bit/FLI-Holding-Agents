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

from pydantic import BaseModel, ConfigDict

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
    model_config = ConfigDict(arbitrary_types_allowed=True)

    period: str
    quant: Any  # Can be QuantOutput or MagicMock in tests
    qual: Any   # Can be QualOutput or MagicMock in tests
    synth: SynthOutput
