import json
import logging
from pathlib import Path
import yaml
from agents.qual.models import Chunk

logger = logging.getLogger(__name__)
MAX_TEXT_CHARS = 50_000
PROMPT_TEMPLATE = (Path(__file__).parent / "prompts" / "signal_extraction.txt").read_text(encoding="utf-8")


class SignalExtractor:
    def __init__(self, schema_path: str, claude_client):
        with open(schema_path, encoding="utf-8") as f:
            self.schema = yaml.safe_load(f)
        self.client = claude_client

    def _build_schema_keys(self) -> str:
        return "\n".join(
            f"- \"{s['key']}\": {s['type']}" for s in self.schema["signals"]
        )

    def extract(self, chunks: list[Chunk]) -> dict:
        full_text = "\n\n".join(c.text for c in chunks)[:MAX_TEXT_CHARS]
        prompt = PROMPT_TEMPLATE.format(
            schema_keys=self._build_schema_keys(),
            text=full_text,
        )
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            # Strip markdown code fences Claude sometimes adds
            if raw.startswith("```"):
                raw = raw.split("```", 2)[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.rsplit("```", 1)[0].strip()
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Claude returned malformed JSON during signal extraction.")
            return {}
