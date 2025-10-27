"""
ROMS V2 - Automated Order Management System
Main FastAPI Application
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

# Import database
from database.database import init_db, close_db

# Import routers
from api import webhooks, orders

# Import queue
from services.webhook_queue import webhook_queue

load_dotenv()

# Configuration
API_HOST = os.getenv("API_V2_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_V2_PORT", 8001))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3001").split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager
    Runs on startup and shutdown
    """
    # Startup
    print("🚀 Starting ROMS V2 Backend...")
    
    # Initialize database
    await init_db()
    
    # Start webhook queue workers
    await webhook_queue.start()
    print(f"⚡ Webhook queue started with {webhook_queue.max_workers} workers")
    
    # Start background tasks (scheduler not yet implemented)
    # if os.getenv("ENABLE_SCHEDULER", "true").lower() == "true":
    #     from tasks.scheduler import start_scheduler
    #     start_scheduler()
    #     print("⏰ Scheduler started")
    
    print("✅ ROMS V2 Backend is ready!")
    print(f"📡 API running on http://{API_HOST}:{API_PORT}")
    print(f"📚 Docs available at http://{API_HOST}:{API_PORT}/docs")
    print(f"🎯 Webhook queue: {webhook_queue.max_workers} workers, {webhook_queue.queue.maxsize} buffer")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down ROMS V2 Backend...")
    print("⏳ Stopping webhook queue (processing remaining messages)...")
    await webhook_queue.stop()
    await close_db()
    print("✅ Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="ROMS V2 API",
    description="Automated Order Management System with Webhooks, Email Scraping, and Web Scraping",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# Health Check Endpoints
# ============================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ROMS V2 - Automated Order Management System",
        "version": "2.0.0",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "features": {
            "webhooks": os.getenv("ENABLE_WEBHOOKS", "true") == "true",
            "email_scraping": os.getenv("ENABLE_EMAIL_SCRAPING", "true") == "true",
            "web_scraping": os.getenv("ENABLE_WEB_SCRAPING", "true") == "true",
            "realtime_ws": os.getenv("ENABLE_REALTIME_WEBSOCKET", "true") == "true",
        }
    }


# ============================================
# WebSocket for Real-Time Updates
# ============================================

class ConnectionManager:
    """Manage WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"❌ WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error broadcasting to WebSocket: {e}")


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time order updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            # Echo back or process
            await websocket.send_json({"type": "ack", "message": "received"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ============================================
# API Routers
# ============================================

app.include_router(webhooks.router, prefix="/api/v2/webhooks", tags=["Webhooks"])
app.include_router(orders.router, prefix="/api/v2/orders", tags=["Orders"])
# app.include_router(analytics.router, prefix="/api/v2/analytics", tags=["Analytics"])
# app.include_router(email_sync.router, prefix="/api/v2/email-sync", tags=["Email Sync"])
# app.include_router(scraping.router, prefix="/api/v2/scraping", tags=["Web Scraping"])


# ============================================
# Run the application
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=os.getenv("API_V2_RELOAD", "true").lower() == "true",
    )

