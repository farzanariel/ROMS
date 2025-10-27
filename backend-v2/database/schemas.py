"""
Pydantic schemas for data validation
"""
from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from typing import Optional
from database.models import OrderStatus, DataSource


class OrderBase(BaseModel):
    """Base order schema"""
    order_number: str = Field(..., description="Unique order number")
    product: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    total: Optional[float] = Field(None, ge=0)
    commission: Optional[float] = Field(None, ge=0)
    quantity: Optional[int] = Field(1, ge=1)
    
    email: Optional[EmailStr] = None
    customer_name: Optional[str] = None
    
    profile: Optional[str] = None
    proxy_list: Optional[str] = None
    reference_number: Optional[str] = None
    
    status: Optional[OrderStatus] = OrderStatus.PENDING
    tracking_number: Optional[str] = None
    qty_received: Optional[int] = Field(0, ge=0)
    
    payment_method: Optional[str] = None
    shipping_address: Optional[str] = None
    shipping_method: Optional[str] = None
    notes: Optional[str] = None
    
    order_date: Optional[datetime] = None
    order_time: Optional[str] = None
    posted_date: Optional[datetime] = None
    shipped_date: Optional[datetime] = None
    
    worksheet_name: Optional[str] = None
    
    @validator('price', 'total', 'commission')
    def round_currency(cls, v):
        """Round currency values to 2 decimal places"""
        if v is not None:
            return round(v, 2)
        return v


class OrderCreate(OrderBase):
    """Schema for creating a new order"""
    source: DataSource = DataSource.WEBHOOK


class OrderUpdate(BaseModel):
    """Schema for updating an order"""
    product: Optional[str] = None
    price: Optional[float] = None
    status: Optional[OrderStatus] = None
    tracking_number: Optional[str] = None
    qty_received: Optional[int] = None
    shipped_date: Optional[datetime] = None
    posted_date: Optional[datetime] = None


class OrderResponse(OrderBase):
    """Schema for order response"""
    id: int
    source: DataSource
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WebhookPayload(BaseModel):
    """
    Generic webhook payload
    Flexible structure to handle different webhook formats
    """
    # Required fields
    order_number: str
    
    # Optional fields that will be mapped to database columns
    product: Optional[str] = None
    product_name: Optional[str] = None  # Alternative field name
    item: Optional[str] = None  # Alternative field name
    
    price: Optional[float] = None
    unit_price: Optional[float] = None  # Alternative field name
    
    total: Optional[float] = None
    total_price: Optional[float] = None  # Alternative field name
    amount: Optional[float] = None  # Alternative field name
    
    commission: Optional[float] = None
    profit: Optional[float] = None  # Alternative field name
    
    quantity: Optional[int] = None
    qty: Optional[int] = None  # Alternative field name
    
    email: Optional[EmailStr] = None
    customer_email: Optional[EmailStr] = None  # Alternative field name
    
    customer_name: Optional[str] = None
    name: Optional[str] = None  # Alternative field name
    
    profile: Optional[str] = None
    proxy_list: Optional[str] = None
    proxy: Optional[str] = None  # Alternative field name
    
    reference: Optional[str] = None
    reference_number: Optional[str] = None
    
    status: Optional[str] = None
    order_status: Optional[str] = None  # Alternative field name
    
    tracking: Optional[str] = None
    tracking_number: Optional[str] = None
    shipment_id: Optional[str] = None  # Alternative field name
    
    order_date: Optional[datetime] = None
    created_at: Optional[datetime] = None  # Alternative field name
    date: Optional[datetime] = None  # Alternative field name
    
    order_time: Optional[str] = None
    
    # Payment and shipping
    payment_method: Optional[str] = None
    shipping_address: Optional[str] = None
    shipping_method: Optional[str] = None
    notes: Optional[str] = None
    
    # Allow any additional fields
    class Config:
        extra = "allow"


class WebhookResponse(BaseModel):
    """Response for webhook requests"""
    success: bool
    message: str
    order_id: Optional[int] = None
    order_number: Optional[str] = None


class OrderEventCreate(BaseModel):
    """Schema for creating an order event"""
    order_id: int
    event_type: str
    description: Optional[str] = None
    event_metadata: Optional[str] = None
    source: Optional[DataSource] = None

