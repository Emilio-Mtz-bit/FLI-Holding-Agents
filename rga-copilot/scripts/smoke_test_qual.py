import sys
import os
import json
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from anthropic import Anthropic
from agents.qual.models import QualDoc
from agents.qual.embedder import SentenceTransformerEmbedder, ChromaStore
from agents.qual.agent import QualAgent

SCHEMA_PATH = "agents/qual/config/nama_signals.yaml"
NAMA_DOC = "agents/qual/Grupo_NAMA_Overview_RGA.md"
OUTPUT_DIR = "data/outputs"

client = Anthropic()
embedder = SentenceTransformerEmbedder()
store = ChromaStore(
    persist_path="data/vector_store",
    collection_name="nama",
    embedder=embedder,
)
agent = QualAgent(schema_path=SCHEMA_PATH, chroma_store=store, claude_client=client)

result = agent.run(docs=[QualDoc(path=NAMA_DOC)], quant_alerts=[])

# Save to JSON
os.makedirs(OUTPUT_DIR, exist_ok=True)
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
output_path = os.path.join(OUTPUT_DIR, f"qual_output_{timestamp}.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)

print(f"\n=== QualOutput ===")
print(f"Sentiment: {result.sentiment}")
print(f"Chunks stored: {result.chunks_stored}")
print(f"\nSignals:")
for k, v in result.signals.items():
    print(f"  {k}: {v}")
print(f"\nSummary:\n{result.summary}")
print(f"\nSaved to: {output_path}")
