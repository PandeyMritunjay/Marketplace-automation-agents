from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, Float, Boolean
from datetime import datetime
import enum
from .base import Base


class AgentType(str, enum.Enum):
    DISPUTE_HANDLER = "dispute_handler"
    SUPPORT_LEAD = "support_lead"
    OPERATOR = "operator"


class ActionType(str, enum.Enum):
    DRAFT_CREATED = "draft_created"
    DRAFT_APPROVED = "draft_approved"
    DRAFT_EDITED = "draft_edited"
    DRAFT_OVERRIDDEN = "draft_overridden"
    ALERT_CREATED = "alert_created"
    ALERT_ACTIONED = "alert_actioned"
    ALERT_DISMISSED = "alert_dismissed"
    CLASSIFICATION = "classification"
    POLICY_MATCH = "policy_match"
    ERROR = "error"


class AgentAction(Base):
    __tablename__ = "agent_actions"
    
    id = Column(Integer, primary_key=True)
    agent_type = Column(Enum(AgentType), nullable=False)
    action_type = Column(Enum(ActionType), nullable=False)
    
    # Entity reference
    entity_type = Column(String(50))  # dispute, support_ticket, operational_alert
    entity_id = Column(Integer)
    
    # Action details
    description = Column(Text)
    confidence_score = Column(Float)
    
    # Human feedback
    human_feedback = Column(String(255))
    was_useful = Column(Boolean)
    
    # Performance metrics
    processing_time_ms = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<AgentAction(id={self.id}, agent={self.agent_type}, action={self.action_type})>"
