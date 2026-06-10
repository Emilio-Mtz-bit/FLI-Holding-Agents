"""
KPI calculations for the QUANT agent — pandas in-memory implementation.

All functions receive a LocalDB (three DataFrames: bd, gastos, nomina)
and a period string (e.g. 'ENERO 2026').
No LLM calls. No external DB.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

import pandas as pd


# ---------------------------------------------------------------------------
# In-memory DB container (replaces DuckDB connection)
# ---------------------------------------------------------------------------

class LocalDB(NamedTuple):
    """Holds the four cleaned DataFrames produced by pipeline/cleaning.py."""
    bd: pd.DataFrame       # transaccional — all rows
    gastos: pd.DataFrame   # gastos operativos
    nomina: pd.DataFrame   # nómina por concepto
    er_nivel: pd.DataFrame # estado de resultados por nivel


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class BranchKPI:
    sucursal: str
    ingresos: float
    costo_ventas: float
    utilidad_bruta: float
    margen_bruto: float
    gastos_operativos: float
    nomina: float
    ebitda: float
    pct_nomina_ingresos: float
    ticket_promedio: float
    transacciones: int


@dataclass
class ProductKPI:
    sku: str
    categoria: str
    sucursal: str
    ingresos: float
    contribucion_marginal: float
    margen_bruto: float
    cantidad: float


@dataclass
class CategoryKPI:
    categoria: str
    ingresos: float
    costo: float
    margen_bruto: float          # (ingresos - costo) / ingresos
    pct_total_ingresos: float    # share of period total revenue


@dataclass
class PeriodKPIs:
    period: str
    consolidado: dict
    por_sucursal: list[BranchKPI]
    top_productos: list[ProductKPI]
    pct_mix_categoria: dict[str, float]
    por_categoria: list[CategoryKPI]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _filter_period(df: pd.DataFrame, period: str, mes_col: str = "MES") -> pd.DataFrame:
    if df.empty or mes_col not in df.columns:
        return df
    col = df[mes_col].astype(str)
    return df[col.str.upper() == period.upper()]


# ---------------------------------------------------------------------------
# Core calculations
# ---------------------------------------------------------------------------

def calc_branch_kpis(db: LocalDB, period: str) -> list[BranchKPI]:
    bd = _filter_period(db.bd, period)

    agg_bd = (
        bd.groupby("SUCURSAL")
        .agg(
            ingresos=("SUBTOTAL", "sum"),
            costo_ventas=("COSTO TOTAL SIN IVA", "sum"),
            utilidad_bruta=("UTILIDAD BRUTA", "sum"),
            transacciones=("SUBTOTAL", "count"),
        )
        .reset_index()
    )

    # Gastos — periodo puede estar en FECHA GASTO o MES GASTO depending on sheet
    mes_col_gastos = "MES GASTO" if "MES GASTO" in db.gastos.columns else "MES"
    gastos_p = _filter_period(db.gastos, period, mes_col=mes_col_gastos)
    # Gastos Financieros va debajo de la línea EBITDA en el ER — no deducir aquí
    if "CATEGORÍA GASTO" in gastos_p.columns:
        gastos_p = gastos_p[gastos_p["CATEGORÍA GASTO"] != "Gastos Financieros"]
    gastos_p = gastos_p[~gastos_p["SUCURSAL"].isin(["Corporativo"])]
    agg_gastos = (
        gastos_p.groupby("SUCURSAL")["SUBTOTAL"]
        .sum()
        .reset_index()
        .rename(columns={"SUBTOTAL": "gastos"})
    )

    # Nómina
    mes_col_nom = "MES NÓMINA" if "MES NÓMINA" in db.nomina.columns else "MES"
    nomina_p = _filter_period(db.nomina, period, mes_col=mes_col_nom)
    nomina_p = nomina_p[~nomina_p["SUCURSAL"].isin(["Corporativo"])]
    agg_nomina = (
        nomina_p.groupby("SUCURSAL")["SUBTOTAL"]
        .sum()
        .reset_index()
        .rename(columns={"SUBTOTAL": "nomina"})
    )

    merged = (
        agg_bd
        .merge(agg_gastos, on="SUCURSAL", how="left")
        .merge(agg_nomina, on="SUCURSAL", how="left")
        .fillna(0)
    )

    result: list[BranchKPI] = []
    for _, r in merged.iterrows():
        ing = r["ingresos"]
        nom = r["nomina"]
        ebitda = r["utilidad_bruta"] - r["gastos"] - nom
        result.append(BranchKPI(
            sucursal=r["SUCURSAL"],
            ingresos=ing,
            costo_ventas=r["costo_ventas"],
            utilidad_bruta=r["utilidad_bruta"],
            margen_bruto=r["utilidad_bruta"] / ing if ing else 0.0,
            gastos_operativos=r["gastos"],
            nomina=nom,
            ebitda=ebitda,
            pct_nomina_ingresos=nom / ing if ing else 0.0,
            ticket_promedio=ing / r["transacciones"] if r["transacciones"] else 0.0,
            transacciones=int(r["transacciones"]),
        ))

    return sorted(result, key=lambda x: x.ingresos, reverse=True)


def calc_top_products(db: LocalDB, period: str, top_n: int = 20) -> list[ProductKPI]:
    bd = _filter_period(db.bd, period)

    agg = (
        bd.groupby(["SUBCATEGORÍA 2", "SUBCATEGORÍA 1", "SUCURSAL"])
        .agg(
            ingresos=("SUBTOTAL", "sum"),
            costo=("COSTO TOTAL SIN IVA", "sum"),
            margen_bruto=("MARGEN BRUTO", "mean"),
            cantidad=("CANTIDAD", "sum"),
        )
        .reset_index()
    )
    agg["contribucion_marginal"] = agg["ingresos"] - agg["costo"]
    agg = agg.sort_values("contribucion_marginal", ascending=False).head(top_n)

    return [
        ProductKPI(
            sku=r["SUBCATEGORÍA 2"],
            categoria=r["SUBCATEGORÍA 1"],
            sucursal=r["SUCURSAL"],
            ingresos=r["ingresos"],
            contribucion_marginal=r["contribucion_marginal"],
            margen_bruto=r["margen_bruto"],
            cantidad=r["cantidad"],
        )
        for _, r in agg.iterrows()
    ]


def calc_category_mix(db: LocalDB, period: str) -> dict[str, float]:
    bd = _filter_period(db.bd, period)
    agg = bd.groupby("SUBCATEGORÍA 1")["SUBTOTAL"].sum()
    total = agg.sum()
    return {cat: round(val / total, 4) for cat, val in agg.items()} if total else {}


def read_er_metrics(er_nivel: pd.DataFrame, period: str) -> dict:
    """Extract key P&L metrics from the ER nivel sheet for a given period.

    Returns dict with ebitda, utilidad_bruta, gastos_operacion_total, nomina,
    gastos_financieros, utilidad_neta, ingresos_total. Returns {} if period not found.
    """
    header_row = er_nivel.iloc[0]
    period_col = None
    for col, val in header_row.items():
        if isinstance(val, str) and val.strip().upper() == period.strip().upper():
            period_col = col
            break
    if period_col is None:
        return {}

    label_col = er_nivel.columns[0]

    def _get(label: str) -> float:
        mask = er_nivel[label_col].astype(str).str.strip() == label
        rows = er_nivel[mask]
        if rows.empty:
            return 0.0
        val = rows.iloc[0][period_col]
        return float(val) if pd.notna(val) else 0.0

    ingresos = _get("UTILIDAD BRUTA") + _get("Total COSTO DE LO VENDIDO")
    return {
        "ingresos_total":         ingresos,
        "utilidad_bruta_total":   _get("UTILIDAD BRUTA"),
        "nomina_total":           _get("NÓMINA"),
        "gastos_operacion_total": _get("Total GASTOS DE OPERACIÓN"),
        "ebitda_total":           _get("EBITDA"),
        "gastos_financieros":     _get("GASTOS FINANCIEROS"),
        "utilidad_neta":          _get("Utilidad (ó Pérdida)"),
    }


def calc_corporate_overhead(db: "LocalDB", period: str) -> tuple[float, float]:
    """Returns (corporate_gastos, corporate_nomina) excluding Gastos Financieros.

    Corporativo overhead is not allocated to branches but must be subtracted
    from the consolidated EBITDA to match the official Estado de Resultados.
    """
    mes_col_gastos = "MES GASTO" if "MES GASTO" in db.gastos.columns else "MES"
    gastos_p = _filter_period(db.gastos, period, mes_col=mes_col_gastos)
    if "CATEGORÍA GASTO" in gastos_p.columns:
        gastos_p = gastos_p[gastos_p["CATEGORÍA GASTO"] != "Gastos Financieros"]
    corp_gastos = gastos_p[gastos_p["SUCURSAL"] == "Corporativo"]["SUBTOTAL"].sum()

    mes_col_nom = "MES NÓMINA" if "MES NÓMINA" in db.nomina.columns else "MES"
    nomina_p = _filter_period(db.nomina, period, mes_col=mes_col_nom)
    corp_nomina = nomina_p[nomina_p["SUCURSAL"] == "Corporativo"]["SUBTOTAL"].sum()

    return float(corp_gastos), float(corp_nomina)


def calc_consolidado(branch_kpis: list[BranchKPI],
                     corporate_gastos: float = 0.0,
                     corporate_nomina: float = 0.0) -> dict:
    ingresos = sum(b.ingresos for b in branch_kpis)
    utilidad = sum(b.utilidad_bruta for b in branch_kpis)
    nomina   = sum(b.nomina for b in branch_kpis) + corporate_nomina
    gastos   = sum(b.gastos_operativos for b in branch_kpis) + corporate_gastos
    # EBITDA = branch contributions minus unallocated corporate overhead
    ebitda   = utilidad - nomina - gastos
    return {
        "ingresos_total": ingresos,
        "utilidad_bruta_total": utilidad,
        "ebitda_total": ebitda,
        "margen_bruto_global": utilidad / ingresos if ingresos else 0.0,
        "margen_ebitda_global": ebitda / ingresos if ingresos else 0.0,
        "nomina_total": nomina,
        "gastos_operativos_total": gastos,
        "pct_nomina_ingresos_global": nomina / ingresos if ingresos else 0.0,
    }


def calc_category_kpis(db: LocalDB, period: str) -> list[CategoryKPI]:
    """Full category aggregation — all rows, not just top-N products."""
    bd = _filter_period(db.bd, period)
    agg = (
        bd.groupby("SUBCATEGORÍA 1")
        .agg(
            ingresos=("SUBTOTAL", "sum"),
            costo=("COSTO TOTAL SIN IVA", "sum"),
        )
        .reset_index()
    )
    total = agg["ingresos"].sum()
    result = []
    for _, r in agg.iterrows():
        ing = float(r["ingresos"])
        costo = float(r["costo"])
        result.append(CategoryKPI(
            categoria=str(r["SUBCATEGORÍA 1"]),
            ingresos=ing,
            costo=costo,
            margen_bruto=(ing - costo) / ing if ing else 0.0,
            pct_total_ingresos=ing / total if total else 0.0,
        ))
    return sorted(result, key=lambda x: x.ingresos, reverse=True)


def build_period_kpis(db: LocalDB, period: str) -> PeriodKPIs:
    branch_kpis    = calc_branch_kpis(db, period)
    top_productos  = calc_top_products(db, period)
    mix            = calc_category_mix(db, period)
    corp_g, corp_n = calc_corporate_overhead(db, period)
    consolidado    = calc_consolidado(branch_kpis, corp_g, corp_n)
    por_categoria  = calc_category_kpis(db, period)

    # Override consolidated P&L with official ER values when available
    er = read_er_metrics(db.er_nivel, period)
    if er:
        ing = er["ingresos_total"]
        ebitda = er["ebitda_total"]
        utilidad = er["utilidad_bruta_total"]
        nomina = er["nomina_total"]
        gastos = er["gastos_operacion_total"] - nomina
        consolidado.update({
            "ingresos_total":              ing,
            "utilidad_bruta_total":        utilidad,
            "ebitda_total":                ebitda,
            "margen_bruto_global":         utilidad / ing if ing else 0.0,
            "margen_ebitda_global":        ebitda / ing if ing else 0.0,
            "nomina_total":                nomina,
            "gastos_operativos_total":     gastos,
            "pct_nomina_ingresos_global":  nomina / ing if ing else 0.0,
            "gastos_financieros":          er["gastos_financieros"],
            "utilidad_neta":               er["utilidad_neta"],
        })
    return PeriodKPIs(
        period=period,
        consolidado=consolidado,
        por_sucursal=branch_kpis,
        top_productos=top_productos,
        pct_mix_categoria=mix,
        por_categoria=por_categoria,
    )
