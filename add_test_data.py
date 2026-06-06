"""
Quick script to add test buyer data to marketplace database
"""
import sys
import os

# Add parent directory to path so we can import lighthouse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lighthouse.integrations.database import get_marketplace_db, init_db
from lighthouse.models.marketplace.buyer import Buyer
from lighthouse.models.marketplace.seller import Seller
from lighthouse.models.marketplace.order import Order
from datetime import datetime, timezone

def add_test_data():
    # First initialize database schema
    print("Initializing database schema...")
    init_db()
    print("Database schema initialized.")
    
    db = get_marketplace_db()
    
    try:
        # Add buyer
        buyer = db.query(Buyer).filter(Buyer.email == "mritunjayjan21@gmail.com").first()
        if not buyer:
            buyer = Buyer(
                name="Mritunjay",
                email="mritunjayjan21@gmail.com",
                total_orders=5
            )
            db.add(buyer)
            print(f"Added buyer: {buyer.email}")
        else:
            print(f"Buyer already exists: {buyer.email}")
        
        # Add seller
        seller = db.query(Seller).filter(Seller.email == "mritunjay@thedatascientist.live").first()
        if not seller:
            seller = Seller(
                name="Mritunjay Store",
                email="mritunjay@thedatascientist.live",
                tier="mid",
                rating=4.5,
                total_orders=100,
                total_gmv=15000.0
            )
            db.add(seller)
            print(f"Added seller: {seller.email}")
        else:
            print(f"Seller already exists: {seller.email}")
        
        db.commit()
        
        # Add order for the buyer
        order = db.query(Order).filter(Order.buyer_id == buyer.id).first()
        if not order:
            order = Order(
                buyer_id=buyer.id,
                seller_id=seller.id,
                total=45.99,
                status="delivered",
                tracking_number=None,
                created_at=datetime.now(timezone.utc)
            )
            db.add(order)
            print(f"Added order #{order.id} for buyer {buyer.email}")
        else:
            print(f"Order already exists for buyer {buyer.email}")
        
        db.commit()
        print("\n✅ Test data added successfully!")
        print(f"Buyer ID: {buyer.id}")
        print(f"Seller ID: {seller.id}")
        print(f"Order ID: {order.id}")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_test_data()
