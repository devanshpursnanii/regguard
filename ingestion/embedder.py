from __future__ import annotations

from typing import Dict, Iterable, List, Tuple
import uuid
from google import genai
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from config import GEMINI_API_KEY, GEMINI_EMBEDDING_MODEL, QDRANT_MODE
from utils.llm_guard import cached_batch_call


class EmbeddingStore:
    """Embedding client that stores vectors in Qdrant."""

    def __init__(self, collection_name: str = "regguard") -> None:
        if QDRANT_MODE != "in_memory":
            raise ValueError("Only in-memory Qdrant mode is supported in Component 1")
        self.client = QdrantClient(":memory:")
        self.collection_name = collection_name
        self._collection_ready = False

    def _ensure_collection(self, vector_size: int) -> None:
        if self._collection_ready:
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        self._collection_ready = True

    def _to_uuid(self, value: str) -> str:
        """Create a deterministic UUID for a given string."""

        return str(uuid.uuid5(uuid.NAMESPACE_URL, value))

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts using Gemini embeddings."""

        client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options={"api_version": "v1beta"},
        )
        embeddings: List[List[float]] = []
        batch_size = 20

        def _embed_batch(batch: List[str]) -> List[List[float]]:
            response = client.models.embed_content(
                model=GEMINI_EMBEDDING_MODEL,
                contents=batch,
            )
            if hasattr(response, "embeddings") and response.embeddings:
                vectors: List[List[float]] = []
                for item in response.embeddings:
                    if hasattr(item, "values"):
                        vectors.append(list(item.values))
                    elif hasattr(item, "embedding"):
                        vectors.append(list(item.embedding))
                return vectors
            if isinstance(response, dict) and "embeddings" in response:
                return [item.get("values", item.get("embedding", [])) for item in response["embeddings"]]
            raise ValueError("Unexpected embedding response format")

        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            cached = cached_batch_call("embed", batch, _embed_batch)
            embeddings.extend([item for item in cached if item is not None])

        return embeddings

    def upsert_embeddings(
        self,
        embeddings: List[List[float]],
        metadatas: Iterable[Dict[str, str | int]],
        ids: List[str],
    ) -> List[str]:
        """Upsert embeddings with metadata into Qdrant."""

        if not embeddings:
            return []
        self._ensure_collection(vector_size=len(embeddings[0]))
        points: List[PointStruct] = []
        qdrant_ids: List[str] = []
        for embedding, metadata, point_id in zip(embeddings, metadatas, ids):
            qdrant_id = self._to_uuid(point_id)
            payload = dict(metadata)
            payload["source_id"] = point_id
            points.append(PointStruct(id=qdrant_id, vector=embedding, payload=payload))
            qdrant_ids.append(qdrant_id)
        self.client.upsert(collection_name=self.collection_name, points=points)
        return qdrant_ids

    def embed_and_store(
        self,
        texts: List[str],
        metadatas: List[Dict[str, str | int]],
        ids: List[str],
    ) -> Tuple[List[List[float]], List[str]]:
        """Embed texts and store them in Qdrant."""

        embeddings = self.embed_texts(texts)
        qdrant_ids = self.upsert_embeddings(embeddings, metadatas, ids)
        return embeddings, qdrant_ids
