"""
MemoGenerator — renders the Jinja2 HTML template and saves to an HTML file.

No LLM calls. Receives pre-computed data from SynthAgent.
"""

from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path

import markdown as _md

from jinja2 import Environment, FileSystemLoader

from agents.synth.models import BreakEvenResult, Recommendation, Scenario, Signal

_TEMPLATES_DIR = Path(__file__).parent / "templates"


class MemoGenerator:
    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=False,
        )
        self._env.filters['md'] = lambda text: _md.markdown(text or '', extensions=['nl2br'])

    def render_html(
        self,
        *,
        company: str,
        period: str,
        quant_narrative: str,
        qual_summary: str,
        signals: list[Signal],
        scenarios: list[Scenario],
        break_even_results: list[BreakEvenResult],
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
            break_even_results=[r.model_dump() for r in break_even_results],
            recommendations=[r.model_dump() for r in recommendations],
            next_steps=next_steps,
        )

    def write_html(self, html: str, *, out_dir: str, period: str) -> str:
        """Write html to disk and return absolute file path."""
        os.makedirs(out_dir, exist_ok=True)
        safe_period = re.sub(r"\s+", "_", period.upper())
        filename = f"memo_{safe_period}.html"
        out_path = os.path.join(out_dir, filename)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        return out_path
