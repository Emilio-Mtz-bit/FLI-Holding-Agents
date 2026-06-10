"""
pipeline/cleaning.py — transforms RawData → LocalDB.

All column names produced here must match exactly what kpi_calculator.py queries.
"""

from __future__ import annotations

import sys
import os

import pandas as pd

# Allow imports from rga-copilot root when run directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.quant.kpi_calculator import LocalDB
from pipeline.ingestion import RawData


# Sucursal code mapping: xlsx uses single letters, CSV uses 3-letter codes
_XL_TO_CSV = {"A": "ANT", "B": "SOK", "C": "JUR", "D": "MOR", "E": "CAM"}

# Numeric columns in the BD CSV (stored as "$X,XXX.XX" strings)
_BD_NUM_COLS = [
    "CANTIDAD",
    "SUBTOTAL",
    "TOTAL",
    "COSTO TOTAL SIN IVA",
    "COSTO TOTAL DEL SERVICIO",
    "UTILIDAD BRUTA",
    "MARGEN BRUTO",
]


def clean(raw: RawData) -> LocalDB:
    return LocalDB(
        bd=_clean_bd(raw.bd),
        gastos=_clean_gastos(raw.gastos),
        nomina=_clean_nomina(raw.nomina),
        er_nivel=raw.er_nivel.copy(),
    )


# ---------------------------------------------------------------------------
# Internal transforms
# ---------------------------------------------------------------------------

def _parse_currency(series: pd.Series) -> pd.Series:
    """'$1,234.56' → 1234.56  (works on any string series)."""
    return pd.to_numeric(
        series.astype(str).str.replace(r"[$,]", "", regex=True).str.strip(),
        errors="coerce",
    )


def _clean_bd(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 1. Parse numeric columns
    for col in _BD_NUM_COLS:
        if col in df.columns:
            df[col] = _parse_currency(df[col])

    # 2. Rename source columns to contract names
    df = df.rename(columns={"LÍNEA DE NEGOCIO": "SUCURSAL"})

    # 3. Normalize MES: strip whitespace, uppercase
    df["MES"] = df["MES"].str.strip().str.upper()

    return df


def _clean_gastos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 1. Keep only rows with a valid expense date and category
    df = df[df["FECHA GASTO"].notna()].copy()
    df = df[df["CATEGORÍA GASTO"].notna()].copy()

    # 2. Drop always-empty TOTAL column if present
    df = df.drop(columns=["TOTAL"], errors="ignore")

    # 3. Derive MES GASTO from FECHA GASTO when column is absent
    if "MES GASTO" not in df.columns:
        df["MES GASTO"] = (
            df["FECHA GASTO"]
            .apply(lambda d: _fecha_to_mes_label(d))
        )
    else:
        df["MES GASTO"] = df["MES GASTO"].astype(str).str.strip().str.upper()

    return df


def _clean_nomina(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 1. Keep only rows with a valid payroll date
    df = df[df["FECHA NÓMINA"].notna()].copy()

    # 2. Rename unnamed concept column
    df = df.rename(columns={"Unnamed: 3": "CONCEPTO_NÓMINA"})

    # 3. Drop unused columns
    df = df.drop(columns=["Unnamed: 4", "CONCEPTO", "TOTAL"], errors="ignore")

    # 4. Derive MES NÓMINA from FECHA NÓMINA when column is absent
    if "MES NÓMINA" not in df.columns:
        df["MES NÓMINA"] = (
            df["FECHA NÓMINA"]
            .apply(lambda d: _fecha_to_mes_label(d))
        )
    else:
        df["MES NÓMINA"] = df["MES NÓMINA"].astype(str).str.strip().str.upper()

    return df


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MES_ES = {
    1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL",
    5: "MAYO", 6: "JUNIO", 7: "JULIO", 8: "AGOSTO",
    9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE",
}


def _fecha_to_mes_label(value) -> str:
    """datetime/date/str → 'ENERO 2026'"""
    try:
        ts = pd.Timestamp(value)
        return f"{_MES_ES[ts.month]} {ts.year}"
    except Exception:
        return str(value).strip().upper()
