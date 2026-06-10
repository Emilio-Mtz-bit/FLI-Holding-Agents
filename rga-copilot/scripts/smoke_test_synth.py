"""
Smoke test: full pipeline with real data.
Run from rga-copilot/: .venv/bin/python scripts/smoke_test_synth.py

Requires:
  - .env with ANTHROPIC_API_KEY
  - ../TEC SG - GN (Interno).xlsx  (sheets: BD 2026, GASTOS 2026, NÓMINA 2026, ER NIVEL 2026)
"""

import io
import logging
import sys
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
sys.path.insert(0, os.path.dirname(__file__) + "/..")

from orchestrator import run_analysis
from agents.synth.scenario_builder import solve_break_even_ticket

XLSX   = "../TEC SG - GN (Interno).xlsx"
YEAR   = 2026
QUAL   = ["agents/qual/Grupo_NAMA_Overview_RGA.md"]
PERIOD = "ENERO 2026"

print(f"Running full pipeline for {PERIOD}...")
result = run_analysis(
    xlsx_path=XLSX,
    year=YEAR,
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
print(f"\nScenarios ({len(result.synth.scenarios)}):")
for sc in result.synth.scenarios:
    sign = "+" if sc.impact_on_ebitda >= 0 else ""
    print(f"  {sc.name}: impact ${sign}{sc.impact_on_ebitda:,.0f}")

assert len(result.synth.scenarios) == 5, f"Expected 5 scenarios, got {len(result.synth.scenarios)}"

# Break-even solve: sucursal D, target EBITDA = 200_000
bev = solve_break_even_ticket(result.quant, sucursal="D", target_ebitda=200_000.0)
print(f"\nBreak-even D (target EBITDA $200k):")
print(f"  current ticket:  ${bev.current_ticket:,.2f}")
print(f"  required ticket: ${bev.required_ticket:,.2f}")
print(f"  delta:           +{bev.ticket_delta_pct:.1%}")
assert bev.required_ticket > bev.current_ticket, "Required ticket should exceed current for positive target"

print(f"\nMemo PDF: {result.synth.memo_pdf_path}")
assert os.path.exists(result.synth.memo_pdf_path), "PDF file was not created!"
print("\nSMOKE TEST PASSED")
