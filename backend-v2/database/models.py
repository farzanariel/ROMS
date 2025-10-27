"""
SQLAlchemy Database Models for ROMS V2
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


class OrderStatus(str, enum.Enum):
    """Order status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    VERIFIED = "verified"
    UNVERIFIED = "unverified"


class DataSource(str, enum.Enum):
    """Source of the order data"""
    WEBHOOK = "webhook"
    EMAIL = "email"
    WEB_SCRAPE = "web_scrape"
    MANUAL_UPLOAD = "manual_upload"
    DISCORD_BOT = "discord_bot"


class Order(Base):
    """Main orders table"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Order Information
    order_number = Column(String(255), unique=True, index=True, nullable=False)
    product = Column(String(500))
    price = Column(Float)
    total = Column(Float)
    commission = Column(Float)
    quantity = Column(Integer, default=1)
    
    # Customer Information
    email = Column(String(255), index=True)
    customer_name = Column(String(255))
    
    # Order Details
    profile = Column(String(255))
    proxy_list = Column(String(255))
    reference_number = Column(String(255))
    
    # Status & Tracking
    status = Column(Enum(OrderStatus), nullable=True, index=True)  # No default - filled in later
    tracking_number = Column(String(255), index=True)
    qty_received = Column(Integer, default=0)
    
    # Payment & Shipping
    payment_method = Column(String(255))
    shipping_address = Column(Text)
    shipping_method = Column(String(255))
    notes = Column(Text)
    
    # Dates
    order_date = Column(DateTime, index=True)
    order_time = Column(String(50))
    posted_date = Column(DateTime)
    shipped_date = Column(DateTime)
    delivered_date = Column(DateTime)
    
    # Metadata
    source = Column(Enum(DataSource), default=DataSource.MANUAL_UPLOAD, index=True)
    worksheet_name = Column(String(255))  # For backwards compatibility with Sheets
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    events = relationship("OrderEvent", back_populates="order", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Order {self.order_number} - {self.product}>"


class OrderEvent(Base):
    """Event log for order state changes"""
    __tablename__ = "order_events"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    
    event_type = Column(String(100), nullable=False, index=True)  # created, shipped, cancelled, etc.
    description = Column(Text)
    event_metadata = Column(Text)  # JSON string for additional data (renamed from 'metadata' - SQLAlchemy reserved word)
    
    source = Column(Enum(DataSource))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    order = relationship("Order", back_populates="events")
    
    def __repr__(self):
        return f"<OrderEvent {self.event_type} for Order {self.order_id}>"


class Product(Base):
    """Product catalog"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False)
    sku = Column(String(255), unique=True, index=True)
    price = Column(Float)
    category = Column(String(255), index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Product {self.name}>"


class Customer(Base):
    """Customer information"""
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255))
    
    # Stats
    total_orders = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Customer {self.email}>"


class WebhookLog(Base):
    """Audit log for incoming webhooks"""
    __tablename__ = "webhook_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    endpoint = Column(String(255), index=True)
    method = Column(String(10))
    headers = Column(Text)  # JSON string
    payload = Column(Text)  # JSON string
    
    status_code = Column(Integer)
    processed = Column(Boolean, default=False, index=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<WebhookLog {self.endpoint} - {self.status_code}>"


class EmailSyncLog(Base):
    """Log for email scraping operations"""
    __tablename__ = "email_sync_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    sync_started_at = Column(DateTime, index=True)
    sync_completed_at = Column(DateTime)
    
    emails_fetched = Column(Integer, default=0)
    emails_processed = Column(Integer, default=0)
    orders_created = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    
    status = Column(String(50), index=True)  # running, completed, failed
    error_message = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<EmailSync {self.sync_started_at} - {self.status}>"


class ScrapingJob(Base):
    """Web scraping job status"""
    __tablename__ = "scraping_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    job_type = Column(String(100), index=True)  # e.g., "product_data", "inventory"
    target_url = Column(String(500))
    
    started_at = Column(DateTime, index=True)
    completed_at = Column(DateTime)
    
    records_scraped = Column(Integer, default=0)
    status = Column(String(50), index=True)  # running, completed, failed
    error_message = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<ScrapingJob {self.job_type} - {self.status}>"


class Reconciliation(Base):
    """Credit card reconciliation records"""
    __tablename__ = "reconciliations"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True, index=True)
    
    reference_number = Column(String(255), index=True)
    transaction_date = Column(DateTime, index=True)
    amount = Column(Float)
    
    matched = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Reconciliation {self.reference_number}>"

