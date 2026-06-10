"""
pipeline/ingestion.py — reads raw source files, returns RawData.

Usage:
    raw = load(xlsx_path="TEC SG - GN (Interno).xlsx", year=2026)
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class RawData:
    bd: pd.DataFrame        # from xlsx BD {year}
    gastos: pd.DataFrame    # from xlsx GASTOS {year}
    nomina: pd.DataFrame    # from xlsx NÓMINA {year}
    er_nivel: pd.DataFrame  # from xlsx ER NIVEL {year}


def load(xlsx_path: str, year: int) -> RawData:
    bd       = pd.read_excel(xlsx_path, sheet_name=f"BD {year}")
    gastos   = pd.read_excel(xlsx_path, sheet_name=f"GASTOS {year}")
    nomina   = pd.read_excel(xlsx_path, sheet_name=f"NÓMINA {year}")
    er_nivel = pd.read_excel(xlsx_path, sheet_name=f"ER nivel 2 {year}")
    return RawData(bd=bd, gastos=gastos, nomina=nomina, er_nivel=er_nivel)
