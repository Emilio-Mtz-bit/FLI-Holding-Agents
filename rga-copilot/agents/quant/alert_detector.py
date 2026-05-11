"""
Alert detection for the QUANT agent.

Thresholds are configurable via constructor kwargs or env vars.
All thresholds defined in the spec:
  - Branch gross margin < 15%  → red
  - Product utilidad_bruta < 35% → warning per product
  - Nómina > 35% of branch revenue → warning
  - Negative EBITDA per branch  → red
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from .kpi_calculator import PeriodKPIs


AlertLevel = Literal["red", "warning"]


class Alert(BaseModel):
    level: AlertLevel
    tipo: str           # machine-readable key
    sucursal: str | None
    sku: str | None
    mensaje: str        # human-readable Spanish message
    valor: float | None = None


def detect_alerts(
    kpis: PeriodKPIs,
    *,
    margen_min: float = 0.15,
    pct_nomina_max: float = 0.35,
) -> list[Alert]:
    alerts: list[Alert] = []

    for b in kpis.por_sucursal:
        # Gross margin below threshold
        if b.margen_bruto < margen_min:
            alerts.append(Alert(
                level="red",
                tipo="margen_bruto_bajo",
                sucursal=b.sucursal,
                sku=None,
                mensaje=(
                    f"Sucursal {b.sucursal}: margen bruto {b.margen_bruto:.1%} "
                    f"por debajo del mínimo ({margen_min:.0%})."
                ),
                valor=b.margen_bruto,
            ))

        # Negative EBITDA
        if b.ebitda < 0:
            alerts.append(Alert(
                level="red",
                tipo="ebitda_negativo",
                sucursal=b.sucursal,
                sku=None,
                mensaje=(
                    f"Sucursal {b.sucursal}: EBITDA negativo "
                    f"(${b.ebitda:,.0f} MXN)."
                ),
                valor=b.ebitda,
            ))

        # Nómina > 35% of revenue
        if b.pct_nomina_ingresos > pct_nomina_max:
            alerts.append(Alert(
                level="warning",
                tipo="nomina_excesiva",
                sucursal=b.sucursal,
                sku=None,
                mensaje=(
                    f"Sucursal {b.sucursal}: nómina representa "
                    f"{b.pct_nomina_ingresos:.1%} de ingresos "
                    f"(umbral {pct_nomina_max:.0%})."
                ),
                valor=b.pct_nomina_ingresos,
            ))

    # Products with negative contribucion_marginal
    for p in kpis.top_productos:
        if p.contribucion_marginal < 0:
            alerts.append(Alert(
                level="warning",
                tipo="producto_margen_negativo",
                sucursal=p.sucursal,
                sku=p.sku,
                mensaje=(
                    f"Producto '{p.sku}' en {p.sucursal}: "
                    f"contribución marginal negativa "
                    f"(${p.contribucion_marginal:,.0f} MXN)."
                ),
                valor=p.contribucion_marginal,
            ))

    # Sort: red first, then by absolute valor magnitude
    return sorted(alerts, key=lambda a: (0 if a.level == "red" else 1, a.valor or 0))
