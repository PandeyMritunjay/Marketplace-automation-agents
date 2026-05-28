from pydantic import BaseSettings, Field
from typing import List
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    # Database
    marketplace_db_url: str = Field(default="")
    agent_db_url: str = Field(default="")
    
    # OpenAI
    openai_api_key: str = Field(default="")
    
    # Slack
    slack_bot_token: str = Field(default="")
    slack_signing_secret: str = Field(default="")
    slack_channel_disputes: str = Field(default="#disputes")
    slack_channel_support: str = Field(default="#support-queue")
    slack_channel_ops: str = Field(default="#ops-daily")
    
    # Gmail
    gmail_credentials_path: str = Field(default="credentials.json")
    gmail_token_path: str = Field(default="token.json")
    gmail_support_email: str = Field(default="")
    
    # Dispute Handler
    dispute_auto_refund_threshold: float = Field(default=200.0)
    dispute_high_confidence_threshold: float = Field(default=0.85)
    dispute_medium_confidence_threshold: float = Field(default=0.70)
    
    # Support Lead
    support_batch_approve_enabled: bool = Field(default=True)
    support_keyword_override: str = Field(
        default="lawyer,chargeback,leaving the platform,fraud,missing payment,payout,legal"
    )
    
    # Operator
    operator_payout_pending_days: int = Field(default=7)
    operator_unfulfilled_days: int = Field(default=5)
    operator_inactive_days: int = Field(default=14)
    
    # Logging
    log_level: str = Field(default="INFO")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Override with environment variables if they exist
        self.marketplace_db_url = os.getenv("MARKETPLACE_DB_URL", self.marketplace_db_url)
        self.agent_db_url = os.getenv("AGENT_DB_URL", self.agent_db_url)
        self.openai_api_key = os.getenv("OPENAI_API_KEY", self.openai_api_key)
        self.slack_bot_token = os.getenv("SLACK_BOT_TOKEN", self.slack_bot_token)
        self.slack_signing_secret = os.getenv("SLACK_SIGNING_SECRET", self.slack_signing_secret)
        self.slack_channel_disputes = os.getenv("SLACK_CHANNEL_DISPUTES", self.slack_channel_disputes)
        self.slack_channel_support = os.getenv("SLACK_CHANNEL_SUPPORT", self.slack_channel_support)
        self.slack_channel_ops = os.getenv("SLACK_CHANNEL_OPS", self.slack_channel_ops)
        self.gmail_credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH", self.gmail_credentials_path)
        self.gmail_token_path = os.getenv("GMAIL_TOKEN_PATH", self.gmail_token_path)
        self.gmail_support_email = os.getenv("GMAIL_SUPPORT_EMAIL", self.gmail_support_email)
        self.dispute_auto_refund_threshold = float(os.getenv("DISPUTE_AUTO_REFUND_THRESHOLD", self.dispute_auto_refund_threshold))
        self.dispute_high_confidence_threshold = float(os.getenv("DISPUTE_HIGH_CONFIDENCE_THRESHOLD", self.dispute_high_confidence_threshold))
        self.dispute_medium_confidence_threshold = float(os.getenv("DISPUTE_MEDIUM_CONFIDENCE_THRESHOLD", self.dispute_medium_confidence_threshold))
        self.support_batch_approve_enabled = os.getenv("SUPPORT_BATCH_APPROVE_ENABLED", str(self.support_batch_approve_enabled)).lower() == "true"
        self.support_keyword_override = os.getenv("SUPPORT_KEYWORD_OVERRIDE", self.support_keyword_override)
        self.operator_payout_pending_days = int(os.getenv("OPERATOR_PAYOUT_PENDING_DAYS", self.operator_payout_pending_days))
        self.operator_unfulfilled_days = int(os.getenv("OPERATOR_UNFULFILLED_DAYS", self.operator_unfulfilled_days))
        self.operator_inactive_days = int(os.getenv("OPERATOR_INACTIVE_DAYS", self.operator_inactive_days))
        self.log_level = os.getenv("LOG_LEVEL", self.log_level)
    
    @property
    def support_keywords(self) -> List[str]:
        return [k.strip() for k in self.support_keyword_override.split(",")]


settings = Settings()
