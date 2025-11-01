"""
Enhanced logging configuration for agent execution tracing.

Add this to individual agent files to see detailed step-by-step execution.

Usage in agent files:
    from scripts.agent_logging_config import get_agent_logger
    
    logger = get_agent_logger(__name__)
    
    logger.info("Agent starting execution")
    logger.debug(f"Input state: {state}")
"""

import logging
from typing import Any, Dict


def get_agent_logger(name: str) -> logging.Logger:
    """
    Get a configured logger for an agent.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    return logger


def log_agent_start(logger: logging.Logger, agent_name: str, state: Dict[str, Any]):
    """Log agent execution start with state summary."""
    logger.info("="*60)
    logger.info(f"🚀 {agent_name} - STARTING")
    logger.info("="*60)
    logger.debug(f"Input state keys: {list(state.keys())}")
    
    if "transaction_id" in state:
        logger.info(f"Transaction ID: {state['transaction_id']}")


def log_agent_end(logger: logging.Logger, agent_name: str, result: Dict[str, Any], duration: float = None):
    """Log agent execution completion with results summary."""
    logger.info("-"*60)
    logger.info(f"✅ {agent_name} - COMPLETED")
    
    if duration:
        logger.info(f"Duration: {duration:.3f}s")
    
    # Log what this agent added to state
    new_keys = [k for k in result.keys() if not k.startswith('_')]
    logger.debug(f"Output state keys: {new_keys}")
    
    logger.info("="*60)


def log_llm_call(logger: logging.Logger, prompt: str, response: str = None):
    """Log LLM interaction."""
    logger.debug("-"*40)
    logger.debug("🤖 LLM CALL")
    logger.debug(f"Prompt length: {len(prompt)} chars")
    logger.debug(f"Prompt preview: {prompt[:200]}...")
    
    if response:
        logger.debug(f"Response length: {len(response)} chars")
        logger.debug(f"Response preview: {response[:200]}...")
    logger.debug("-"*40)


def log_vector_search(logger: logging.Logger, query: str, results_count: int):
    """Log vector database search."""
    logger.debug("-"*40)
    logger.debug("🔍 VECTOR SEARCH")
    logger.debug(f"Query: {query[:100]}...")
    logger.debug(f"Results found: {results_count}")
    logger.debug("-"*40)


def log_agent_error(logger: logging.Logger, agent_name: str, error: Exception):
    """Log agent execution error."""
    logger.error("="*60)
    logger.error(f"❌ {agent_name} - ERROR")
    logger.error(f"Error: {error}")
    logger.error("="*60, exc_info=True)


# Example: How to add logging to an agent
EXAMPLE_AGENT_WITH_LOGGING = """
# Example: agents/part1/retrieval.py

import logging
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)


class RetrievalAgent:
    def __init__(self, llm_service, pinecone_internal, pinecone_external):
        self.llm_service = llm_service
        self.pinecone_internal = pinecone_internal
        self.pinecone_external = pinecone_external
        logger.info("RetrievalAgent initialized")
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        
        # Log start
        logger.info("="*60)
        logger.info("🚀 RetrievalAgent - STARTING")
        logger.info("="*60)
        logger.info(f"Transaction ID: {state.get('transaction_id')}")
        
        try:
            # Get query context
            query_context = state.get("query_context", "")
            logger.debug(f"Query context length: {len(query_context)}")
            
            # Search internal rules
            logger.info("Searching internal rules index...")
            internal_results = await self.pinecone_internal.search_by_text(
                query_text=query_context,
                top_k=10
            )
            logger.info(f"Found {len(internal_results)} internal rules")
            
            # Search external rules
            logger.info("Searching external rules index...")
            external_results = await self.pinecone_external.search_by_text(
                query_text=query_context,
                top_k=5
            )
            logger.info(f"Found {len(external_results)} external rules")
            
            # Combine results
            all_rules = internal_results + external_results
            logger.info(f"Total rules retrieved: {len(all_rules)}")
            
            # Log sample rule
            if all_rules:
                sample = all_rules[0]
                logger.debug(f"Sample rule: {sample.get('metadata', {}).get('rule_id', 'N/A')}")
            
            duration = time.time() - start_time
            
            # Log completion
            logger.info("-"*60)
            logger.info(f"✅ RetrievalAgent - COMPLETED in {duration:.3f}s")
            logger.info("="*60)
            
            return {
                **state,
                "retrieved_rules": all_rules,
                "retrieval_executed": True,
            }
            
        except Exception as e:
            logger.error(f"❌ RetrievalAgent - ERROR: {e}", exc_info=True)
            return {
                **state,
                "retrieved_rules": [],
                "retrieval_executed": False,
                "errors": state.get("errors", []) + [f"RetrievalAgent: {str(e)}"],
            }
"""
