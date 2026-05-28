"""
Dispute Handler - Main Entry Point

Processes buyer complaints, applies policy rules, drafts resolution messages,
and sends them to Slack for human review.

Usage:
    python -m lighthouse.main.dispute_handler --complaint "I ordered a vase 12 days ago and never got it" --buyer-email "buyer@example.com"
"""
import argparse
import logging
from lighthouse.agents.dispute_handler import DisputeHandler
from lighthouse.integrations.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Dispute Handler Agent")
    parser.add_argument("--complaint", type=str, help="Buyer complaint text")
    parser.add_argument("--buyer-email", type=str, help="Buyer's email address")
    parser.add_argument("--init-db", action="store_true", help="Initialize database schema")
    
    args = parser.parse_args()
    
    if args.init_db:
        logger.info("Initializing database schema...")
        init_db()
        logger.info("Database initialized successfully")
        return
    
    if not args.complaint or not args.buyer_email:
        logger.error("Both --complaint and --buyer-email are required")
        return
    
    handler = DisputeHandler()
    result = handler.process_complaint(args.complaint, args.buyer_email)
    
    if result:
        logger.info(f"Dispute processed successfully: {result}")
    else:
        logger.error("Failed to process dispute")


if __name__ == "__main__":
    main()
