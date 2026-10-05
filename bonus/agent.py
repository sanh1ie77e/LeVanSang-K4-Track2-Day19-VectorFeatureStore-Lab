"""Minimal hybrid episodic memory + Feast profile context (no paid LLM call)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from feast import FeatureStore
from qdrant_client import QdrantClient, models
from rank_bm25 import BM25Okapi

from app.embeddings import Embedder

ROOT = Path(__file__).resolve().parents[1]


class HybridMemoryAgent:
    """User-filtered vector retrieval, BM25 and 1-based RRF, plus online features.

    The caller must supply an authenticated user_id in a real service.
    This POC keeps episodic memories in RAM for the lifetime of the agent.
    """

    def __init__(self, feature_store=None, embedder=None):
        self.embedder = embedder or Embedder()
        self.feature_store = feature_store or FeatureStore(repo_path=str(ROOT / "app/feast_repo"))
        self.client = QdrantClient(":memory:")
        self.collection = "episodic_memory"
        self.client.create_collection(
            self.collection,
            vectors_config=models.VectorParams(size=self.embedder.dim, distance=models.Distance.COSINE),
        )
        self.memories: dict[str, dict] = {}

    @staticmethod
    def _check(text: str, user_id: str) -> None:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text/query must not be empty")
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id must not be empty")

    @staticmethod
    def _chunks(text: str, size: int = 120, overlap: int = 20) -> list[str]:
        """120 whitespace tokens with 20-token overlap; preserve original accents."""
        words = text.split()
        chunks = []
        for start in range(0, len(words), size - overlap):
            chunks.append(" ".join(words[start:start + size]))
            if start + size >= len(words):
                break
        return chunks

    def remember(self, text: str, user_id: str = "u_001") -> None:
        self._check(text, user_id)
        chunks = self._chunks(text)
        vectors = list(self.embedder.embed(chunks))
        pending = {}
        points = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            memory_id = str(uuid4())
            payload = {"user_id": user_id, "text": chunk,
                       "created_at": datetime.now(timezone.utc).isoformat()}
            pending[memory_id] = payload
            points.append(models.PointStruct(id=memory_id, vector=vector.tolist(), payload=payload))
        self.client.upsert(self.collection, points=points)
        self.memories.update(pending)

    def recall(self, query: str, user_id: str = "u_001") -> str:
        self._check(query, user_id)
        profiles = self.feature_store.get_online_features(
            features=["user_profile_features:reading_speed_wpm",
                      "user_profile_features:preferred_language",
                      "user_profile_features:topic_affinity",
                      "query_velocity_features:queries_last_hour",
                      "query_velocity_features:distinct_topics_24h"],
            entity_rows=[{"user_id": user_id}],
        ).to_dict()
        profile = {key: values[0] for key, values in profiles.items()}
        owned = [(key, value) for key, value in self.memories.items() if value["user_id"] == user_id]
        ranked = []
        if owned:
            bm25 = BM25Okapi([value["text"].lower().split() for _, value in owned])
            scores = bm25.get_scores(query.lower().split())
            keyword = [owned[i][0] for i in sorted(range(len(owned)), key=lambda i: -scores[i])[:50]]
            vector = next(self.embedder.embed([query])).tolist()
            semantic = self.client.query_points(
                self.collection, query=vector, limit=50,
                query_filter=models.Filter(must=[models.FieldCondition(
                    key="user_id", match=models.MatchValue(value=user_id))]),
            ).points
            fused: dict[str, float] = {}
            for ids in (keyword, [str(point.id) for point in semantic]):
                for rank, memory_id in enumerate(ids, start=1):
                    fused[memory_id] = fused.get(memory_id, 0.0) + 1 / (60 + rank)
            ranked = sorted(fused, key=lambda key: -fused[key])[:3]
        context = [f"User: {user_id}; query: {query}",
                   f"Profile: language={profile.get('preferred_language')}; "
                   f"topic={profile.get('topic_affinity')}; reading={profile.get('reading_speed_wpm')} wpm.",
                   f"Recent activity (materialized snapshot): queries_last_hour={profile.get('queries_last_hour')}; "
                   f"distinct_topics_24h={profile.get('distinct_topics_24h')}.",
                   "Top episodic memories (BM25 + vector + RRF k=60):"]
        context.extend(f"- [{key}] {self.memories[key]['text']}" for key in ranked)
        if not ranked:
            context.append("- No memories for this user.")
        return "\n".join(context)

    def close(self) -> None:
        self.client.close()
