"""
External Rules Ingestion Cron Job

Scheduled task to run regulatory crawlers and ingest external rules.
Run daily via cron: 0 2 * * * python cron/external_rules_ingestion.py
"""

import logging
import asyncio
from datetime import datetime

from db.database import SessionLocal
from crawlers.hkma import HKMACrawler
from crawlers.mas import MASCrawler
from crawlers.finma import FINMACrawler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_all_crawlers():
    """Run all regulatory crawlers and ingest rules"""
    logger.info("="*60)
    logger.info("Starting external rules ingestion job")
    logger.info(f"Timestamp: {datetime.utcnow().isoformat()}")
    logger.info("="*60)
    
    db = SessionLocal()
    
    try:
        total_saved = 0
        
        # HKMA
        logger.info("\n[1/3] Running HKMA crawler...")
        hkma_crawler = HKMACrawler()
        hkma_circulars = await hkma_crawler.crawl()
        hkma_saved = hkma_crawler.save_to_db(hkma_circulars, db)
        total_saved += hkma_saved
        logger.info(f"HKMA: {hkma_saved} new rules ingested")
        
        # MAS
        logger.info("\n[2/3] Running MAS crawler...")
        mas_crawler = MASCrawler()
        mas_circulars = await mas_crawler.crawl()
        # Save to DB (similar to HKMA)
        logger.info(f"MAS: Placeholder - crawler implemented")
        
        # FINMA
        logger.info("\n[3/3] Running FINMA crawler...")
        finma_crawler = FINMACrawler()
        finma_circulars = await finma_crawler.crawl()
        # Save to DB (similar to HKMA)
        logger.info(f"FINMA: Placeholder - crawler implemented")
        
        logger.info("\n" + "="*60)
        logger.info(f"Ingestion job complete: {total_saved} new rules saved")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Error in ingestion job: {str(e)}", exc_info=True)
    
    finally:
        db.close()


def main():
    """Entry point for cron job"""
    asyncio.run(run_all_crawlers())


if __name__ == "__main__":
    main()
