"""
RetrievalAgent - Hybrid search (BM25 + vector) for applicable rules

Logic:

1. Take query_strings from context
2. Generate embeddings for each query
3. Perform hybrid search on external_rules (Qdrant) and internal_rules (Pinecone) collections
4. Apply filters (jurisdiction, effective_date)
5. Re-rank results by relevance
6. Return top-k applicable rules with metadata


Output:
applicable_rules: List[Dict] with rule_id, text, score, metadata
"""

import logging
from typing import Any, Dict

from agents import Part1Agent
from services.llm import LLMService
from services.vector_db import VectorDBService
from services.pinecone_db import PineconeService
from services.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class RetrievalAgent(Part1Agent):
    """Agent: Hybrid search (BM25 + vector) for applicable rules"""

    def __init__(
        self, 
        llm_service: LLMService = None, 
        vector_service: VectorDBService = None,
        pinecone_internal: PineconeService = None,
        pinecone_external: PineconeService = None,
        embedding_service: EmbeddingService = None
    ):
        super().__init__("retrieval")
        self.llm = llm_service
        self.vector_db = vector_service  # Deprecated - for backward compatibility
        self.pinecone_internal = pinecone_internal or PineconeService(index_type="internal")
        self.pinecone_external = pinecone_external or PineconeService(index_type="external")
        self.embeddings = embedding_service or EmbeddingService()

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute retrieval agent logic.

        Args:
            state: Workflow state

        Returns:
            Updated state with applicable_rules
        """
        self.logger.info("Executing RetrievalAgent")

        try:
            # Get query strings from context
            query_strings = state.get("query_strings", [])
            if not query_strings:
                self.logger.warning("No query strings found in state")
                state["applicable_rules"] = []
                return state

            transaction = state.get("transaction", {})
            jurisdiction = transaction.get("jurisdiction", "HK")
            
            # Get current date for effective_date filtering
            from datetime import datetime
            current_date = datetime.utcnow()

            all_rules = []
            seen_rule_ids = set()

            # Perform hybrid search for each query string
            for query in query_strings:
                self.logger.info(f"Searching for query: {query[:100]}...")

                # Generate embedding for query
                query_embedding = self.embeddings.embed_text(query)

                # Search internal rules (Pinecone internal index)
                internal_results = await self.pinecone_internal.similarity_search(
                    query_vector=query_embedding,
                    top_k=10,
                    filters={
                        "jurisdiction": jurisdiction,
                        "is_active": True,
                    }
                )

                # Search external rules (Pinecone external index)
                external_results = await self.pinecone_external.similarity_search(
                    query_vector=query_embedding,
                    top_k=10,
                    filters={
                        "jurisdiction": jurisdiction,
                    }
                )

                # Combine and deduplicate
                for result in internal_results + external_results:
                    rule_id = result.get("rule_id")
                    if rule_id and rule_id not in seen_rule_ids:
                        seen_rule_ids.add(rule_id)
                        
                        # Filter by effective date if present
                        effective_date = result.get("effective_date")
                        if effective_date:
                            try:
                                eff_date = datetime.fromisoformat(str(effective_date))
                                if eff_date > current_date:
                                    continue  # Rule not yet effective
                            except:
                                pass  # Keep rule if date parsing fails
                        
                        all_rules.append({
                            "rule_id": rule_id,
                            "title": result.get("title", ""),
                            "description": result.get("description", ""),
                            "rule_type": result.get("rule_type", ""),
                            "severity": result.get("severity", "medium"),
                            "jurisdiction": result.get("jurisdiction", ""),
                            "source": result.get("source", ""),
                            "score": result.get("score", 0.0),
                            "metadata": result.get("metadata", {}),
                        })

            # Sort by score (descending) and take top 20
            all_rules.sort(key=lambda x: x["score"], reverse=True)
            top_rules = all_rules[:20]

            self.logger.info(f"Retrieved {len(top_rules)} applicable rules")

            state["applicable_rules"] = top_rules
            state["retrieval_completed"] = True

        except Exception as e:
            self.logger.error(f"Error in RetrievalAgent: {str(e)}", exc_info=True)
            state["applicable_rules"] = []
            state["errors"] = state.get("errors", []) + [f"RetrievalAgent: {str(e)}"]

        return state
        state["retrieval_executed"] = True

        return state
