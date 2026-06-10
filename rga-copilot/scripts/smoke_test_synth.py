"""
Smoke test: full pipeline with real data.
Run from rga-copilot/: .venv/bin/python scripts/smoke_test_synth.py

Requires:
  - .env with ANTHROPIC_API_KEY
  - ../TEC SG - GN (Interno).xlsx
  - ../TEC SG 2 - Grupo Nama (Interno) - BD 2026.csv
"""

import io
import logging
import sys
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
sys.path.insert(0, os.path.dirname(__file__) + "/..")

from orchestrator import run_analysis

CSV  = "../TEC SG 2 - Grupo Nama (Interno) - BD 2026.csv"
XLSX = "../TEC SG - GN (Interno).xlsx"
QUAL = ["agents/qual/Grupo_NAMA_Overview_RGA.md"]
PERIOD = "ENERO 2026"

print(f"Running full pipeline for {PERIOD}...")
result = run_analysis(
    csv_path=CSV,
    xlsx_path=XLSX,
    qual_docs=QUAL,
    period=PERIOD,
)

print("\n=== AnalysisResult ===")
print(f"Period: {result.period}")
print(f"EBITDA total: ${result.quant.kpis['consolidado']['ebitda_total']:,.0f}")
print(f"Alerts: {len(result.quant.alerts)}")
print(f"Qual sentiment: {result.qual.sentiment:.2f}")
print(f"\nTop 3 signals:")
for s in result.synth.signals:
    print(f"  [{s.rank}] {s.titulo} — impacto={s.impacto}, facilidad={s.facilidad}")
print(f"\nScenarios:")
for sc in result.synth.scenarios:
    sign = "+" if sc.impact_on_ebitda >= 0 else ""
    print(f"  {sc.name}: impact ${sign}{sc.impact_on_ebitda:,.0f}")
print(f"\nMemo HTML: {result.synth.memo_pdf_path}")
assert os.path.exists(result.synth.memo_pdf_path), "HTML file was not created!"
print("\nSMOKE TEST PASSED")
