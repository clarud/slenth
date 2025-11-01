"""
Vector Database Service - Qdrant client wrapper for hybrid search.

Provides methods for:
- Upserting vectors with metadata
- Hybrid search (BM25 + vector similarity)
- Filtering by date, jurisdiction, etc.
- Batch operations
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from config import settings

_provider = getattr(settings, "vector_db_provider", "pinecone").lower()

# Optional Qdrant imports guarded by provider (kept for backward compatibility)
if _provider == "qdrant":  # pragma: no cover
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        FieldCondition,
        Filter,
        MatchValue,
        PointStruct,
        Range,
        VectorParams,
    )
else:
    QdrantClient = None  # type: ignore
    PointStruct = None  # type: ignore

# Pinecone v7+ client
try:
    from pinecone import Pinecone  # type: ignore
except Exception:  # pragma: no cover
    Pinecone = None  # type: ignore

logger = logging.getLogger(__name__)


class VectorDBService:
    """Service for interacting with Qdrant vector database."""

    def __init__(self):
        """Initialize Qdrant client."""
        self.provider = _provider
        self.embedding_dim = settings.embedding_dimension
        if self.provider == "qdrant":  # pragma: no cover
            self.client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                timeout=getattr(settings, "qdrant_timeout", 60),
                api_key=getattr(settings, "qdrant_api_key", None),
            )
            logger.info(
                f"Initialized VectorDBService (Qdrant) at {settings.qdrant_host}:{settings.qdrant_port}"
            )
        elif self.provider == "pinecone":
            if Pinecone is None:
                raise RuntimeError("pinecone package not installed but vector_db_provider is 'pinecone'")
            self.pc = Pinecone(api_key=getattr(settings, "pinecone_api_key", None))
            # Hosts for two logical indexes
            self.external_index_host = getattr(settings, "pinecone_external_index_host", None)
            self.internal_index_host = getattr(settings, "pinecone_internal_index_host", None)
            if not self.external_index_host or not self.internal_index_host:
                logger.warning("Pinecone hosts not fully configured; set PINECONE_EXTERNAL_INDEX_HOST and PINECONE_INTERNAL_INDEX_HOST")
            logger.info("Initialized VectorDBService (Pinecone)")
        else:
            raise RuntimeError(f"Unknown vector_db_provider: {self.provider}")

    def ensure_collection(self, collection_name: str) -> None:
        """
        Ensure collection exists with proper configuration.

        Args:
            collection_name: Name of the collection
        """
        if self.provider == "qdrant":
            try:
                collections = self.client.get_collections().collections
                collection_names = [c.name for c in collections]
                if collection_name not in collection_names:
                    logger.info(f"Creating collection: {collection_name}")
                    self.client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=self.embedding_dim, distance=Distance.COSINE
                        ),
                    )
                else:
                    logger.debug(f"Collection {collection_name} already exists")
            except Exception as e:
                logger.error(f"Error ensuring collection {collection_name}: {e}")
                raise
        else:
            # Pinecone: indexes are pre-created and addressed by host; nothing to ensure here.
            return

    def upsert_vectors(
        self,
        collection_name: str,
        texts: List[str],
        vectors: List[List[float]],
        metadata: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Upsert vectors with metadata into collection.

        Args:
            collection_name: Target collection
            texts: List of text content
            vectors: List of embedding vectors
            metadata: List of metadata dicts

        Returns:
            List of point IDs
        """
        if not (len(texts) == len(vectors) == len(metadata)):
            raise ValueError("texts, vectors, and metadata must have same length")

        self.ensure_collection(collection_name)

        point_ids = []

        if self.provider == "qdrant":  # pragma: no cover
            points = []
            for text, vector, meta in zip(texts, vectors, metadata):
                point_id = str(uuid4())
                point_ids.append(point_id)
                meta = dict(meta)
                meta["text"] = text
                meta["ingested_at"] = datetime.utcnow().isoformat()
                points.append(
                    PointStruct(id=point_id, vector=vector, payload=meta)
                )
            try:
                self.client.upsert(collection_name=collection_name, points=points)
                logger.info(
                    f"Upserted {len(points)} vectors to collection {collection_name} (Qdrant)"
                )
                return point_ids
            except Exception as e:
                logger.error(f"Error upserting vectors to {collection_name}: {e}")
                raise
        else:
            # Pinecone expects separate indexes; choose based on collection_name
            host = self.external_index_host if "external" in collection_name else self.internal_index_host
            if not host:
                raise RuntimeError("Pinecone index host not configured for collection: " + collection_name)
            index = self.pc.Index(host=host)
            items = []
            for text, vector, meta in zip(texts, vectors, metadata):
                point_id = str(uuid4())
                point_ids.append(point_id)
                meta = dict(meta)
                meta["text"] = text
                meta["ingested_at"] = datetime.utcnow().isoformat()
                items.append({"id": point_id, "values": vector, "metadata": meta})
            index.upsert(vectors=items)
            logger.info(
                f"Upserted {len(items)} vectors to collection {collection_name} (Pinecone)"
            )
            return point_ids

    def hybrid_search(
        self,
        collection_name: str,
        query_vector: List[float],
        query_text: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector similarity and keyword matching.

        Args:
            collection_name: Collection to search
            query_vector: Query embedding vector
            query_text: Query text for BM25
            top_k: Number of results to return
            filters: Optional metadata filters

        Returns:
            List of search results with scores
        """
        if self.provider == "qdrant":  # pragma: no cover
            try:
                # Build filter conditions
                from qdrant_client.models import MatchValue, Range, FieldCondition, Filter  # type: ignore

                filter_conditions = []
                if filters:
                    if "effective_date_from" in filters:
                        filter_conditions.append(
                            FieldCondition(
                                key="effective_date",
                                range=Range(gte=filters["effective_date_from"]),
                            )
                        )
                    if "effective_date_to" in filters:
                        filter_conditions.append(
                            FieldCondition(
                                key="effective_date",
                                range=Range(lte=filters["effective_date_to"]),
                            )
                        )
                    if "jurisdiction" in filters:
                        filter_conditions.append(
                            FieldCondition(
                                key="jurisdiction",
                                match=MatchValue(value=filters["jurisdiction"]),
                            )
                        )
                    if "regulator" in filters:
                        filter_conditions.append(
                            FieldCondition(
                                key="regulator",
                                match=MatchValue(value=filters["regulator"]),
                            )
                        )
                    if "is_active" in filters:
                        filter_conditions.append(
                            FieldCondition(
                                key="is_active",
                                match=MatchValue(value=filters["is_active"]),
                            )
                        )
                query_filter = Filter(must=filter_conditions) if filter_conditions else None
                results = self.client.search(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    query_filter=query_filter,
                    limit=top_k,
                    score_threshold=0.5,
                )
                formatted_results = []
                for result in results:
                    formatted_results.append(
                        {
                            "id": result.id,
                            "score": result.score,
                            "text": result.payload.get("text", ""),
                            "metadata": {
                                k: v
                                for k, v in result.payload.items()
                                if k not in ["text", "ingested_at"]
                            },
                            "ingested_at": result.payload.get("ingested_at"),
                        }
                    )
                logger.info(
                    f"Hybrid search returned {len(formatted_results)} results from {collection_name} (Qdrant)"
                )
                return formatted_results
            except Exception as e:
                logger.error(f"Error in hybrid search on {collection_name}: {e}")
                raise
        else:
            # Pinecone: no built-in hybrid search; do vector-only search
            host = self.external_index_host if "external" in collection_name else self.internal_index_host
            if not host:
                raise RuntimeError("Pinecone index host not configured for collection: " + collection_name)
            index = self.pc.Index(host=host)
            res = index.query(vector=query_vector, top_k=top_k, include_metadata=True)
            formatted = []
            for match in getattr(res, "matches", []):
                meta = getattr(match, "metadata", {}) or {}
                formatted.append(
                    {
                        "id": getattr(match, "id", None),
                        "score": getattr(match, "score", 0.0),
                        "text": meta.get("text", ""),
                        "metadata": {k: v for k, v in meta.items() if k not in ["text", "ingested_at"]},
                        "ingested_at": meta.get("ingested_at"),
                    }
                )
            logger.info(
                f"Vector search returned {len(formatted)} results from {collection_name} (Pinecone)"
            )
            return formatted

    def search_by_filters(
        self,
        collection_name: str,
        filters: Dict[str, Any],
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search by metadata filters only (no vector search).

        Args:
            collection_name: Collection to search
            filters: Metadata filters
            limit: Maximum number of results

        Returns:
            List of matching documents
        """
        try:  # pragma: no cover
            filter_conditions = []

            for key, value in filters.items():
                if isinstance(value, dict) and "gte" in value:
                    filter_conditions.append(
                        FieldCondition(key=key, range=Range(gte=value["gte"]))
                    )
                elif isinstance(value, dict) and "lte" in value:
                    filter_conditions.append(
                        FieldCondition(key=key, range=Range(lte=value["lte"]))
                    )
                else:
                    filter_conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )

            query_filter = Filter(must=filter_conditions) if filter_conditions else None

            # Scroll through results
            results, _ = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=query_filter,
                limit=limit,
            )

            formatted_results = []
            for result in results:
                formatted_results.append(
                    {
                        "id": result.id,
                        "text": result.payload.get("text", ""),
                        "metadata": {
                            k: v
                            for k, v in result.payload.items()
                            if k not in ["text", "ingested_at"]
                        },
                    }
                )

            logger.info(
                f"Filter search returned {len(formatted_results)} results from {collection_name}"
            )
            return formatted_results

        except Exception as e:
            logger.error(f"Error in filter search on {collection_name}: {e}")
            raise

    def delete_by_id(self, collection_name: str, point_ids: List[str]) -> None:
        """
        Delete points by IDs.

        Args:
            collection_name: Collection name
            point_ids: List of point IDs to delete
        """
        try:
            self.client.delete(collection_name=collection_name, points_selector=point_ids)
            logger.info(f"Deleted {len(point_ids)} points from {collection_name}")
        except Exception as e:
            logger.error(f"Error deleting points from {collection_name}: {e}")
            raise

    def count_points(self, collection_name: str) -> int:
        """
        Count total points in collection.

        Args:
            collection_name: Collection name

        Returns:
            Number of points
        """
        try:
            collection_info = self.client.get_collection(collection_name)
            return collection_info.points_count
        except Exception as e:
            logger.error(f"Error counting points in {collection_name}: {e}")
            return 0

    def get_collections(self) -> List[str]:
        """
        Get list of all collection names.

        Returns:
            List of collection names
        """
        try:
            collections = self.client.get_collections().collections
            return [c.name for c in collections]
        except Exception as e:
            logger.error(f"Error getting collections: {e}")
            return []
