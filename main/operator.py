"""
Operator - Main Entry Point

Proactively monitors operational health, surfaces issues before they become tickets,
and sends daily briefing to Slack.

Usage:
    python -m lighthouse.main.operator
"""
import argparse
import logging
from lighthouse.agents.operator import Operator
from lighthouse.integrations.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Operator Agent")
    parser.add_argument("--init-db", action="store_true", help="Initialize database schema")
    
    args = parser.parse_args()
    
    if args.init_db:
        logger.info("Initializing database schema...")
        init_db()
        logger.info("Database initialized successfully")
        return
    
    logger.info("Running daily operational health check...")
    agent = Operator()
    result = agent.run_daily_health_check()
    logger.info(f"Health check complete: {result}")


if __name__ == "__main__":
    main()
