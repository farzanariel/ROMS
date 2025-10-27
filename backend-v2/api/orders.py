"""
Orders API endpoints
CRUD operations for orders
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from database.database import get_db
from database.models import Order
from database.schemas import OrderResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional

router = APIRouter()


@router.get("")
async def get_orders(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in order_number, product, email"),
):
    """
    Get orders with pagination and filtering
    """
    async with get_db() as db:
        # Build query
        query = select(Order)
        
        # Apply filters
        if status:
            query = query.where(Order.status == status.upper())
        
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Order.order_number.ilike(search_pattern),
                    Order.product.ilike(search_pattern),
                    Order.email.ilike(search_pattern),
                )
            )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = query.order_by(Order.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        # Execute query
        result = await db.execute(query)
        orders = result.scalars().all()
        
        return {
            "orders": [
                {
                    "id": order.id,
                    "order_number": order.order_number,
                    "product": order.product,
                    "price": order.price,
                    "total": order.total,
                    "commission": order.commission,
                    "quantity": order.quantity,
                    "email": order.email,
                    "customer_name": order.customer_name,
                    "profile": order.profile,
                    "proxy_list": order.proxy_list,
                    "reference_number": order.reference_number,
                    "status": order.status.value if order.status else None,
                    "tracking_number": order.tracking_number,
                    "qty_received": order.qty_received,
                    "payment_method": order.payment_method,
                    "shipping_address": order.shipping_address,
                    "shipping_method": order.shipping_method,
                    "notes": order.notes,
                    "order_date": order.order_date.isoformat() if order.order_date else None,
                    "order_time": order.order_time,
                    "posted_date": order.posted_date.isoformat() if order.posted_date else None,
                    "shipped_date": order.shipped_date.isoformat() if order.shipped_date else None,
                    "delivered_date": order.delivered_date.isoformat() if order.delivered_date else None,
                    "source": order.source.value if order.source else None,
                    "worksheet_name": order.worksheet_name,
                    "created_at": order.created_at.isoformat(),
                    "updated_at": order.updated_at.isoformat(),
                }
                for order in orders
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_next": (page * page_size) < total,
            "has_previous": page > 1,
        }


@router.get("/{order_id}")
async def get_order(order_id: int):
    """
    Get a single order by ID
    """
    async with get_db() as db:
        result = await db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        return {
            "id": order.id,
            "order_number": order.order_number,
            "product": order.product,
            "price": order.price,
            "total": order.total,
            "commission": order.commission,
            "quantity": order.quantity,
            "email": order.email,
            "customer_name": order.customer_name,
            "profile": order.profile,
            "proxy_list": order.proxy_list,
            "reference_number": order.reference_number,
            "status": order.status.value if order.status else None,
            "tracking_number": order.tracking_number,
            "qty_received": order.qty_received,
            "payment_method": order.payment_method,
            "shipping_address": order.shipping_address,
            "shipping_method": order.shipping_method,
            "notes": order.notes,
            "order_date": order.order_date.isoformat() if order.order_date else None,
            "order_time": order.order_time,
            "posted_date": order.posted_date.isoformat() if order.posted_date else None,
            "shipped_date": order.shipped_date.isoformat() if order.shipped_date else None,
            "delivered_date": order.delivered_date.isoformat() if order.delivered_date else None,
            "source": order.source.value if order.source else None,
            "worksheet_name": order.worksheet_name,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
        }

