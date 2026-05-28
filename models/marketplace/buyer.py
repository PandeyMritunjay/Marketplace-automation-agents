from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Buyer(Base):
    __tablename__ = "buyers"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    total_orders = Column(Integer, default=0)
    dispute_history = Column(String(2000))  # JSON string of dispute history
    
    def __repr__(self):
        return f"<Buyer(id={self.id}, name={self.name}, email={self.email})>"
