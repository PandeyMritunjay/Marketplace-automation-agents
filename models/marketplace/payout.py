from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class PayoutStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Payout(Base):
    __tablename__ = "payouts"
    
    id = Column(Integer, primary_key=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(Enum(PayoutStatus), nullable=False, default=PayoutStatus.pending)
    initiated_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    
    # Relationships removed - marketplace is read-only
    
    def __repr__(self):
        return f"<Payout(id={self.id}, amount={self.amount}, status={self.status})>"
