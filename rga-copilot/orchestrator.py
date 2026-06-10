"""
Orchestrator — top-level entry point for the RGA Copilot pipeline.

run_analysis(xlsx_path, year, qual_docs, period) → AnalysisResult

Pipeline:
    load(xlsx, year) → RawData
    clean(raw) → LocalDB
    QuantAgent.run(period, db) → QuantOutput
    _normalize_alerts(quant.alerts) → list[QualAlert]   ← Alert model adapter
    QualAgent.run(qual_docs, qual_alerts) → QualOutput
    SynthAgent.run(quant, qual) → SynthOutput
    → AnalysisResult

Alert model adapter:
    QuantAlert (agents.quant.alert_detector.Alert):
        level: "red"|"warning", tipo: str, sucursal: str|None,
        sku: str|None, mensaje: str, valor: float|None
    QualAlert (agents.qual.models.Alert):
        sucursal: str, message: str, severity: "red"|"yellow"
    Mapping: level=="red" → severity="red"; else → severity="yellow"
             mensaje → message; sucursal or "" → sucursal
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

from agents.qual.agent import QualAgent
from agents.qual.embedder import ChromaStore, SentenceTransformerEmbedder
from agents.qual.models import Alert as QualAlert
from agents.qual.models import QualDoc
from agents.quant.agent import QuantAgent
from agents.quant.alert_detector import Alert as QuantAlert
from agents.synth.agent import SynthAgent
from agents.synth.models import AnalysisResult
from pipeline.cleaning import clean
from pipeline.ingestion import load

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Alert model adapter
# ---------------------------------------------------------------------------

def _normalize_alerts(quant_alerts: list[QuantAlert]) -> list[QualAlert]:
    """Convert QuantAgent Alert list to QualAgent Alert list."""
    return [
        QualAlert(
            sucursal=a.sucursal or "",
            message=a.mensaje,
            severity="red" if a.level == "red" else "yellow",
        )
        for a in quant_alerts
    ]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_analysis(
    xlsx_path: str,
    year: int,
    qual_docs: list[str],
    period: str,
    company: str = "Grupo Nama",
    chroma_persist_path: str = "data/vector_store",
    memo_out_dir: str = "data/outputs",
    schema_path: str | None = None,
    break_even_target_ebitda: float = 1_500_000.0,
) -> AnalysisResult:
    """
    Full analysis pipeline.

    Args:
        xlsx_path: Path to Excel file with sheets BD {year}, GASTOS {year},
                   NÓMINA {year}, ER NIVEL {year}.
        year: The fiscal year (e.g. 2026) used to select sheet names.
        qual_docs: List of file paths (PDF, image, text) for qualitative analysis.
        period: Period string, e.g. "ENERO 2026".
        company: Client name for narratives.
        chroma_persist_path: Directory for ChromaDB vector store.
        memo_out_dir: Directory to write the PDF memo.

    Returns:
        AnalysisResult with quant, qual, and synth sub-results.
    """
    if schema_path is None:
        schema_path = str(Path(__file__).parent / "agents" / "qual" / "config" / "nama_signals.yaml")

    logger.info("Orchestrator: loading data for period=%s year=%d", period, year)
    raw = load(xlsx_path, year)
    db  = clean(raw)

    logger.info("Orchestrator: running QuantAgent")
    quant_agent = QuantAgent(company=company)
    quant = quant_agent.run(period=period, db=db)

    logger.info("Orchestrator: running QualAgent (docs=%d, alerts=%d)",
                len(qual_docs), len(quant.alerts))
    claude_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    embedder = SentenceTransformerEmbedder()
    chroma_store = ChromaStore(
        persist_path=chroma_persist_path,
        collection_name=f"rga_{company.lower().replace(' ', '_')}",
        embedder=embedder,
    )
    qual_agent = QualAgent(
        schema_path=schema_path,
        chroma_store=chroma_store,
        claude_client=claude_client,
    )
    qual_docs_typed = [QualDoc(path=p) for p in qual_docs]
    qual_alerts     = _normalize_alerts(quant.alerts)
    qual = qual_agent.run(docs=qual_docs_typed, quant_alerts=qual_alerts)

    logger.info("Orchestrator: running SynthAgent")
    synth_agent = SynthAgent(
        company=company,
        claude_client=claude_client,
        memo_out_dir=memo_out_dir,
    )
    synth = synth_agent.run(quant, qual, break_even_target_ebitda=break_even_target_ebitda)

    return AnalysisResult(period=period, quant=quant, qual=qual, synth=synth)
