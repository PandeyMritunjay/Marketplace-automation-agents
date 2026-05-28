"""
Support Lead - Main Entry Point

Triages support emails, classifies intent, drafts responses,
and provides morning briefing to Slack.

Usage:
    # Morning batch processing
    python -m lighthouse.main.support_lead --mode batch
    
    # Real-time processing (continuously polls for new emails)
    python -m lighthouse.main.support_lead --mode realtime
"""
import argparse
import logging
import time
from lighthouse.agents.support_lead import SupportLead
from lighthouse.integrations.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Support Lead Agent")
    parser.add_argument("--mode", type=str, choices=["batch", "realtime"], default="batch", help="Processing mode")
    parser.add_argument("--init-db", action="store_true", help="Initialize database schema")
    
    args = parser.parse_args()
    
    if args.init_db:
        logger.info("Initializing database schema...")
        init_db()
        logger.info("Database initialized successfully")
        return
    
    agent = SupportLead()
    
    if args.mode == "batch":
        logger.info("Running overnight batch processing...")
        result = agent.process_overnight_batch()
        logger.info(f"Batch processing complete: {result}")
    
    elif args.mode == "realtime":
        logger.info("Starting real-time email processing...")
        while True:
            try:
                # In production, this would poll Gmail for new emails
                # For now, we'll just run batch every 5 minutes
                result = agent.process_overnight_batch()
                logger.info(f"Processing cycle complete: {result}")
                time.sleep(300)  # 5 minutes
            except KeyboardInterrupt:
                logger.info("Stopping real-time processing...")
                break
            except Exception as e:
                logger.error(f"Error in real-time processing: {e}")
                time.sleep(60)


if __name__ == "__main__":
    main()
