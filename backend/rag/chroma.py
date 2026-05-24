"""ChromaDB singleton — persistent local vector store."""
from __future__ import annotations
import chromadb
from chromadb.config import Settings
from backend.config import PROJECT_ROOT

_client = None
_collection = None
COLLECTION_NAME = "kn"
CHROMA_DIR = PROJECT_ROOT / "chroma_db"

def get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection
