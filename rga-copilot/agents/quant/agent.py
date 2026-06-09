"""
QuantAgent — numerical analysis for a single period.

Usage:
    from agents.quant.agent import QuantAgent
    from agents.quant.kpi_calculator import LocalDB

    db = LocalDB(bd=bd_df, gastos=gastos_df, nomina=nomina_df)
    result = QuantAgent(company="Grupo Nama").run(period="ENERO 2026", db=db)

Output: QuantOutput (Pydantic model)
"""

from __future__ import annotations

import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()  # loads rga-copilot/.env (or any parent .env)
from pydantic import BaseModel

from .alert_detector import Alert, detect_alerts
from .kpi_calculator import LocalDB, PeriodKPIs, build_period_kpis


# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------

class QuantOutput(BaseModel):
    period: str
    kpis: dict
    alerts: list[Alert]
    narrative: str
    top_products: list[dict]


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_SYSTEM_TMPL = """\
Eres un analista financiero senior especializado en análisis de estados \
financieros para empresas del sector restaurantero.
Estás analizando los resultados de {company}.
Redacta UN PÁRRAFO ejecutivo en español (máx. 120 palabras) que sintetice \
los KPIs del período. Cita cifras exactas del JSON. No inventes datos.
No uses bullets. Termina señalando el riesgo más urgente si hay alertas."""

_USER_TMPL = """\
Empresa: {company}
Período: {period}

KPIs consolidados:
{consolidado}

Alertas activas ({n_alerts}):
{alerts}

Redacta el párrafo ejecutivo."""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class QuantAgent:
    def __init__(
        self,
        company: str = "Grupo Nama",
        model: str = "claude-sonnet-4-6",
    ) -> None:
        self._client  = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self._model   = model
        self._company = company

    def run(self, period: str, db: LocalDB) -> QuantOutput:
        period_kpis = build_period_kpis(db, period)
        alerts      = detect_alerts(period_kpis)
        narrative   = self._narrative(period_kpis, alerts)

        return QuantOutput(
            period=period,
            kpis=_serialize_kpis(period_kpis),
            alerts=alerts,
            narrative=narrative,
            top_products=[vars(p) for p in period_kpis.top_productos],
        )

    def _narrative(self, kpis: PeriodKPIs, alerts: list[Alert]) -> str:
        system = _SYSTEM_TMPL.format(company=self._company)
        user   = _USER_TMPL.format(
            company=self._company,
            period=kpis.period,
            consolidado=json.dumps(kpis.consolidado, ensure_ascii=False, indent=2),
            n_alerts=len(alerts),
            alerts=json.dumps([a.model_dump() for a in alerts], ensure_ascii=False, indent=2),
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=300,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text.strip()


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def _serialize_kpis(kpis: PeriodKPIs) -> dict:
    return {
        "period": kpis.period,
        "consolidado": kpis.consolidado,
        "por_sucursal": [vars(b) for b in kpis.por_sucursal],
        "pct_mix_categoria": kpis.pct_mix_categoria,
        "por_categoria": [vars(c) for c in kpis.por_categoria],
    }
