"""
Pinecone Vector Database Service for rules storage and similarity search.

Provides methods for:
- Upserting vectors with metadata
- Similarity search
- Filtering by metadata
- Batch operations
"""

import logging
from typing import Any, Dict, List, Optional
from pinecone import Pinecone

from config import settings

logger = logging.getLogger(__name__)


class PineconeService:
    """Service for interacting with Pinecone vector database."""

    def __init__(self, index_type: str = "internal"):
        """
        Initialize Pinecone client.
        
        Args:
            index_type: Either "internal" or "external" to specify which index to use
        """
        self.pc = Pinecone(api_key=settings.pinecone_api_key)
        self.embedding_dim = settings.embedding_dimension
        self.index_type = index_type
        
        # Get the appropriate index host
        if index_type == "internal":
            index_host = settings.pinecone_internal_index_host
        elif index_type == "external":
            index_host = settings.pinecone_external_index_host
        else:
            raise ValueError(f"Invalid index_type: {index_type}. Must be 'internal' or 'external'")
        
        # Connect to existing index using host
        self.index = self.pc.Index(host=index_host)
        
        logger.info(f"Initialized PineconeService with {index_type} index: {index_host}")

    def upsert_vectors(
        self,
        vectors: List[List[float]],
        metadata_list: List[Dict[str, Any]],
        ids: List[str],
    ) -> bool:
        """
        Upsert vectors with metadata to Pinecone.

        Args:
            vectors: List of embedding vectors
            metadata_list: List of metadata dictionaries
            ids: List of unique IDs for vectors

        Returns:
            True if successful
        """
        try:
            # Prepare vectors for upsert
            vectors_to_upsert = [
                {
                    "id": str(id_),
                    "values": vector,
                    "metadata": metadata
                }
                for id_, vector, metadata in zip(ids, vectors, metadata_list)
            ]
            
            # Upsert in batches of 100
            batch_size = 100
            for i in range(0, len(vectors_to_upsert), batch_size):
                batch = vectors_to_upsert[i:i + batch_size]
                self.index.upsert(vectors=batch)
            
            logger.info(f"Upserted {len(vectors_to_upsert)} vectors to Pinecone")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e}")
            return False

    async def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        namespace: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Perform similarity search in Pinecone.

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filters: Metadata filters (e.g., {"category": "kyc", "is_active": True})
            namespace: Pinecone namespace (optional)

        Returns:
            List of matching results with metadata and scores
        """
        try:
            # Build filter for Pinecone query
            pinecone_filter = None
            if filters:
                # Convert filters to Pinecone filter format
                pinecone_filter = self._build_pinecone_filter(filters)
            
            # Query Pinecone
            results = self.index.query(
                vector=query_vector,
                top_k=top_k,
                filter=pinecone_filter,
                namespace=namespace,
                include_metadata=True
            )
            
            # Format results
            formatted_results = []
            for match in results['matches']:
                result = {
                    "rule_id": match['id'],
                    "score": match['score'],
                    **match.get('metadata', {})
                }
                formatted_results.append(result)
            
            logger.info(f"Found {len(formatted_results)} results for similarity search")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []

    def _build_pinecone_filter(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert simple filters to Pinecone filter format.
        
        Args:
            filters: Dictionary of field: value pairs
            
        Returns:
            Pinecone-formatted filter
        """
        # Pinecone filter format: {"field": {"$eq": value}}
        pinecone_filter = {}
        
        for field, value in filters.items():
            if isinstance(value, bool):
                pinecone_filter[field] = {"$eq": value}
            elif isinstance(value, (int, float)):
                pinecone_filter[field] = {"$eq": value}
            elif isinstance(value, str):
                pinecone_filter[field] = {"$eq": value}
            elif isinstance(value, list):
                pinecone_filter[field] = {"$in": value}
        
        return pinecone_filter

    def delete_by_ids(self, ids: List[str], namespace: str = "") -> bool:
        """
        Delete vectors by IDs.

        Args:
            ids: List of vector IDs to delete
            namespace: Pinecone namespace (optional)

        Returns:
            True if successful
        """
        try:
            self.index.delete(ids=ids, namespace=namespace)
            logger.info(f"Deleted {len(ids)} vectors from Pinecone")
            return True
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            return False

    def get_index_stats(self, namespace: str = "") -> Dict[str, Any]:
        """
        Get index statistics.

        Args:
            namespace: Pinecone namespace (optional)

        Returns:
            Dictionary with index stats
        """
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats.get('total_vector_count', 0),
                "dimension": stats.get('dimension', 0),
                "namespaces": stats.get('namespaces', {}),
            }
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {}
