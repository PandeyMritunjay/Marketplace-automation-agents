"""
Support Lead - Main Entry Point

Triages support emails, classifies intent, drafts responses,
and provides morning briefing to Slack.

Usage:
    # Morning batch processing
    python -m lighthouse.main.support_lead --mode batch
    
    # Real-time processing (continuously polls for new emails)
    python -m lighthouse.main.support_lead --mode realtime
    
    # Process a specific email (for testing)
    python -m lighthouse.main.support_lead --email-body "Where's my payout?" --email-from "mritunjaypandey0429@gmail.com" --email-subject "Payout inquiry"
"""
import argparse
import logging
import time
import json
from lighthouse.agents.support_lead import SupportLead
from lighthouse.integrations.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Support Lead Agent")
    parser.add_argument("--mode", type=str, choices=["batch", "realtime"], help="Processing mode")
    parser.add_argument("--init-db", action="store_true", help="Initialize database schema")
    parser.add_argument("--email-body", type=str, help="Email body text (for testing)")
    parser.add_argument("--email-from", type=str, help="Sender email address (for testing)")
    parser.add_argument("--email-subject", type=str, help="Email subject (for testing)")
    
    args = parser.parse_args()
    
    if args.init_db:
        logger.info("Initializing database schema...")
        init_db()
        logger.info("Database initialized successfully")
        return
    
    # Handle single email testing
    if args.email_body and args.email_from:
        agent = SupportLead()
        result = agent._test_single_email(
            body=args.email_body,
            from_email=args.email_from,
            subject=args.email_subject or "No subject"
        )
        print("\n" + "="*80)
        print("SUPPORT LEAD OUTPUT (JSON):")
        print("="*80)
        print(json.dumps(result, indent=2))
        print("="*80 + "\n")
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
