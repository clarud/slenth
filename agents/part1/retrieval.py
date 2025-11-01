"""
RetrievalAgent - Semantic search for applicable rules using Pinecone

Logic:

1. Take query_strings from context
2. Perform semantic search using Pinecone's integrated embeddings (no separate embedding service)
3. Search both internal_rules and external_rules Pinecone indexes
4. Apply filters (jurisdiction, effective_date, is_active)
5. Re-rank results by relevance
6. Return top-k applicable rules with metadata


Output:
applicable_rules: List[Dict] with rule_id, text, score, metadata
"""

import logging
from typing import Any, Dict

from agents import Part1Agent
from services.llm import LLMService
from services.pinecone_db import PineconeService

logger = logging.getLogger(__name__)


class RetrievalAgent(Part1Agent):
    """Agent: Semantic search for applicable rules using Pinecone with integrated embeddings"""

    def __init__(
        self, 
        llm_service: LLMService = None, 
        pinecone_internal: PineconeService = None,
        pinecone_external: PineconeService = None,
    ):
        super().__init__("retrieval")
        self.llm = llm_service
        self.pinecone_internal = pinecone_internal or PineconeService(index_type="internal")
        self.pinecone_external = pinecone_external or PineconeService(index_type="external")

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

            # Perform semantic search for each query string using Pinecone's integrated embeddings
            for query in query_strings:
                self.logger.info(f"Searching for query: {query[:100]}...")

                # Search internal rules (Pinecone internal index) - uses Pinecone's built-in embedding
                internal_results = self.pinecone_internal.search_by_text(
                    query_text=query,
                    top_k=10,
                    filters={
                        "jurisdiction": jurisdiction,
                        "is_active": True,
                    },
                    namespace="internal-rules"
                )

                # Search external rules (Pinecone external index) - uses Pinecone's built-in embedding
                external_results = self.pinecone_external.search_by_text(
                    query_text=query,
                    top_k=10,
                    filters={
                        "jurisdiction": jurisdiction,
                    },
                    namespace="external-rules"
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
