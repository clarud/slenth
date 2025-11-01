"""
ContextBuilder Agent - Build query context from transaction data.

This agent converts transaction JSON into rules-like query strings and pulls
short transaction history for the customer/account. Formats context for downstream retrieval.

Logic:
1. Extract key fields from transaction (jurisdiction, customer_risk, amount, counterparty countries)
2. Build query strings that match rule language
3. Fetch recent transaction history for customer (last 30 days)
4. Format as structured context dict

Output:
- query_strings: List[str]
- transaction_history: List[Dict]
- context_summary: str
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from agents import Part1Agent
from db.models import Transaction

logger = logging.getLogger(__name__)


class ContextBuilderAgent(Part1Agent):
    """Agent to build context from transaction data."""

    def __init__(self, db_session: Session):
        super().__init__("ContextBuilder")
        self.db = db_session

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build context from transaction.

        Args:
            state: Workflow state containing transaction data

        Returns:
            Updated state with query_strings and transaction_history
        """
        transaction = state.get("transaction", {})
        transaction_id = transaction.get("transaction_id")

        self.logger.info(f"Building context for transaction {transaction_id}")

        # Build query strings from transaction
        query_strings = self._build_query_strings(transaction)

        # Fetch transaction history
        customer_id = transaction.get("customer_id")
        transaction_history = self._fetch_transaction_history(customer_id)

        # Create context summary
        context_summary = self._create_context_summary(transaction, transaction_history)

        # Update state
        state["query_strings"] = query_strings
        state["transaction_history"] = transaction_history
        state["context_summary"] = context_summary

        self.logger.info(
            f"Built context with {len(query_strings)} queries and "
            f"{len(transaction_history)} historical transactions"
        )

        return state

    def _build_query_strings(self, transaction: Dict[str, Any]) -> List[str]:
        """
        Build query strings from transaction fields.

        Creates natural language queries that match regulatory rule language.
        """
        queries = []

        # Jurisdiction-based query
        jurisdiction = transaction.get("booking_jurisdiction")
        if jurisdiction:
            queries.append(f"{jurisdiction} jurisdiction regulatory requirements")
            queries.append(f"{jurisdiction} AML surveillance rules")

        # Customer risk-based query
        risk_rating = transaction.get("customer_risk_rating")
        if risk_rating:
            queries.append(f"{risk_rating} risk customer due diligence requirements")

        # PEP-related query
        if transaction.get("customer_is_pep"):
            queries.append("politically exposed person PEP enhanced due diligence")

        # EDD-related query
        if transaction.get("edd_required") and not transaction.get("edd_performed"):
            queries.append("enhanced due diligence requirements missing documentation")

        # High-risk jurisdiction query
        originator_country = transaction.get("originator_country")
        beneficiary_country = transaction.get("beneficiary_country")
        if originator_country:
            queries.append(f"{originator_country} originator country AML requirements")
        if beneficiary_country:
            queries.append(f"{beneficiary_country} beneficiary country sanctions screening")

        # SWIFT/Travel rule query
        if not transaction.get("travel_rule_complete"):
            queries.append("SWIFT travel rule compliance FATF requirements")

        # Virtual assets query
        if transaction.get("product_has_va_exposure"):
            queries.append("virtual assets cryptocurrency due diligence")

        # Cash handling query
        if transaction.get("cash_id_verified") is False:
            queries.append("cash transaction identification verification requirements")

        # Amount-based query
        amount = transaction.get("amount", 0)
        if amount > 100000:
            queries.append("large value transaction reporting requirements")
        if amount > 500000:
            queries.append("suspicious transaction reporting threshold")

        return queries

    def _fetch_transaction_history(
        self, customer_id: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent transaction history for customer.

        Args:
            customer_id: Customer ID
            days: Number of days to look back

        Returns:
            List of recent transactions
        """
        if not customer_id:
            return []

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        try:
            transactions = (
                self.db.query(Transaction)
                .filter(
                    Transaction.customer_id == customer_id,
                    Transaction.booking_datetime >= cutoff_date,
                )
                .order_by(Transaction.booking_datetime.desc())
                .limit(50)
                .all()
            )

            return [
                {
                    "transaction_id": t.transaction_id,
                    "amount": t.amount,
                    "currency": t.currency,
                    "booking_datetime": t.booking_datetime.isoformat(),
                    "originator_country": t.originator_country,
                    "beneficiary_country": t.beneficiary_country,
                }
                for t in transactions
            ]
        except Exception as e:
            self.logger.error(f"Error fetching transaction history: {e}")
            return []

    def _create_context_summary(
        self, transaction: Dict[str, Any], history: List[Dict[str, Any]]
    ) -> str:
        """Create natural language context summary."""
        summary_parts = []

        # Transaction details
        summary_parts.append(
            f"Transaction {transaction.get('transaction_id')} in "
            f"{transaction.get('booking_jurisdiction')} jurisdiction"
        )

        # Customer details
        summary_parts.append(
            f"Customer {transaction.get('customer_id')} "
            f"with {transaction.get('customer_risk_rating')} risk rating"
        )

        # PEP status
        if transaction.get("customer_is_pep"):
            summary_parts.append("Customer is a Politically Exposed Person (PEP)")

        # History summary
        if history:
            total_amount = sum(t.get("amount", 0) for t in history)
            summary_parts.append(
                f"Customer has {len(history)} transactions in last 30 days "
                f"totaling {total_amount:.2f}"
            )

        return ". ".join(summary_parts)
