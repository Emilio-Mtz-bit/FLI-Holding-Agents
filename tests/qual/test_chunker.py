from agents.qual.chunker import chunk


SHORT_TEXT = "hola mundo"
LONG_TEXT = "palabra " * 600  # ~4800 chars, should produce multiple chunks


def test_short_text_produces_one_chunk():
    chunks = chunk(SHORT_TEXT, source_path="doc.txt")
    assert len(chunks) == 1
    assert chunks[0].text == SHORT_TEXT
    assert chunks[0].source_path == "doc.txt"
    assert chunks[0].chunk_index == 0


def test_long_text_produces_multiple_chunks():
    chunks = chunk(LONG_TEXT, source_path="doc.txt")
    assert len(chunks) > 1


def test_chunks_have_sequential_indices():
    chunks = chunk(LONG_TEXT, source_path="doc.txt")
    for i, c in enumerate(chunks):
        assert c.chunk_index == i


def test_chunks_have_correct_source_path():
    chunks = chunk(LONG_TEXT, source_path="informe.pdf")
    for c in chunks:
        assert c.source_path == "informe.pdf"


def test_overlap_means_last_chars_of_chunk_appear_in_next():
    chunks = chunk(LONG_TEXT, source_path="doc.txt")
    if len(chunks) > 1:
        end_of_first = chunks[0].text[-100:]
        start_of_second = chunks[1].text[:300]
        assert end_of_first.strip() in start_of_second
