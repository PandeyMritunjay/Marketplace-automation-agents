from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class OrderStatus(str, enum.Enum):
    paid = "paid"
    shipped = "shipped"
    delivered = "delivered"
    disputed = "disputed"
    refunded = "refunded"
    cancelled = "cancelled"


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True)
    buyer_id = Column(Integer, ForeignKey("buyers.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=False)
    items = Column(Text)  # JSON string of order items
    total = Column(Float, nullable=False)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.paid)
    tracking_number = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    shipped_at = Column(DateTime)
    delivered_at = Column(DateTime)
    
    # Relationships removed - marketplace is read-only
    
    def __repr__(self):
        return f"<Order(id={self.id}, total={self.total}, status={self.status})>"
