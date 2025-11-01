"""
Transaction Simulator

Simulates transaction submission from CSV file for demo purposes.
Reads transactions_mock_1000_for_participants.csv and submits to API.
"""

import logging
import csv
import time
import requests
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TransactionSimulator:
    """Simulates transaction submissions"""
    
    def __init__(self, api_base_url="http://localhost:8000"):
        self.api_base_url = api_base_url
        self.endpoint = f"{api_base_url}/transactions"
    
    def load_transactions(self, csv_path: str):
        """Load transactions from CSV file"""
        transactions = []
        
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                transactions.append(row)
        
        logger.info(f"Loaded {len(transactions)} transactions from {csv_path}")
        return transactions
    
    def submit_transaction(self, transaction: dict):
        """Submit a transaction to the API"""
        try:
            # Transform CSV row to API format
            payload = {
                "transaction_type": transaction.get("transaction_type", "transfer"),
                "amount": float(transaction.get("amount", 0)),
                "currency": transaction.get("currency", "USD"),
                "sender_account": transaction.get("sender_account", ""),
                "sender_country": transaction.get("sender_country", "HK"),
                "receiver_account": transaction.get("receiver_account", ""),
                "receiver_country": transaction.get("receiver_country", "US"),
                "purpose": transaction.get("purpose", ""),
                "timestamp": transaction.get("timestamp", ""),
                "jurisdiction": transaction.get("jurisdiction", "HK"),
            }
            
            response = requests.post(self.endpoint, json=payload)
            response.raise_for_status()
            
            result = response.json()
            task_id = result.get("task_id")
            
            logger.info(f"✅ Submitted transaction: task_id={task_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"❌ Error submitting transaction: {str(e)}")
            return None
    
    def simulate(self, csv_path: str, batch_size: int = 10, delay: float = 1.0):
        """
        Simulate transaction submissions in batches.
        
        Args:
            csv_path: Path to CSV file
            batch_size: Number of transactions per batch
            delay: Delay between batches (seconds)
        """
        transactions = self.load_transactions(csv_path)
        
        logger.info(f"Starting simulation: {len(transactions)} transactions")
        logger.info(f"Batch size: {batch_size}, Delay: {delay}s")
        
        submitted_count = 0
        failed_count = 0
        
        for i in range(0, len(transactions), batch_size):
            batch = transactions[i:i+batch_size]
            
            logger.info(f"\nBatch {i//batch_size + 1}: Submitting {len(batch)} transactions...")
            
            for transaction in batch:
                task_id = self.submit_transaction(transaction)
                if task_id:
                    submitted_count += 1
                else:
                    failed_count += 1
            
            # Delay between batches
            if i + batch_size < len(transactions):
                logger.info(f"Waiting {delay}s before next batch...")
                time.sleep(delay)
        
        logger.info("\n" + "="*60)
        logger.info(f"Simulation complete!")
        logger.info(f"Submitted: {submitted_count}")
        logger.info(f"Failed: {failed_count}")
        logger.info("="*60)


def main():
    """Entry point"""
    # Path to CSV file
    csv_path = Path(__file__).parent.parent / "transactions_mock_1000_for_participants.csv"
    
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return
    
    # Initialize simulator
    simulator = TransactionSimulator(api_base_url="http://localhost:8000")
    
    # Run simulation
    # Submit 100 transactions in batches of 10, with 2s delay
    simulator.simulate(
        csv_path=str(csv_path),
        batch_size=10,
        delay=2.0
    )


if __name__ == "__main__":
    main()
