from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .base import Base


class SenderType(str, enum.Enum):
    BUYER = "buyer"
    SELLER = "seller"
    UNKNOWN = "unknown"


class TicketCategory(str, enum.Enum):
    ORDER_STATUS = "order_status"
    REFUND_RETURN = "refund_return"
    ACCOUNT_PASSWORD = "account_password"
    SELLER_ONBOARDING = "seller_onboarding"
    PAYOUT_PAYMENT = "payout_payment"
    PRODUCT_LISTING = "product_listing"
    COMPLAINT_ESCALATION = "complaint_escalation"
    OTHER = "other"


class TicketPriority(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TicketStatus(str, enum.Enum):
    NEW = "new"
    DRAFTED = "drafted"
    APPROVED = "approved"
    SENT = "sent"
    RESOLVED = "resolved"


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    
    id = Column(Integer, primary_key=True)
    source_email_id = Column(String(255), unique=True)  # Gmail message ID
    sender_type = Column(Enum(SenderType), nullable=False)
    sender_id = Column(Integer)  # Foreign key to buyer/seller if known
    sender_email = Column(String(255), nullable=False)
    raw_text = Column(Text, nullable=False)
    category = Column(Enum(TicketCategory), nullable=False)
    priority = Column(Enum(TicketPriority), nullable=False)
    classification_confidence = Column(Float, default=0.0)
    status = Column(Enum(TicketStatus), nullable=False, default=TicketStatus.NEW)
    
    # Agent outputs
    agent_draft = Column(Text)
    human_response = Column(Text)
    
    # Routing
    routed_to_dispute = Column(Boolean, default=False)
    dispute_id = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)
    
    def __repr__(self):
        return f"<SupportTicket(id={self.id}, category={self.category}, priority={self.priority})>"
