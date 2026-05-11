from unittest.mock import MagicMock
from agents.qual.models import Chunk
from agents.qual.summarizer import Summarizer


def _make_mock_client(responses: list[str]):
    """Returns a mock client that yields responses in order."""
    call_count = {"n": 0}
    def create(**kwargs):
        mock_content = MagicMock()
        mock_content.text = responses[call_count["n"]]
        mock_message = MagicMock()
        mock_message.content = [mock_content]
        call_count["n"] += 1
        return mock_message
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = create
    return mock_client


def test_generate_returns_paragraph_and_quote():
    client = _make_mock_client([
        "Grupo NAMA es un operador restaurantero sólido con fuerte presencia en Querétaro.",
        "compartir lo mejor del mar a través de técnicas japonesas",
    ])
    summarizer = Summarizer(claude_client=client)
    signals = {"fortalezas": ["calidad"], "sentiment_score": 0.7}
    chunks = [Chunk(text="texto de ejemplo", source_path="doc.md", chunk_index=0)]
    result = summarizer.generate(signals, chunks)
    assert "Grupo NAMA" in result
    assert ">" in result   # Markdown blockquote for the key quote
    assert client.messages.create.call_count == 2


def test_generate_makes_exactly_two_claude_calls():
    client = _make_mock_client(["párrafo", "cita"])
    summarizer = Summarizer(claude_client=client)
    summarizer.generate({}, [Chunk(text="x", source_path="f.txt", chunk_index=0)])
    assert client.messages.create.call_count == 2
