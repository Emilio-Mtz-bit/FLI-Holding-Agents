import json
import pytest
from unittest.mock import MagicMock
from pathlib import Path
from agents.qual.models import Chunk
from agents.qual.signal_extractor import SignalExtractor

SCHEMA_PATH = str(Path(__file__).parent.parent.parent / "rga-copilot/agents/qual/config/nama_signals.yaml")

MOCK_RESPONSE = json.dumps({
    "tipo_empresa": "Restaurantero japonés",
    "posicionamiento": "Gama media-alta",
    "fortalezas": ["Calidad del producto del mar"],
    "riesgos": ["Insumos importados"],
    "factores_crecimiento": ["Expansión a Morelia"],
    "temas_topicos": ["sushi", "teppanyaki"],
    "sentiment_score": 0.7,
})


def _make_mock_client(response_text: str):
    mock_content = MagicMock()
    mock_content.text = response_text
    mock_message = MagicMock()
    mock_message.content = [mock_content]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message
    return mock_client


def test_extract_returns_dict_with_all_schema_keys():
    client = _make_mock_client(MOCK_RESPONSE)
    extractor = SignalExtractor(schema_path=SCHEMA_PATH, claude_client=client)
    chunks = [Chunk(text="texto de prueba", source_path="doc.md", chunk_index=0)]
    result = extractor.extract(chunks)
    assert isinstance(result, dict)
    for key in ["tipo_empresa", "posicionamiento", "fortalezas", "riesgos",
                 "factores_crecimiento", "temas_topicos", "sentiment_score"]:
        assert key in result


def test_extract_truncates_text_at_50000_chars():
    client = _make_mock_client(MOCK_RESPONSE)
    extractor = SignalExtractor(schema_path=SCHEMA_PATH, claude_client=client)
    big_text = "palabra " * 10000  # ~80000 chars
    chunks = [Chunk(text=big_text, source_path="big.txt", chunk_index=0)]
    extractor.extract(chunks)
    call_args = client.messages.create.call_args
    prompt_sent = call_args[1]["messages"][0]["content"]
    assert len(prompt_sent) < 55000  # prompt + template overhead


def test_extract_returns_empty_dict_on_malformed_json():
    client = _make_mock_client("Este no es JSON válido")
    extractor = SignalExtractor(schema_path=SCHEMA_PATH, claude_client=client)
    chunks = [Chunk(text="texto", source_path="doc.txt", chunk_index=0)]
    result = extractor.extract(chunks)
    assert result == {}
