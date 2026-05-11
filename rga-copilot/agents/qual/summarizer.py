import json
from pathlib import Path
from agents.qual.models import Chunk

_PROMPTS = Path(__file__).parent / "prompts"
_SUMMARY_TEMPLATE = (_PROMPTS / "summary.txt").read_text(encoding="utf-8")
_QUOTE_TEMPLATE = (_PROMPTS / "key_quote.txt").read_text(encoding="utf-8")
MAX_RAW_CHARS = 50_000


class Summarizer:
    def __init__(self, claude_client):
        self.client = claude_client

    def _call(self, prompt: str) -> str:
        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    def generate(self, signals: dict, chunks: list[Chunk]) -> str:
        signals_prompt = _SUMMARY_TEMPLATE.format(signals_json=json.dumps(signals, ensure_ascii=False, indent=2))
        paragraph = self._call(signals_prompt)

        raw_text = "\n\n".join(c.text for c in chunks)[:MAX_RAW_CHARS]
        quote_prompt = _QUOTE_TEMPLATE.format(text=raw_text)
        key_quote = self._call(quote_prompt)

        return f"{paragraph}\n\n> {key_quote}"
