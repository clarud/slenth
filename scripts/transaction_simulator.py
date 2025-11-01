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


def _to_bool(v):
    if isinstance(v, bool):
        return v
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in {"true", "1", "yes", "y"}:
        return True
    if s in {"false", "0", "no", "n"}:
        return False
    return None


def _to_float(v):
    if v is None or str(v).strip() == "":
        return None
    try:
        return float(str(v).replace(",", ""))
    except Exception:
        return None


def _to_int(v):
    if v is None or str(v).strip() == "":
        return None
    try:
        return int(float(str(v).replace(",", "")))
    except Exception:
        return None

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
            # Transform CSV row to API format matching TransactionCreate schema
            # The CSV already has most fields with correct names, just pass them through
            
            # Handle value_date format conversion from DD/M/YYYY to YYYY-MM-DD
            value_date = transaction.get("value_date", "")
            if value_date and "/" in value_date:
                # Parse DD/M/YYYY format and convert to YYYY-MM-DD
                from datetime import datetime
                try:
                    parsed_date = datetime.strptime(value_date, "%d/%m/%Y")
                    value_date = parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    logger.warning(f"Could not parse value_date: {value_date}, using empty string")
                    value_date = ""
            
            payload = {
                # Required basic fields - CSV already has these with correct names
                "transaction_id": transaction.get("transaction_id", f"TXN_{int(time.time())}"),
                "booking_jurisdiction": transaction.get("booking_jurisdiction", "HK"),
                "regulator": transaction.get("regulator", "HKMA"),
                "booking_datetime": transaction.get("booking_datetime", ""),
                "value_date": value_date,
                "amount": float(transaction.get("amount", 0)),
                "currency": transaction.get("currency", "USD"),
                "channel": transaction.get("channel", "SWIFT"),
                "product_type": transaction.get("product_type", "wire_transfer"),
                
                # Originator information - CSV already has these with correct names
                "originator_name": transaction.get("originator_name", "Unknown Sender"),
                "originator_account": transaction.get("originator_account", ""),
                "originator_country": transaction.get("originator_country", "HK"),
                
                # Beneficiary information - CSV already has these with correct names
                "beneficiary_name": transaction.get("beneficiary_name", "Unknown Receiver"),
                "beneficiary_account": transaction.get("beneficiary_account", ""),
                "beneficiary_country": transaction.get("beneficiary_country", "US"),
                
                # SWIFT fields - CSV already has these with correct names
                "swift_mt": transaction.get("swift_mt") or "MT103",  # Default if empty
                "swift_f70_purpose": transaction.get("swift_f70_purpose", ""),
                
                # Customer fields (required) - CSV already has these with correct names
                "customer_id": transaction.get("customer_id") or "CUST_UNKNOWN",  # Default if empty
                "customer_type": transaction.get("customer_type") or "individual",  # Default if empty
                "customer_risk_rating": transaction.get("customer_risk_rating") or "medium",  # Default if empty
            }
            
            logger.info(f"📤 Submitting transaction: {payload['transaction_id']}")
            logger.debug(f"Payload: {payload}")
            
            response = requests.post(self.endpoint, json=payload)
            response.raise_for_status()

            result = response.json()
            task_id = result.get("task_id")
            
            logger.info(f"✅ Submitted transaction: {payload['transaction_id']} -> task_id={task_id}")
            return task_id
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ HTTP Error submitting transaction: {e}")
            if e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"Error details: {error_detail}")
                except:
                    logger.error(f"Response text: {e.response.text}")
            return None
        except Exception as e:
            try:
                # If available, surface server response for easier debugging
                err_text = e.response.text if hasattr(e, "response") and hasattr(e.response, "text") else ""
            except Exception:
                err_text = ""
            logger.error(f"❌ Error submitting transaction: {str(e)} {err_text}")
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


# def main():
#     """Entry point"""
#     # Path to CSV file
#     csv_path = Path(__file__).parent.parent / "transactions_mock_1000_for_participants.csv"
    
#     if not csv_path.exists():
#         logger.error(f"CSV file not found: {csv_path}")
#         return
    
#     # Initialize simulator
#     simulator = TransactionSimulator(api_base_url="http://localhost:8000")
    
#     # Run simulation
#     # Submit 100 transactions in batches of 10, with 2s delay
#     simulator.simulate(
#         csv_path=str(csv_path),
#         batch_size=10,
#         delay=2.0
#     )
def main():
    """Entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Submit transactions from CSV to API")
    parser.add_argument(
        "--api",
        dest="api_base_url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--csv",
        dest="csv_path",
        default=str(Path(__file__).parent.parent / "transactions_mock_1000_for_participants.csv"),
        help="Path to CSV file",
    )
    parser.add_argument(
        "--batch-size",
        dest="batch_size",
        type=int,
        default=10,
        help="Number of transactions per batch (default: 10)",
    )
    parser.add_argument(
        "--delay",
        dest="delay",
        type=float,
        default=2.0,
        help="Delay between batches in seconds (default: 2.0)",
    )

    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return
    
    # Initialize simulator
    simulator = TransactionSimulator(api_base_url="http://127.0.0.1:8000")
    
    # Load only first 5 transactions
    all_transactions = simulator.load_transactions(str(csv_path))
    first_5_transactions = all_transactions[:50]
    
    logger.info(f"Submitting first 50 transactions with 1s intervals...")
    
    submitted_count = 0
    failed_count = 0
    
    for i, transaction in enumerate(first_5_transactions, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"Transaction {i}/50:")
        logger.info(f"{'='*60}")
        
        task_id = simulator.submit_transaction(transaction)
        if task_id:
            submitted_count += 1
        else:
            failed_count += 1
        
        # Wait 10 seconds before next transaction (except after the last one)
        if i < len(first_5_transactions):
            logger.info(f"⏳ Waiting 10 seconds before next transaction...")
            time.sleep(1)
    
    logger.info("\n" + "="*60)
    logger.info(f"Simulation complete!")
    logger.info(f"Submitted: {submitted_count}")
    logger.info(f"Failed: {failed_count}")
    logger.info("="*60)

if __name__ == "__main__":
    main()
