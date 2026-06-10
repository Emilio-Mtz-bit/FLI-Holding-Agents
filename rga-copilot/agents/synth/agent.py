"""
SynthAgent — synthesizes QuantOutput + QualOutput into SynthOutput.

One Claude call extracts top-3 signals + next_steps.
Deterministic scenario builder runs without LLM.
MemoGenerator renders HTML + PDF.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

from agents.quant.agent import QuantOutput
from agents.qual.models import QualOutput
from agents.synth.memo_generator import MemoGenerator
from agents.synth.models import Recommendation, Signal, SynthOutput
from agents.synth.scenario_builder import build_default_scenarios

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent / "prompts" / "signal_synthesis.txt"


class SynthAgent:
    def __init__(
        self,
        company: str = "Grupo Nama",
        model: str = "claude-sonnet-4-6",
        claude_client=None,
        memo_out_dir: str = "data/outputs",
    ) -> None:
        self._company = company
        self._model = model
        self._client = claude_client or anthropic.Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"]
        )
        self._memo_gen = MemoGenerator()
        self._memo_out_dir = memo_out_dir

    # ------------------------------------------------------------------

    def run(self, quant: QuantOutput, qual: QualOutput) -> SynthOutput:
        signals, next_steps = self._extract_signals(quant, qual)
        scenarios = build_default_scenarios(quant)
        recommendations = self._derive_recommendations(signals)
        html = self._memo_gen.render_html(
            company=self._company,
            period=quant.period,
            quant_narrative=quant.narrative,
            qual_summary=qual.summary,
            signals=signals,
            scenarios=scenarios,
            recommendations=recommendations,
            next_steps=next_steps,
        )
        html_path = self._memo_gen.write_html(
            html, out_dir=self._memo_out_dir, period=quant.period
        )
        return SynthOutput(
            signals=signals,
            scenarios=scenarios,
            recommendations=recommendations,
            next_steps=next_steps,
            memo_html=html,
            memo_pdf_path=html_path,
        )

    # ------------------------------------------------------------------

    def _extract_signals(
        self, quant: QuantOutput, qual: QualOutput
    ) -> tuple[list[Signal], str]:
        try:
            prompt_template = _PROMPT_PATH.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Signal synthesis prompt not found at {_PROMPT_PATH}. "
                "Ensure agents/synth/prompts/signal_synthesis.txt exists."
            ) from None
        prompt = prompt_template.format(
            company=self._company,
            period=quant.period,
            quant_json=json.dumps(
                {"kpis": quant.kpis, "alerts": [a.model_dump() for a in quant.alerts],
                 "narrative": quant.narrative},
                ensure_ascii=False, indent=2,
            ),
            qual_json=json.dumps(
                {"signals": qual.signals, "sentiment": qual.sentiment,
                 "hypotheses": qual.hypotheses, "summary": qual.summary},
                ensure_ascii=False, indent=2,
            ),
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=1500,
            system=[{
                "type": "text",
                "text": "Responde únicamente con JSON válido. Sin markdown. Sin texto adicional.",
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()

        # Strip accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0].strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("Claude returned malformed JSON in signal extraction: %r", raw[:200])
            parsed = {"signals": [], "next_steps": ""}

        try:
            signals = [Signal(**s) for s in parsed.get("signals", [])]
        except Exception as exc:
            logger.error("Signal validation failed — Claude output did not match schema: %s", exc)
            signals = []
        next_steps = parsed.get("next_steps", "")
        return signals, next_steps

    # ------------------------------------------------------------------

    @staticmethod
    def _derive_recommendations(signals: list[Signal]) -> list[Recommendation]:
        return [
            Recommendation(
                accion=s.recomendacion,
                impacto=s.impacto,
                facilidad=s.facilidad,
                fuente=f"signal_{s.rank}",
            )
            for s in signals
        ]
