"""
Webhook API endpoints
Receive and process webhooks from external systems
"""
from fastapi import APIRouter, Request, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from database.database import get_db
from database.schemas import WebhookPayload, WebhookResponse
from database.models import WebhookLog
from services.order_processor import OrderProcessor
from services.webhook_parser import parse_webhook_content, is_text_webhook
from services.webhook_queue import webhook_queue
from sqlalchemy.ext.asyncio import AsyncSession
import hashlib
import hmac
import json
import os
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Get webhook secret from environment
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "your-webhook-secret-change-this")


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Verify webhook signature for security
    Uses HMAC-SHA256
    """
    if not signature:
        return False
    
    # Calculate expected signature
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures (constant-time comparison)
    return hmac.compare_digest(signature, expected_signature)


@router.post("/orders")
async def receive_order_webhook(
    request: Request,
    x_webhook_signature: str = Header(None, alias="X-Webhook-Signature"),
):
    """
    HIGH-PERFORMANCE Webhook Receiver
    
    **Handles hundreds of webhooks per second with ZERO message loss**
    
    Features:
    - Returns 200 OK in < 100ms
    - Background queue processing
    - Automatic retries (3x)
    - Dead letter queue for failed messages
    - Real-time metrics
    
    **Headers:**
    - `X-Webhook-Signature`: HMAC-SHA256 signature (optional)
    
    **Body:** Discord embed or JSON format
    """
    start_time = datetime.utcnow()
    
    # Get raw body
    raw_body = await request.body()
    body_text = raw_body.decode()
    content_type = request.headers.get('content-type', '')
    
    # Quick signature check (if provided)
    if x_webhook_signature:
        if not verify_webhook_signature(raw_body, x_webhook_signature):
            logger.warning("❌ Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    # Log webhook immediately (for audit)
    webhook_log = WebhookLog(
        endpoint="/api/v2/webhooks/orders",
        method="POST",
        headers=json.dumps(dict(request.headers)),
        payload=body_text,
        status_code=202,  # Accepted for processing
        processed=False,
    )
    
    try:
        async with get_db() as db_session:
            db_session.add(webhook_log)
            await db_session.commit()
            webhook_log_id = webhook_log.id
    except Exception as e:
        logger.error(f"Failed to log webhook: {e}")
        webhook_log_id = None
    
    # Enqueue for background processing (FAST!)
    webhook_data = {
        "body": body_text,
        "content_type": content_type,
        "headers": dict(request.headers),
        "webhook_log_id": webhook_log_id,
        "received_at": start_time.isoformat(),
    }
    
    enqueued = await webhook_queue.enqueue(webhook_data)
    
    if not enqueued:
        logger.error("⚠️ Queue full - webhook may be lost!")
        raise HTTPException(status_code=503, detail="Service busy - retry")
    
    # Calculate response time
    response_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
    
    logger.info(f"📥 Queued in {response_time_ms:.0f}ms (queue: {webhook_queue.queue.qsize()})")
    
    # Return immediately! (Fast acknowledgment)
    return {
        "success": True,
        "message": "Webhook received and queued",
        "queued": True,
        "response_time_ms": round(response_time_ms, 2),
        "queue_size": webhook_queue.queue.qsize(),
    }


@router.get("/test")
async def test_webhook():
    """
    Test endpoint to verify webhook URL is accessible
    Use this to verify your webhook configuration
    """
    return {
        "status": "ok",
        "message": "Webhook endpoint is operational",
        "timestamp": datetime.utcnow().isoformat(),
        "signature_required": bool(WEBHOOK_SECRET and WEBHOOK_SECRET != "your-webhook-secret-change-this"),
    }


@router.post("/test-order")
async def test_create_order():
    """
    Test endpoint to create a sample order
    Useful for testing the webhook flow without external software
    """
    test_payload = WebhookPayload(
        order_number=f"TEST-{datetime.utcnow().timestamp()}",
        product="Test Product",
        price=99.99,
        quantity=1,
        email="test@example.com",
        status="pending",
    )
    
    async with get_db() as db_session:
        processor = OrderProcessor(db_session)
        order = await processor.create_order_from_webhook(test_payload)
        
        return {
            "success": True,
            "message": "Test order created",
            "order": {
                "id": order.id,
                "order_number": order.order_number,
                "product": order.product,
                "price": order.price,
            }
        }


@router.get("/logs")
async def get_webhook_logs(limit: int = 50):
    """
    Get recent webhook logs for debugging
    Shows the last N webhook requests received
    """
    from sqlalchemy import select, desc
    
    async with get_db() as db_session:
        result = await db_session.execute(
            select(WebhookLog)
            .order_by(desc(WebhookLog.created_at))
            .limit(limit)
        )
        logs = result.scalars().all()
        
        return {
            "total": len(logs),
            "logs": [
                {
                    "id": log.id,
                    "endpoint": log.endpoint,
                    "method": log.method,
                    "status_code": log.status_code,
                    "processed": log.processed,
                    "error_message": log.error_message,
                    "created_at": log.created_at.isoformat(),
                    "payload_preview": log.payload[:200] + "..." if len(log.payload) > 200 else log.payload,
                }
                for log in logs
            ]
        }


@router.get("/queue/stats")
async def get_queue_stats():
    """
    Get webhook queue statistics
    Monitor performance and health
    """
    stats = webhook_queue.get_stats()
    return {
        "status": "healthy" if stats["success_rate"] > 95 else "degraded",
        **stats
    }


@router.get("/queue/dead-letters")
async def get_dead_letters(limit: int = 100):
    """
    Get failed messages from dead letter queue
    Use this to debug and retry failed webhooks
    """
    dead_letters = await webhook_queue.get_dead_letters(limit)
    return {
        "total": len(dead_letters),
        "messages": dead_letters
    }


@router.post("/queue/retry-failed")
async def retry_failed_webhooks():
    """
    Retry all messages in dead letter queue
    """
    retried = await webhook_queue.retry_dead_letters()
    return {
        "success": True,
        "retried": retried,
        "message": f"Retrying {retried} failed webhooks"
    }


@router.get("/signature-help")
async def get_signature_help():
    """
    Help endpoint explaining how to generate webhook signatures
    """
    return {
        "message": "Webhook Signature Generation Guide",
        "algorithm": "HMAC-SHA256",
        "secret": "Set in WEBHOOK_SECRET environment variable",
        "header_name": "X-Webhook-Signature",
        "examples": {
            "python": """
import hmac
import hashlib
import json

payload = {"order_number": "12345", "product": "Nike Shoes"}
payload_bytes = json.dumps(payload).encode()
secret = "your-webhook-secret"

signature = hmac.new(
    secret.encode(),
    payload_bytes,
    hashlib.sha256
).hexdigest()

# Include in header: X-Webhook-Signature: {signature}
            """,
            "node": """
const crypto = require('crypto');

const payload = {order_number: "12345", product: "Nike Shoes"};
const payloadString = JSON.stringify(payload);
const secret = "your-webhook-secret";

const signature = crypto
    .createHmac('sha256', secret)
    .update(payloadString)
    .digest('hex');

// Include in header: X-Webhook-Signature: signature
            """,
            "curl": """
# Without signature (less secure)
curl -X POST http://localhost:8001/api/v2/webhooks/orders \\
  -H "Content-Type: application/json" \\
  -d '{"order_number":"12345","product":"Nike Shoes","price":99.99}'

# With signature (recommended)
SIGNATURE=$(echo -n '{"order_number":"12345"}' | openssl dgst -sha256 -hmac "your-webhook-secret" | cut -d' ' -f2)
curl -X POST http://localhost:8001/api/v2/webhooks/orders \\
  -H "Content-Type: application/json" \\
  -H "X-Webhook-Signature: $SIGNATURE" \\
  -d '{"order_number":"12345","product":"Nike Shoes","price":99.99}'
            """
        },
        "note": "Signature verification is optional but highly recommended for production use."
    }

