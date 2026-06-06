from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
from .base import Base
from datetime import datetime
import enum


class SellerTier(str, enum.Enum):
    top = "top"
    mid = "mid"
    low = "low"


class SellerStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"
    inactive = "inactive"


class Seller(Base):
    __tablename__ = "sellers"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    tier = Column(Enum(SellerTier), nullable=False, default=SellerTier.low)
    status = Column(Enum(SellerStatus), nullable=False, default=SellerStatus.active)
    total_gmv = Column(Float, default=0.0)
    total_orders = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    bank_details = Column(String(500))  # Encrypted in production
    signup_date = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    policies = Column(String(2000))  # JSON string of custom policies
    
    def __repr__(self):
        return f"<Seller(id={self.id}, name={self.name}, tier={self.tier})>"
