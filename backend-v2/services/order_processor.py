"""
Order processing service
Handles business logic for creating and updating orders
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import Order, OrderEvent, DataSource
from database.schemas import OrderCreate, WebhookPayload
from datetime import datetime
from typing import Optional, Dict, Any
import json


def serialize_payload(payload: WebhookPayload) -> str:
    """Convert payload to JSON string, handling datetime objects"""
    payload_dict = payload.dict(exclude_none=True)
    # Convert datetime objects to ISO format strings
    for key, value in payload_dict.items():
        if isinstance(value, datetime):
            payload_dict[key] = value.isoformat()
    return json.dumps(payload_dict)


class OrderProcessor:
    """Process and store orders from various sources"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_order_from_webhook(self, payload: WebhookPayload) -> Order:
        """
        Create order from webhook payload
        Maps flexible field names to database columns
        """
        # Map webhook payload to order data
        order_data = self._map_webhook_to_order(payload)
        
        # Check if order already exists
        existing_order = await self._get_order_by_number(order_data["order_number"])
        
        if existing_order:
            # Update existing order
            return await self._update_existing_order(existing_order, order_data, payload)
        else:
            # Create new order
            return await self._create_new_order(order_data, payload)
    
    def _map_webhook_to_order(self, payload: WebhookPayload) -> Dict[str, Any]:
        """
        Map webhook payload fields to database columns
        Handles alternative field names
        """
        # Product name (try multiple field names)
        product = (
            payload.product or 
            payload.product_name or 
            payload.item or 
            "Unknown Product"
        )
        
        # Price (try multiple field names)
        price = (
            payload.price or 
            payload.unit_price or 
            0.0
        )
        
        # Total (try multiple field names - leave blank if not provided)
        total = (
            payload.total or 
            payload.total_price or 
            payload.amount
        )
        
        # Commission/Profit
        commission = (
            payload.commission or 
            payload.profit or 
            0.0
        )
        
        # Quantity
        quantity = (
            payload.quantity or 
            payload.qty or 
            1
        )
        
        # Email
        email = (
            payload.email or 
            payload.customer_email
        )
        
        # Customer name
        customer_name = (
            payload.customer_name or 
            payload.name
        )
        
        # Proxy
        proxy_list = (
            payload.proxy_list or 
            payload.proxy
        )
        
        # Reference number
        reference_number = (
            payload.reference or 
            payload.reference_number
        )
        
        # Status (leave blank if not provided - will be filled in later)
        status_str = payload.status or payload.order_status
        
        if status_str:
            # Map status string to enum
            status_map = {
                "pending": "pending",
                "processing": "processing",
                "shipped": "shipped",
                "delivered": "delivered",
                "cancelled": "cancelled",
                "refunded": "refunded",
                "verified": "verified",
                "unverified": "unverified",
            }
            status = status_map.get(status_str.lower(), None)
        else:
            status = None  # Leave blank if not in webhook
        
        # Tracking number
        tracking_number = (
            payload.tracking or 
            payload.tracking_number or 
            payload.shipment_id
        )
        
        # Order date
        order_date = (
            payload.order_date or 
            payload.created_at or 
            payload.date or 
            datetime.utcnow()
        )
        
        # Order time
        order_time = getattr(payload, 'order_time', None)
        
        # Payment and shipping details
        payment_method = getattr(payload, 'payment_method', None)
        shipping_address = getattr(payload, 'shipping_address', None)
        shipping_method = getattr(payload, 'shipping_method', None)
        notes = getattr(payload, 'notes', None)
        
        return {
            "order_number": payload.order_number,
            "product": product,
            "price": price,
            "total": total,
            "commission": commission,
            "quantity": quantity,
            "email": email,
            "customer_name": customer_name,
            "profile": payload.profile,
            "proxy_list": proxy_list,
            "reference_number": reference_number,
            "status": status,
            "tracking_number": tracking_number,
            "order_date": order_date,
            "order_time": order_time,
            "payment_method": payment_method,
            "shipping_address": shipping_address,
            "shipping_method": shipping_method,
            "notes": notes,
            "source": DataSource.WEBHOOK,
        }
    
    async def _get_order_by_number(self, order_number: str) -> Optional[Order]:
        """Get order by order number"""
        result = await self.db.execute(
            select(Order).where(Order.order_number == order_number)
        )
        return result.scalar_one_or_none()
    
    async def _create_new_order(self, order_data: Dict[str, Any], raw_payload: WebhookPayload) -> Order:
        """Create a new order in the database"""
        # Create order
        order = Order(**order_data)
        self.db.add(order)
        await self.db.flush()  # Get the order ID
        
        # Create order event
        event = OrderEvent(
            order_id=order.id,
            event_type="created",
            description=f"Order created from webhook",
            event_metadata=serialize_payload(raw_payload),
            source=DataSource.WEBHOOK,
        )
        self.db.add(event)
        
        await self.db.commit()
        await self.db.refresh(order)
        
        return order
    
    async def _update_existing_order(
        self, 
        order: Order, 
        new_data: Dict[str, Any],
        raw_payload: WebhookPayload
    ) -> Order:
        """Update existing order with new data from webhook"""
        # Track what changed
        changes = []
        
        # Update fields if they have new values
        for key, value in new_data.items():
            if key in ["order_number", "source"]:
                continue  # Don't update these
            
            if value is not None:
                old_value = getattr(order, key, None)
                if old_value != value:
                    setattr(order, key, value)
                    changes.append(f"{key}: {old_value} -> {value}")
        
        if changes:
            # Create update event
            event = OrderEvent(
                order_id=order.id,
                event_type="updated",
                description=f"Order updated from webhook. Changes: {', '.join(changes)}",
                event_metadata=serialize_payload(raw_payload),
                source=DataSource.WEBHOOK,
            )
            self.db.add(event)
        
        await self.db.commit()
        await self.db.refresh(order)
        
        return order
    
    async def get_order_by_id(self, order_id: int) -> Optional[Order]:
        """Get order by ID"""
        result = await self.db.execute(
            select(Order).where(Order.id == order_id)
        )
        return result.scalar_one_or_none()
    
    async def get_orders(
        self, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[str] = None
    ) -> list[Order]:
        """Get list of orders with pagination"""
        query = select(Order).order_by(Order.created_at.desc())
        
        if status:
            query = query.where(Order.status == status)
        
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()

