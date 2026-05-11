from agents.qual.models import QualDoc, Alert, QualOutput
from agents.qual.embedder import ChromaStore
from agents.qual import doc_processor, cleaner, chunker
from agents.qual.signal_extractor import SignalExtractor
from agents.qual.summarizer import Summarizer


class QualAgent:
    def __init__(self, schema_path: str, chroma_store: ChromaStore, claude_client):
        self.chroma_store = chroma_store
        self.signal_extractor = SignalExtractor(schema_path, claude_client)
        self.summarizer = Summarizer(claude_client)

    def run(self, docs: list[QualDoc], quant_alerts: list[Alert]) -> QualOutput:
        all_chunks = []
        for doc in docs:
            processed = doc_processor.process(doc)
            if not processed.raw_text:
                continue
            cleaned = cleaner.clean(processed.raw_text)
            chunks = chunker.chunk(cleaned, source_path=doc.path)
            all_chunks.extend(chunks)

        chunks_stored = self.chroma_store.store(all_chunks) if all_chunks else 0
        signals = self.signal_extractor.extract(all_chunks) if all_chunks else {}
        summary = self.summarizer.generate(signals, all_chunks) if all_chunks else ""

        return QualOutput(
            signals=signals,
            sentiment=float(signals.get("sentiment_score", 0.0)),
            hypotheses=[],
            summary=summary,
            chunks_stored=chunks_stored,
        )
