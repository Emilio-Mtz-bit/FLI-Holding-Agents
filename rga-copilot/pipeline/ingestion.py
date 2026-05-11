"""
pipeline/ingestion.py — reads raw source files, returns RawData.

Usage:
    raw = load(
        csv_path="TEC SG 2 - Grupo Nama (Interno) - BD 2026.csv",
        xlsx_path="TEC SG - GN (Interno).xlsx",
    )
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class RawData:
    bd: pd.DataFrame      # from CSV — all columns as strings
    gastos: pd.DataFrame  # from xlsx GASTOS 2026
    nomina: pd.DataFrame  # from xlsx NÓMINA 2026


def load(csv_path: str, xlsx_path: str) -> RawData:
    bd = pd.read_csv(csv_path, dtype=str)
    gastos = pd.read_excel(xlsx_path, sheet_name="GASTOS 2026")
    nomina = pd.read_excel(xlsx_path, sheet_name="NÓMINA 2026")
    return RawData(bd=bd, gastos=gastos, nomina=nomina)
