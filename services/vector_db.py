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
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    Range,
    SearchParams,
    VectorParams,
)

from config import settings

logger = logging.getLogger(__name__)


class VectorDBService:
    """Service for interacting with Qdrant vector database."""

    def __init__(self):
        """Initialize Qdrant client."""
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            timeout=settings.qdrant_timeout,
        )
        self.embedding_dim = settings.embedding_dim
        logger.info(
            f"Initialized VectorDBService with Qdrant at {settings.qdrant_host}:{settings.qdrant_port}"
        )

    def ensure_collection(self, collection_name: str) -> None:
        """
        Ensure collection exists with proper configuration.

        Args:
            collection_name: Name of the collection
        """
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

        points = []
        point_ids = []

        for text, vector, meta in zip(texts, vectors, metadata):
            point_id = str(uuid4())
            point_ids.append(point_id)

            # Add text to metadata
            meta["text"] = text
            meta["ingested_at"] = datetime.utcnow().isoformat()

            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=meta,
                )
            )

        try:
            self.client.upsert(collection_name=collection_name, points=points)
            logger.info(
                f"Upserted {len(points)} vectors to collection {collection_name}"
            )
            return point_ids
        except Exception as e:
            logger.error(f"Error upserting vectors to {collection_name}: {e}")
            raise

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
        try:
            # Build filter conditions
            filter_conditions = []

            if filters:
                # Date range filtering
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

                # Jurisdiction filtering
                if "jurisdiction" in filters:
                    filter_conditions.append(
                        FieldCondition(
                            key="jurisdiction",
                            match=MatchValue(value=filters["jurisdiction"]),
                        )
                    )

                # Regulator filtering
                if "regulator" in filters:
                    filter_conditions.append(
                        FieldCondition(
                            key="regulator",
                            match=MatchValue(value=filters["regulator"]),
                        )
                    )

                # Active status filtering
                if "is_active" in filters:
                    filter_conditions.append(
                        FieldCondition(
                            key="is_active",
                            match=MatchValue(value=filters["is_active"]),
                        )
                    )

            query_filter = Filter(must=filter_conditions) if filter_conditions else None

            # Vector search
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=top_k,
                score_threshold=0.5,  # Minimum similarity threshold
            )

            # Format results
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
                f"Hybrid search returned {len(formatted_results)} results from {collection_name}"
            )
            return formatted_results

        except Exception as e:
            logger.error(f"Error in hybrid search on {collection_name}: {e}")
            raise

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
        try:
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
