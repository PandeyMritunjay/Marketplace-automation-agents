from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text, ARRAY, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class ListingStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    sold = "sold"
    flagged = "flagged"


class Listing(Base):
    __tablename__ = "listings"
    
    id = Column(Integer, primary_key=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    photos = Column(JSON)  # JSON array of photo URLs (MySQL compatible)
    category = Column(String(100))
    status = Column(Enum(ListingStatus), nullable=False, default=ListingStatus.active)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships removed - marketplace is read-only
    
    def __repr__(self):
        return f"<Listing(id={self.id}, title={self.title}, price={self.price})>"
