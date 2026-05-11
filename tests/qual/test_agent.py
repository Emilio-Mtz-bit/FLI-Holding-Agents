import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from agents.qual.models import QualDoc, Alert, Chunk
from agents.qual.embedder import EmbedderBase, ChromaStore
from agents.qual.agent import QualAgent

SCHEMA_PATH = str(Path(__file__).parent.parent.parent / "rga-copilot/agents/qual/config/nama_signals.yaml")
NAMA_DOC = str(Path(__file__).parent.parent.parent / "rga-copilot/agents/qual/Grupo_NAMA_Overview_RGA.md")


class FakeEmbedder(EmbedderBase):
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 384 for _ in texts]


def _make_mock_claude(signals_json: str, summary_text: str, quote_text: str):
    call_count = {"n": 0}
    responses = [signals_json, summary_text, quote_text]
    def create(**kwargs):
        mock_content = MagicMock()
        mock_content.text = responses[min(call_count["n"], len(responses) - 1)]
        mock_msg = MagicMock()
        mock_msg.content = [mock_content]
        call_count["n"] += 1
        return mock_msg
    mock = MagicMock()
    mock.messages.create.side_effect = create
    return mock


def test_qual_agent_run_returns_qual_output():
    signals = json.dumps({
        "tipo_empresa": "Restaurantero",
        "posicionamiento": "Gama media-alta",
        "fortalezas": ["Calidad del mar"],
        "riesgos": ["Insumos importados"],
        "factores_crecimiento": ["Expansión"],
        "temas_topicos": ["sushi"],
        "sentiment_score": 0.7,
    })
    claude = _make_mock_claude(signals, "Párrafo ejecutivo.", "cita clave del documento")

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        store = ChromaStore(persist_path=tmpdir, collection_name="test", embedder=FakeEmbedder())
        agent = QualAgent(schema_path=SCHEMA_PATH, chroma_store=store, claude_client=claude)
        docs = [QualDoc(path=NAMA_DOC)]
        result = agent.run(docs=docs, quant_alerts=[])

    assert result.sentiment == 0.7
    assert result.chunks_stored > 0
    assert result.hypotheses == []
    assert "Párrafo" in result.summary
    assert ">" in result.summary


def test_qual_agent_run_with_no_docs_returns_empty_output():
    claude = _make_mock_claude("{}", "", "")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        store = ChromaStore(persist_path=tmpdir, collection_name="test2", embedder=FakeEmbedder())
        agent = QualAgent(schema_path=SCHEMA_PATH, chroma_store=store, claude_client=claude)
        result = agent.run(docs=[], quant_alerts=[])

    assert result.chunks_stored == 0
    assert result.hypotheses == []
