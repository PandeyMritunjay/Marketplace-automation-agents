from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, Float, ForeignKey, Boolean
from datetime import datetime
import enum
from .base import Base


class AlertType(str, enum.Enum):
    PAYOUT_PENDING = "payout_pending"
    PAYOUT_FAILED = "payout_failed"
    UNFULFILLED_ORDER = "unfulfilled_order"
    SELLER_INACTIVE = "seller_inactive"
    LISTING_INCOMPLETE = "listing_incomplete"
    ONBOARDING_STUCK = "onboarding_stuck"
    PAYMENT_PROCESSOR_ALERT = "payment_processor_alert"
    OTHER = "other"


class AlertSeverity(str, enum.Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class OperationalAlert(Base):
    __tablename__ = "operational_alerts"
    
    id = Column(Integer, primary_key=True)
    alert_type = Column(Enum(AlertType), nullable=False)
    severity = Column(Enum(AlertSeverity), nullable=False)
    status = Column(Enum(AlertStatus), nullable=False, default=AlertStatus.OPEN)
    
    # Entity references (no FK constraints - marketplace tables are in separate database)
    seller_id = Column(Integer)
    order_id = Column(Integer)
    payout_id = Column(Integer)
    listing_id = Column(Integer)
    
    # Alert details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    metric_value = Column(Float)  # e.g., days pending, amount
    threshold = Column(Float)  # e.g., 7 days, $500
    
    # Agent outputs
    suggested_action = Column(Text)
    draft_communication = Column(Text)
    
    # Human action
    human_action_taken = Column(String(255))
    human_skipped = Column(Boolean, default=False)
    useful_feedback = Column(Boolean)  # 👍/👎 feedback
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    actioned_at = Column(DateTime)
    resolved_at = Column(DateTime)
    
    def __repr__(self):
        return f"<OperationalAlert(id={self.id}, type={self.alert_type}, severity={self.severity})>"
