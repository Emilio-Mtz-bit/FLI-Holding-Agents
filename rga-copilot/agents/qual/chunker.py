from agents.qual.models import Chunk

CHUNK_SIZE = 2000   # ~500 tokens
OVERLAP = 200       # ~50 tokens


def chunk(text: str, source_path: str) -> list[Chunk]:
    if len(text) <= CHUNK_SIZE:
        return [Chunk(text=text, source_path=source_path, chunk_index=0)]

    chunks = []
    start = 0
    index = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunks.append(Chunk(
            text=text[start:end],
            source_path=source_path,
            chunk_index=index,
        ))
        start += CHUNK_SIZE - OVERLAP
        index += 1
    return chunks
