"""
Base agent classes and utilities for all agents.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all agents in the AML system."""

    def __init__(self, name: str):
        """
        Initialize base agent.

        Args:
            name: Agent name
        """
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")

    @abstractmethod
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's logic.

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        pass

    def log_execution(self, state: Dict[str, Any], result: Any) -> None:
        """Log agent execution details."""
        self.logger.info(
            f"Agent {self.name} executed for "
            f"transaction_id={state.get('transaction_id', 'N/A')} "
            f"document_id={state.get('document_id', 'N/A')}"
        )


class Part1Agent(BaseAgent):
    """Base class for Part 1 (transaction monitoring) agents."""

    def __init__(self, name: str):
        super().__init__(name)

    def get_transaction_id(self, state: Dict[str, Any]) -> Optional[str]:
        """Extract transaction ID from state."""
        return state.get("transaction", {}).get("transaction_id")


class Part2Agent(BaseAgent):
    """Base class for Part 2 (document corroboration) agents."""

    def __init__(self, name: str):
        super().__init__(name)

    def get_document_id(self, state: Dict[str, Any]) -> Optional[str]:
        """Extract document ID from state."""
        return state.get("document", {}).get("document_id")
