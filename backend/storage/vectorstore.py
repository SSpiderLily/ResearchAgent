import chromadb
from chromadb.config import Settings

from config import CHROMA_DIR

_client: chromadb.ClientAPI | None = None
_COLLECTION_NAME = "paper_chunks"


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def get_collection() -> chromadb.Collection:
    return _get_client().get_or_create_collection(
        name=_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def add_chunks(
    ids: list[str],
    documents: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict],
) -> None:
    collection = get_collection()
    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )


def query_chunks(
    query_embedding: list[float],
    top_k: int = 5,
) -> dict:
    collection = get_collection()
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )


def delete_by_paper_id(paper_id: str) -> None:
    collection = get_collection()
    collection.delete(where={"paper_id": paper_id})
