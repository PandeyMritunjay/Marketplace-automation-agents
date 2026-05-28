from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, Float, ForeignKey, Boolean
from datetime import datetime
import enum
from .base import Base


class DisputeType(str, enum.Enum):
    NON_DELIVERY = "non_delivery"
    ITEM_NOT_DESCRIBED = "item_not_described"
    DAMAGED_ITEM = "damaged_item"
    WRONG_ITEM = "wrong_item"
    LATE_SHIPMENT = "late_shipment"
    OTHER = "other"


class DisputeStatus(str, enum.Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    PENDING_SELLER_RESPONSE = "pending_seller_response"
    RESOLVED = "resolved"
    REFUNDED = "refunded"
    CLOSED = "closed"


class ConfidenceLevel(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Dispute(Base):
    __tablename__ = "disputes"
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, nullable=False)  # Reference to marketplace orders table (no FK constraint)
    buyer_id = Column(Integer, nullable=False)  # Reference to marketplace buyers table (no FK constraint)
    seller_id = Column(Integer, nullable=False)  # Reference to marketplace sellers table (no FK constraint)
    
    # Dispute details
    dispute_type = Column(Enum(DisputeType), nullable=False)
    complaint_text = Column(Text, nullable=False)
    buyer_sentiment = Column(String(50))  # angry, neutral, calm, etc.
    requested_resolution = Column(String(255))
    
    # Agent analysis
    confidence_level = Column(Enum(ConfidenceLevel), nullable=False)
    policy_match = Column(Text)  # Description of which policy applies
    complicating_factors = Column(Text)  # JSON array of complicating factors
    
    # Agent drafts
    seller_message_draft = Column(Text)
    buyer_message_draft = Column(Text)
    internal_summary = Column(Text)
    
    # Resolution
    status = Column(Enum(DisputeStatus), nullable=False, default=DisputeStatus.OPEN)
    resolution_action = Column(String(255))
    refund_amount = Column(Float)
    seller_response_deadline = Column(DateTime)
    
    # Human review
    human_approved = Column(Boolean, default=False)
    human_edited = Column(Boolean, default=False)
    human_override = Column(Boolean, default=False)
    override_reason = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)
    
    def __repr__(self):
        return f"<Dispute(id={self.id}, type={self.dispute_type}, status={self.status})>"
