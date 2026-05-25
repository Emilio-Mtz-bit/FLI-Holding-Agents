"""
MemoGenerator — renders the Jinja2 HTML template and exports to PDF via WeasyPrint.

No LLM calls. Receives pre-computed data from SynthAgent.
"""

from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from agents.synth.models import Recommendation, Scenario, Signal

# Imported at module level so tests can monkeypatch it.
# WeasyPrint requires system cairo/gobject libs; on macOS set
# DYLD_LIBRARY_PATH=/opt/homebrew/lib before importing.
try:
    from weasyprint import HTML
except OSError:
    HTML = None  # type: ignore[assignment,misc]

_TEMPLATES_DIR = Path(__file__).parent / "templates"


class MemoGenerator:
    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=False,
        )

    def render_html(
        self,
        *,
        company: str,
        period: str,
        quant_narrative: str,
        qual_summary: str,
        signals: list[Signal],
        scenarios: list[Scenario],
        recommendations: list[Recommendation],
        next_steps: str,
        generated_date: str | None = None,
    ) -> str:
        tmpl = self._env.get_template("memo.html.j2")
        return tmpl.render(
            company=company,
            period=period,
            generated_date=generated_date or date.today().isoformat(),
            quant_narrative=quant_narrative,
            qual_summary=qual_summary,
            signals=[s.model_dump() for s in signals],
            scenarios=[s.model_dump() for s in scenarios],
            recommendations=[r.model_dump() for r in recommendations],
            next_steps=next_steps,
        )

    def write_pdf(self, html: str, *, out_dir: str, period: str) -> str:
        """Render html → PDF and return absolute file path."""
        if HTML is None:
            raise RuntimeError(
                "WeasyPrint is unavailable (missing system cairo/gobject libs). "
                "PDF generation is disabled. Set DYLD_LIBRARY_PATH=/opt/homebrew/lib on macOS."
            )
        os.makedirs(out_dir, exist_ok=True)
        safe_period = re.sub(r"\s+", "_", period.upper())
        filename = f"memo_{safe_period}.pdf"
        out_path = os.path.join(out_dir, filename)
        HTML(string=html).write_pdf(out_path)
        return out_path
