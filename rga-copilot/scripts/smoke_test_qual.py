import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from anthropic import Anthropic
from agents.qual.models import QualDoc
from agents.qual.embedder import SentenceTransformerEmbedder, ChromaStore
from agents.qual.agent import QualAgent

SCHEMA_PATH = "agents/qual/config/nama_signals.yaml"
NAMA_DOC = "agents/qual/Grupo_NAMA_Overview_RGA.md"

client = Anthropic()
embedder = SentenceTransformerEmbedder()
store = ChromaStore(
    persist_path="data/vector_store",
    collection_name="nama",
    embedder=embedder,
)
agent = QualAgent(schema_path=SCHEMA_PATH, chroma_store=store, claude_client=client)

result = agent.run(docs=[QualDoc(path=NAMA_DOC)], quant_alerts=[])

print(f"\n=== QualOutput ===")
print(f"Sentiment: {result.sentiment}")
print(f"Chunks stored: {result.chunks_stored}")
print(f"\nSignals:")
for k, v in result.signals.items():
    print(f"  {k}: {v}")
print(f"\nSummary:\n{result.summary}")
