import asyncio
import json
from typing import Dict, List
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.sheet_subscribers: Dict[str, List[WebSocket]] = {}
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """Connect a new WebSocket client with its unique client_id"""
        await websocket.accept()
        
        # Clean up any existing connection with this client_id
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].close()
            except Exception:
                pass
            
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket connected for client {client_id}. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket, client_id: str):
        """Disconnect a WebSocket client and clean up its connections"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        logger.info(f"WebSocket disconnected for client {client_id}. Total connections: {len(self.active_connections)}")

    def subscribe_to_sheet(self, websocket: WebSocket, sheet_url: str):
        """Subscribe a websocket connection to updates for a specific sheet"""
        if sheet_url not in self.sheet_subscribers:
            self.sheet_subscribers[sheet_url] = []
        
        if websocket not in self.sheet_subscribers[sheet_url]:
            self.sheet_subscribers[sheet_url].append(websocket)
            logger.info(f"WebSocket subscribed to sheet {sheet_url[:50]}... Total subscribers: {len(self.sheet_subscribers[sheet_url])}")

    def unsubscribe_from_sheet(self, websocket: WebSocket, sheet_url: str):
        """Unsubscribe a websocket connection from a specific sheet"""
        if sheet_url in self.sheet_subscribers and websocket in self.sheet_subscribers[sheet_url]:
            self.sheet_subscribers[sheet_url].remove(websocket)
            logger.info(f"WebSocket unsubscribed from sheet {sheet_url[:50]}... Remaining subscribers: {len(self.sheet_subscribers[sheet_url])}")
            
            # Clean up empty subscriber lists
            if not self.sheet_subscribers[sheet_url]:
                del self.sheet_subscribers[sheet_url]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def broadcast_to_sheet_subscribers(self, message: dict, sheet_url: str):
        """Broadcast updates to all clients subscribed to a specific sheet"""
        if sheet_url not in self.sheet_subscribers:
            return
        
        try:
            message_str = json.dumps(message)
            logger.debug(f"Broadcasting WebSocket message: {message_str}")
        except Exception as e:
            logger.error(f"Failed to serialize WebSocket message: {e}")
            return
        
        disconnected_websockets = []
        
        for connection in self.sheet_subscribers[sheet_url]:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error broadcasting to websocket: {e}")
                disconnected_websockets.append(connection)
        
        # Clean up disconnected websockets
        for ws in disconnected_websockets:
            try:
                await ws.close()
            except Exception:
                pass
            if sheet_url in self.sheet_subscribers and ws in self.sheet_subscribers[sheet_url]:
                self.sheet_subscribers[sheet_url].remove(ws)

    async def broadcast_data_update(self, sheet_url: str, update_type: str, data: dict):
        """Broadcast data updates to subscribers"""
        message = {
            "type": "data_update",
            "update_type": update_type,  # "overview", "orders", "cell_edit"
            "data": data,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.broadcast_to_sheet_subscribers(message, sheet_url)

    async def broadcast_cell_edit(self, sheet_url: str, row_id: str, column: str, old_value: str, new_value: str, user_id: str = "system"):
        """Broadcast real-time cell edits"""
        message = {
            "type": "cell_edit",
            "row_id": row_id,
            "column": column,
            "old_value": old_value,
            "new_value": new_value,
            "user_id": user_id,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.broadcast_to_sheet_subscribers(message, sheet_url)

    async def cleanup_stale_connections(self):
        """Clean up any stale or dead connections"""
        for client_id, ws in list(self.active_connections.items()):
            try:
                await ws.send_text(json.dumps({"type": "ping"}))
            except Exception:
                logger.info(f"Removing stale connection for client {client_id}")
                self.disconnect(ws, client_id)

manager = WebSocketManager()