from fastapi import FastAPI, HTTPException, WebSocket, File, UploadFile, Form, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import os
import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from enum import Enum

# Import our new modules
from websocket_manager import manager
from sheet_operations import sheets_manager
from cache_manager import periodic_cache_cleanup, data_cache
from file_processing import parse_message, parse_csv, process_cancel_orders, process_tracking_upload, process_mark_received, process_reconcile_charges

class FileAction(str, Enum):
    UPLOAD_ORDERS = "upload_orders"
    CANCEL_ORDERS = "cancel_orders"
    UPLOAD_TRACKINGS = "upload_trackings"
    MARK_RECEIVED = "mark_received"
    RECONCILE_CHARGES = "reconcile_charges"

def apply_date_filter(df: pd.DataFrame, date_filter: Optional[str], start_date: Optional[str], end_date: Optional[str]) -> pd.DataFrame:
    """
    Apply date filtering to dataframe based on the Date column.
    This is the SINGLE SOURCE OF TRUTH for all date filtering across the application.
    
    Args:
        df: DataFrame to filter
        date_filter: Predefined filter (today, this_week, this_month, last_month, year_to_date, all_time, or YYYY-MM)
        start_date: Custom start date (YYYY-MM-DD format)
        end_date: Custom end date (YYYY-MM-DD format)
    
    Returns:
        Filtered DataFrame with only rows matching the date criteria
    """
    if df.empty:
        logger.info("📊 apply_date_filter: Empty DataFrame received, returning as-is")
        return df

    # STEP 1: Find the date column
    date_columns = ['Date', 'Order Date', 'Created', 'Posted Date']
    date_column = None
    for col in date_columns:
        if col in df.columns:
            date_column = col
            logger.info(f"✅ Found date column: '{date_column}'")
            break

    if not date_column:
        logger.warning(f"⚠️ No date column found in DataFrame. Available columns: {list(df.columns)}")
        return df

    # STEP 2: Convert date column to datetime (this is critical for accurate filtering)
    try:
        logger.info(f"🔄 Converting '{date_column}' column to datetime...")
        logger.info(f"📅 Sample values before conversion: {df[date_column].head(5).tolist()}")
        
        # Store original count for comparison
        original_count = len(df)
        
        # Convert to datetime with flexible parsing for multiple formats
        # Handles: 'YYYY-MM-DD', 'M/D/YYYY', 'Sun, 05 Oct 2025 17:28:02 -0600', etc.
        df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
        
        # Check for conversion issues
        invalid_dates = df[date_column].isna().sum()
        if invalid_dates > 0:
            logger.warning(f"⚠️ Found {invalid_dates} rows with invalid/missing dates (will be excluded)")
        
        # Remove rows with invalid dates (NaT values)
        df = df.dropna(subset=[date_column])
        removed_count = original_count - len(df)
        if removed_count > 0:
            logger.info(f"🗑️ Removed {removed_count} rows with invalid dates")
        
        if df.empty:
            logger.warning("⚠️ No valid dates found in DataFrame after conversion")
            return df
        
        # Log the date range we're working with
        min_date = df[date_column].min()
        max_date = df[date_column].max()
        logger.info(f"📊 Data date range: {min_date.date()} to {max_date.date()} ({len(df)} total rows)")
        
    except Exception as e:
        logger.error(f"❌ Error converting date column: {e}")
        return df

    # STEP 3: Determine the date range to filter
    try:
        # Use timezone-naive datetime for consistency
        now = datetime.now()
        today = now.date()
        start = None
        end = None
        
        # Handle different date filter options
        if date_filter == 'today':
            start = datetime.combine(today, datetime.min.time())
            end = datetime.combine(today, datetime.max.time())
            logger.info(f"📆 Filtering for TODAY: {start.date()}")

        elif date_filter == 'this_week':
            # Week starts on Monday (weekday 0), ends on Sunday (weekday 6)
            days_since_monday = today.weekday()
            start = datetime.combine(today - timedelta(days=days_since_monday), datetime.min.time())
            end = datetime.combine(today + timedelta(days=6-days_since_monday), datetime.max.time())
            logger.info(f"📆 Filtering for THIS WEEK: {start.date()} to {end.date()}")

        elif date_filter == 'this_month':
            # From 1st day of current month to last day of current month
            start = datetime.combine(today.replace(day=1), datetime.min.time())
            # Calculate last day of current month
            if today.month == 12:
                end = datetime.combine(today.replace(year=today.year+1, month=1, day=1), datetime.min.time()) - timedelta(seconds=1)
            else:
                end = datetime.combine(today.replace(month=today.month+1, day=1), datetime.min.time()) - timedelta(seconds=1)
            logger.info(f"📆 Filtering for THIS MONTH: {start.date()} to {end.date()}")

        elif date_filter == 'last_month':
            # From 1st day of last month to last day of last month
            if today.month == 1:
                last_month = 12
                last_year = today.year - 1
            else:
                last_month = today.month - 1
                last_year = today.year
            
            start = datetime.combine(datetime(last_year, last_month, 1).date(), datetime.min.time())
            # Calculate last day of last month
            if last_month == 12:
                end = datetime.combine(datetime(last_year+1, 1, 1).date(), datetime.min.time()) - timedelta(seconds=1)
            else:
                end = datetime.combine(datetime(last_year, last_month+1, 1).date(), datetime.min.time()) - timedelta(seconds=1)
            logger.info(f"📆 Filtering for LAST MONTH: {start.date()} to {end.date()}")

        elif date_filter == 'year_to_date':
            # From January 1st of current year to today
            start = datetime.combine(datetime(today.year, 1, 1).date(), datetime.min.time())
            end = datetime.combine(today, datetime.max.time())
            logger.info(f"📆 Filtering for YEAR TO DATE: {start.date()} to {end.date()}")

        elif date_filter == 'all_time' or date_filter is None:
            # No filtering - return all data
            logger.info("📆 No date filtering applied - showing ALL TIME")
            return df

        elif date_filter and len(date_filter) == 7 and date_filter[4] == '-':
            # Specific month filter (YYYY-MM format)
            try:
                year = int(date_filter[:4])
                month = int(date_filter[5:7])
                start = datetime.combine(datetime(year, month, 1).date(), datetime.min.time())
                # Calculate last day of specified month
                if month == 12:
                    end = datetime.combine(datetime(year+1, 1, 1).date(), datetime.min.time()) - timedelta(seconds=1)
                else:
                    end = datetime.combine(datetime(year, month+1, 1).date(), datetime.min.time()) - timedelta(seconds=1)
                logger.info(f"📆 Filtering for SPECIFIC MONTH: {year}-{month:02d} ({start.date()} to {end.date()})")
            except (ValueError, IndexError) as e:
                logger.warning(f"⚠️ Invalid month format '{date_filter}': {e}. Skipping filter.")
                return df

        elif start_date and end_date:
            # Custom date range
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                # Include the entire end date (up to 23:59:59.999999)
                end = datetime.combine(end.date(), datetime.max.time())
                logger.info(f"📆 Filtering for CUSTOM RANGE: {start.date()} to {end.date()}")
            except ValueError as e:
                logger.error(f"❌ Invalid custom date format. Expected YYYY-MM-DD. Error: {e}")
                return df
        
        # STEP 4: Apply the filter
        if start is not None and end is not None:
            before_count = len(df)
            # Create boolean mask for filtering
            mask = (df[date_column] >= start) & (df[date_column] <= end)
            df = df[mask]
            after_count = len(df)
            
            logger.info(f"✅ Date filter applied: {before_count} rows → {after_count} rows ({after_count/before_count*100:.1f}% retained)")
            
            if df.empty:
                logger.warning(f"⚠️ No rows found within date range {start.date()} to {end.date()}")
        
        return df
        
    except Exception as e:
        logger.error(f"❌ Unexpected error in date filtering: {e}", exc_info=True)
        # Return original dataframe on error to avoid data loss
        return df

def filter_pending_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Shared function to filter pending orders consistently"""
    if df.empty:
        return df
    
    # Find tracking number column (could be named differently)
    tracking_columns = ['Tracking Number', 'Tracking', 'Track Number', 'Track #', 'Tracking#']
    tracking_column = None
    for col in tracking_columns:
        if col in df.columns:
            tracking_column = col
            break
    
    if not tracking_column:
        logger.warning("No tracking number column found")
        return pd.DataFrame()
    
    # Filter for orders without tracking numbers
    # Check for empty, NaN, or whitespace-only values
    pending_mask = (
        df[tracking_column].isna() | 
        (df[tracking_column] == '') |
        (df[tracking_column].astype(str).str.strip() == '') |
        (df[tracking_column].astype(str).str.lower() == 'nan')
    )
    
    pending_orders = df[pending_mask].copy()
    logger.info(f"Found {len(pending_orders)} pending orders (no tracking in {tracking_column})")
    return pending_orders

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Background task for periodic data refresh
async def periodic_data_refresh():
    """Periodically fetch latest data and broadcast to all connected clients"""
    while True:
        try:
            # This will run every 2 minutes to check for external changes (reduced frequency)
            await asyncio.sleep(120)
            
            # For each sheet with active subscribers, fetch latest data
            for sheet_url in list(manager.sheet_subscribers.keys()):
                try:
                    df = await sheets_manager.get_all_data(sheet_url)
                    
                    # Calculate overview data
                    today = datetime.now().date()
                    total_orders = len(df)
                    total_revenue = df['Price'].apply(lambda x: float(str(x).replace('$', '').replace(',', '')) if x else 0).sum()
                    
                    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                    orders_today = len(df[df['Date'].dt.date == today]) if 'Date' in df.columns else 0
                    
                    pending_orders = len(df[
                        (df['Status'].str.upper() != 'VERIFIED') | 
                        (df['Tracking Number'].isna() | (df['Tracking Number'] == ''))
                    ])
                    
                    overview_data = {
                        "total_orders": total_orders,
                        "total_revenue": f"${total_revenue:,.2f}",
                        "orders_today": orders_today,
                        "pending_orders": pending_orders,
                        "last_updated": datetime.now().isoformat()
                    }
                    
                    # Broadcast update
                    await manager.broadcast_data_update(sheet_url, "overview", overview_data)
                    
                except Exception as e:
                    logger.error(f"Error in periodic refresh for sheet {sheet_url}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in periodic data refresh: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting Order Management Dashboard...")
    
    # Initialize Google Sheets connection
    try:
        if sheets_manager.client:
            logger.info("✅ Google Sheets connection verified")
        else:
            logger.error("❌ Google Sheets connection failed")
    except Exception as e:
        logger.error(f"❌ Google Sheets initialization error: {e}")
    
    # Start background tasks
    logger.info("Starting background tasks...")
    refresh_task = asyncio.create_task(periodic_data_refresh())
    cache_cleanup_task = asyncio.create_task(periodic_cache_cleanup())
    
    # Initial data sync - clear cache to force fresh data on startup
    logger.info("🔄 Clearing cache for fresh data on startup...")
    data_cache.clear_cache()
    
    yield
    
    # Shutdown
    logger.info("Stopping background tasks...")
    refresh_task.cancel()
    cache_cleanup_task.cancel()
    try:
        await refresh_task
        await cache_cleanup_task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="Order Management Dashboard", version="2.0.0", lifespan=lifespan)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class CellUpdateRequest(BaseModel):
    row_id: str
    column: str
    value: str
    
class RowUpdateRequest(BaseModel):
    row_id: str
    data: Dict[str, Any]

class NewOrderRequest(BaseModel):
    data: Dict[str, Any]



@app.get("/")
async def root():
    return {"message": "Order Management Dashboard API", "status": "running"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint with performance metrics"""
    try:
        # Get cache performance metrics
        cache_hit_rate = data_cache.get_hit_rate()
        cache_size = len(data_cache.cache)
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "google_sheets": "connected" if sheets_manager.client else "disconnected",
            "performance": {
                "cache_hit_rate": f"{cache_hit_rate:.1%}",
                "cache_entries": cache_size,
                "cache_hits": data_cache.cache_hits,
                "cache_misses": data_cache.cache_misses,
                "rate_limiter_max": "DISABLED",
                "concurrent_api_calls": 8  # Current semaphore limit
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "timestamp": datetime.now().isoformat(),
            "google_sheets": "disconnected",
            "error": str(e)
        }

@app.get("/api/performance")
async def get_performance_info():
    """Get performance information and recommendations based on current usage"""
    try:
        cache_hit_rate = data_cache.get_hit_rate()
        cache_size = len(data_cache.cache)
        
        # Calculate performance score
        performance_score = min(100, cache_hit_rate * 100)
        
        recommendations = []
        if cache_hit_rate < 0.7:
            recommendations.append("Consider increasing cache duration for better performance")
        if cache_size < 5:
            recommendations.append("Cache is warming up - performance will improve with usage")
        
        # Since quota usage is very low (0.4%), we can recommend more aggressive settings
        optimization_status = "OPTIMAL" if cache_hit_rate > 0.8 else "CAN_OPTIMIZE"
        
        return {
            "performance_score": f"{performance_score:.0f}%",
            "cache_statistics": {
                "hit_rate": f"{cache_hit_rate:.1%}",
                "total_entries": cache_size,
                "hits": data_cache.cache_hits,
                "misses": data_cache.cache_misses
            },
            "api_configuration": {
                "concurrent_requests": 8,  # Optimized for low quota usage
                "rate_limit": "DISABLED",
                "cache_duration_minutes": 10
            },
            "quota_analysis": {
                "current_usage": "Very Low (0.4%)",
                "optimization_status": optimization_status,
                "can_increase_concurrency": True,
                "recommended_concurrent_requests": "8-12"
            },
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/files/process")
async def process_uploaded_file(
    sheet_url: str = Form(...),
    action: FileAction = Form(...),
    worksheet_name: Optional[str] = Form(None),
    client_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Process an uploaded file for bulk operations.
    """
    if not sheets_manager.client:
        raise HTTPException(status_code=400, detail="Google Sheets not initialized. Please set a valid sheet URL.")

    # Log the parameters for debugging
    logger.info(f"Processing file with parameters: action={action}, worksheet_name={worksheet_name}, client_id={client_id}")
    
    content = await file.read()
    
    # Log file details for debugging
    logger.info(f"Processing file: {file.filename}, size: {len(content)} bytes")
    
    try:
        text_content = content.decode('utf-8')
        logger.info(f"Successfully decoded file as UTF-8")
    except UnicodeDecodeError:
        try:
            text_content = content.decode('latin-1')
            logger.info(f"Successfully decoded file as Latin-1")
        except UnicodeDecodeError:
            logger.error(f"Failed to decode file: {file.filename}")
            raise HTTPException(status_code=400, detail="Failed to decode file. Please ensure it's UTF-8 or Latin-1 encoded.")

    if not text_content.strip():
        logger.warning(f"File is empty: {file.filename}")
        return JSONResponse(status_code=400, content={"message": "File is empty."})
    
    # Log file content preview for debugging
    logger.info(f"File content preview: {text_content[:500]}...")
    logger.info(f"File content length: {len(text_content)}")
    
    # Parse file based on action type
    if action == FileAction.UPLOAD_ORDERS:
        # Upload orders uses the "Successful Checkout" format
        logger.info(f"File contains 'Successful Checkout': {'Successful Checkout' in text_content}")
        logger.info(f"File contains 'Product': {'Product' in text_content}")
        logger.info(f"File contains 'Order Number': {'Order Number' in text_content}")
        
        parsed_data = parse_message(text_content)
        logger.info(f"Parsed data result: {parsed_data}")

        if not parsed_data:
            return JSONResponse(status_code=400, content={
                "message": "Could not parse any data from the file. Expected format:\nProduct\n[Product Name]\nPrice\n$[Price]\nOrder Number\n[Order Number]\nEmail\n[Email]\nQuantity\n[Quantity]"
            })

        # Validate that we have at least some basic order data
        valid_orders = [order for order in parsed_data if order.get('Product') or order.get('Order Number')]
        if not valid_orders:
            return JSONResponse(status_code=400, content={
                "message": "No valid orders found. Expected format:\nProduct\n[Product Name]\nPrice\n$[Price]\nOrder Number\n[Order Number]\nEmail\n[Email]\nQuantity\n[Quantity]"
            })
    
    elif action == FileAction.CANCEL_ORDERS:
        # Cancel orders uses CSV with order numbers
        parsed_data = parse_csv(text_content)
        if not parsed_data:
            return JSONResponse(status_code=400, content={
                "message": "Could not parse CSV file. Please ensure it has a column with order numbers (e.g., 'Order Number', 'Order', or 'order_number')."
            })
        logger.info(f"Parsed {len(parsed_data)} rows from CSV for cancel orders")
        
    elif action == FileAction.UPLOAD_TRACKINGS:
        # Track orders uses CSV with order numbers and tracking numbers
        parsed_data = parse_csv(text_content)
        if not parsed_data:
            return JSONResponse(status_code=400, content={
                "message": "Could not parse CSV file. Please ensure it has columns for order numbers and tracking numbers."
            })
        logger.info(f"Parsed {len(parsed_data)} rows from CSV for tracking upload")
        
    elif action == FileAction.MARK_RECEIVED:
        # Mark received uses CSV with order numbers and optionally quantities
        parsed_data = parse_csv(text_content)
        if not parsed_data:
            return JSONResponse(status_code=400, content={
                "message": "Could not parse CSV file. Please ensure it has a column with order numbers."
            })
        logger.info(f"Parsed {len(parsed_data)} rows from CSV for mark received")
        
    elif action == FileAction.RECONCILE_CHARGES:
        # Reconcile charges uses CSV with order numbers
        parsed_data = parse_csv(text_content)
        if not parsed_data:
            return JSONResponse(status_code=400, content={
                "message": "Could not parse CSV file. Please ensure it has a column with order numbers."
            })
        logger.info(f"Parsed {len(parsed_data)} rows from CSV for reconcile charges")
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action specified.")

    async def progress_callback(current, total, message):
        logger.info(f"Progress callback called: {current}/{total} - {message}")
        logger.info(f"Active connections: {list(manager.active_connections.keys())}")
        logger.info(f"Looking for client_id: {client_id}")
        
        if client_id in manager.active_connections:
            websocket = manager.active_connections[client_id]
            try:
                progress_message = {
                    "type": "progress",
                    "current": current,
                    "total": total,
                    "message": str(message),  # Ensure message is a string
                }
                await websocket.send_json(progress_message)
                logger.info(f"✅ Successfully sent progress update: {progress_message}")
            except Exception as e:
                logger.error(f"❌ Failed to send progress update: {e}")
                # Don't let WebSocket errors break the main process
        else:
            logger.warning(f"❌ Client {client_id} not found in active connections!")

    if action == FileAction.UPLOAD_ORDERS:
        # This action appends rows, progress can be reported differently if needed
        logger.info(f"Processing {len(parsed_data)} orders for upload")
        logger.info(f"Sample order data: {parsed_data[0] if parsed_data else 'No data'}")
        
        # Convert parsed data to the format expected by the sheet (like Discord bot does)
        from datetime import datetime
        rows_to_add = []
        failed = []
        
        # Send initial progress
        await progress_callback(0, len(parsed_data), f"Starting to process {len(parsed_data)} orders...")
        
        for i, order_data in enumerate(parsed_data, 1):
            try:
                now = datetime.now()
                
                # Format price as currency (like Discord bot)
                try:
                    price_value = float(order_data['Price'])
                    formatted_price = f"${price_value:,.2f}"
                except (ValueError, TypeError):
                    formatted_price = order_data['Price']  # Keep original if can't parse
                
                # Format quantity as integer (like Discord bot)
                try:
                    qty_value = int(order_data['Quantity'])
                    formatted_qty = qty_value
                except (ValueError, TypeError):
                    formatted_qty = order_data['Quantity']  # Keep original if can't parse
                
                # Create row in the exact same format as Discord bot
                row = [
                    now.strftime('%Y-%m-%d'),      # Date
                    now.strftime('%I:%M:%S %p'),   # Time
                    order_data['Product'],         # Product
                    formatted_price,               # Price
                    formatted_qty,                 # Quantity
                    order_data['Profile'],         # Profile
                    order_data['Proxy List'],      # Proxy List
                    order_data['Order Number'],    # Order Number
                    order_data['Email']            # Email
                ]
                rows_to_add.append(row)
                
                # Update progress less frequently for speed (every 10 orders or at the end)
                if i % 10 == 0 or i == len(parsed_data):
                    progress = int((i / len(parsed_data)) * 100)
                    await progress_callback(i, len(parsed_data), f"Processed {i}/{len(parsed_data)} orders... {len(rows_to_add)} valid, {len(failed)} failed")
                
                # Send individual order data for table display
                if client_id in manager.active_connections:
                    websocket = manager.active_connections[client_id]
                    try:
                        order_message = {
                            "type": "order_parsed",
                            "order": {
                                "id": i,
                                "product": order_data.get('Product', '')[:50] + ('...' if len(order_data.get('Product', '')) > 50 else ''),
                                "price": formatted_price,
                                "orderNumber": order_data.get('Order Number', ''),
                                "email": order_data.get('Email', ''),
                                "quantity": formatted_qty,
                                "status": "Parsed"
                            }
                        }
                        await websocket.send_json(order_message)
                        logger.debug(f"Sent order data for order {i}")
                    except Exception as e:
                        logger.error(f"Failed to send order data: {e}")
                
                # Regular progress update
                await progress_callback(i, len(parsed_data), f"Parsed order {i}: {order_data.get('Product', 'Unknown Product')[:30]}...")
                    
            except Exception as e:
                failed.append(f"Order {i}: {str(e)}")
                logger.error(f"Error processing order {i}: {e}")
        
        logger.info(f"Converted to {len(rows_to_add)} rows in Discord bot format")
        logger.info(f"Sample row: {rows_to_add[0] if rows_to_add else 'No rows'}")
        
        # Send final processing progress
        await progress_callback(len(parsed_data), len(parsed_data), f"Processing complete. Uploading {len(rows_to_add)} orders to sheet...")
        
        success, message = await sheets_manager.append_rows_discord_format(sheet_url, rows_to_add, worksheet_name, progress_callback)
        logger.info(f"Upload result: success={success}, message={message}")
        
        # Send completion progress
        if success:
            await progress_callback(len(parsed_data), len(parsed_data), f"✅ Successfully uploaded {len(rows_to_add)} orders!")
        else:
            await progress_callback(len(parsed_data), len(parsed_data), f"❌ Upload failed: {message}")
    elif action == FileAction.CANCEL_ORDERS:
        success, message = await process_cancel_orders(sheet_url, parsed_data, worksheet_name, progress_callback)
    elif action == FileAction.UPLOAD_TRACKINGS:
        success, message = await process_tracking_upload(sheet_url, parsed_data, worksheet_name, progress_callback)
    elif action == FileAction.MARK_RECEIVED:
        success, message = await process_mark_received(sheet_url, parsed_data, worksheet_name, progress_callback)
    elif action == FileAction.RECONCILE_CHARGES:
        success, message = await process_reconcile_charges(sheet_url, parsed_data, worksheet_name, progress_callback)

    if success:
        data_cache.clear_cache(sheet_url)
        await manager.broadcast_data_update(sheet_url, f"{action}_completed", {"count": len(parsed_data)})
        return {"message": message}
    else:
        # Check if it's a worksheet not found error and provide helpful guidance
        if "not found" in message.lower():
            raise HTTPException(status_code=400, detail=f"{message}. Tip: Leave worksheet name blank to use the default sheet, or ensure the worksheet name matches exactly (case-sensitive).")
        else:
            raise HTTPException(status_code=500, detail=message)


@app.post("/api/cache/clear")
async def clear_cache(sheet_url: str = None):
    """Clear cache for better data freshness (use sparingly)"""
    try:
        data_cache.clear_cache(sheet_url)
        return {
            "success": True,
            "message": f"Cache cleared for {sheet_url if sheet_url else 'all sheets'}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {e}")

@app.get("/api/debug/test-connection")
async def test_connection(sheet_url: str):
    """Debug endpoint to test Google Sheets connection and data fetching"""
    try:
        logger.info(f"🔍 Testing connection to sheet: {sheet_url}")
        
        # Test basic connection
        if not sheets_manager.client:
            return {"error": "Google Sheets client not initialized", "success": False}
        
        # Try to get worksheets first
        worksheets = sheets_manager.get_worksheet_list(sheet_url)
        logger.info(f"📋 Found worksheets: {worksheets}")
        
        # Try to get data from first worksheet
        if worksheets:
            test_df = await sheets_manager.get_all_data(sheet_url, worksheets[0])
            logger.info(f"📊 Sample data from {worksheets[0]}: {len(test_df)} rows, columns: {list(test_df.columns) if not test_df.empty else 'No data'}")
            
            return {
                "success": True,
                "sheets_client": "connected",
                "worksheets": worksheets,
                "sample_worksheet": worksheets[0],
                "sample_rows": len(test_df),
                "sample_columns": list(test_df.columns) if not test_df.empty else [],
                "sample_data": test_df.head(3).to_dict() if not test_df.empty else "No data"
            }
        else:
            return {"error": "No worksheets found", "success": False}
            
    except Exception as e:
        logger.error(f"❌ Debug connection test failed: {e}")
        return {"error": str(e), "success": False}

@app.get("/api/debug/overview-calculation")
async def debug_overview_calculation(sheet_url: str, date_filter: str = None):
    """Debug endpoint to understand overview calculation issues"""
    try:
        logger.info(f"🔍 Debug overview calculation for sheet: {sheet_url}, filter: {date_filter}")
        
        # Get data from all worksheets
        df = await sheets_manager.get_all_worksheets_data(sheet_url)
        
        if df is None:
            return {"error": "Failed to load data from Google Sheets"}
        
        if df.empty:
            return {"error": "No data found in sheet", "total_rows": 0}
        
        # Log basic info
        logger.info(f"📊 Total rows: {len(df)}")
        logger.info(f"📋 Columns: {list(df.columns)}")
        
        # Check for required columns
        required_columns = ['Date', 'Price', 'Commission', 'Tracking Number']
        column_status = {}
        for col in required_columns:
            column_status[col] = col in df.columns
            if col in df.columns:
                non_null_count = df[col].notna().sum()
                column_status[f"{col}_non_null"] = non_null_count
                logger.info(f"📊 {col}: {non_null_count}/{len(df)} non-null values")
        
        # Check date column and sample dates
        date_column = 'Date' if 'Date' in df.columns else None
        date_info = {}
        if date_column:
            df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
            date_info = {
                "min_date": str(df[date_column].min()),
                "max_date": str(df[date_column].max()),
                "today_orders": len(df[df[date_column].dt.date == datetime.now().date()]),
                "this_month_orders": len(df[
                    (df[date_column].dt.month == datetime.now().month) & 
                    (df[date_column].dt.year == datetime.now().year)
                ])
            }
        
        # Check price column and sample values
        price_info = {}
        if 'Price' in df.columns:
            price_values = df['Price'].dropna().head(10).tolist()
            price_info = {
                "sample_values": price_values,
                "non_null_count": df['Price'].notna().sum(),
                "total_revenue_estimate": float(df['Price'].apply(
                    lambda x: float(str(x).replace('$', '').replace(',', '')) if x and str(x) not in ['nan', '', 'None'] else 0
                ).sum())
            }
        
        # Check Commission column (for profit calculations)
        commission_info = {}
        if 'Commission' in df.columns:
            commission_values = df['Commission'].dropna().head(10).tolist()
            commission_info = {
                "sample_values": commission_values,
                "non_null_count": df['Commission'].notna().sum(),
                "total_profit_estimate": float(df['Commission'].apply(
                    lambda x: float(str(x).replace('$', '').replace(',', '')) if x and str(x) not in ['nan', '', 'None'] else 0
                ).sum())
            }
        
        return {
            "success": True,
            "total_rows": len(df),
            "columns": list(df.columns),
            "column_status": column_status,
            "date_info": date_info,
            "price_info": price_info,
            "commission_info": commission_info,
            "sample_data": df.head(3).to_dict() if not df.empty else {}
        }
        
    except Exception as e:
        logger.error(f"❌ Debug overview calculation failed: {e}")
        return {"error": str(e), "success": False}

@app.get("/api/debug/test-cell-update")
async def test_cell_update(sheet_url: str, row: int = 2, col: int = 2, value: str = "TEST"):
    """Debug endpoint to test cell update functionality"""
    try:
        logger.info(f"🧪 Testing cell update: sheet={sheet_url}, row={row}, col={col}, value={value}")
        
        # Test basic connection
        if not sheets_manager.client:
            return {"error": "Google Sheets client not initialized", "success": False}
        
        # Try to update a cell
        success = await sheets_manager.update_cell(sheet_url, row, col, value)
        
        if success:
            return {
                "success": True,
                "message": f"Cell updated successfully: row={row}, col={col}, value={value}",
                "sheets_client": "connected"
            }
        else:
            return {"error": "Cell update failed", "success": False}
            
    except Exception as e:
        logger.error(f"❌ Debug cell update test failed: {e}")
        return {"error": str(e), "success": False}

@app.get("/api/worksheets")
async def get_worksheets(sheet_url: str):
    """Get all available worksheets from the Google Sheet"""
    try:
        worksheets = await sheets_manager.get_worksheets_info(sheet_url)
        return {
            "worksheets": worksheets,
            "total_count": len(worksheets),
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching worksheets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch worksheets: {str(e)}")

@app.post("/api/worksheets/config")
async def update_worksheet_config(request: Dict[str, Any]):
    """Update worksheet configuration settings"""
    try:
        worksheet_configs = request.get("configurations", {})
        
        # Save configurations to a local file
        config_file = "worksheet_configs.json"
        
        import json
        with open(config_file, 'w') as f:
            json.dump(worksheet_configs, f, indent=2)
        
        logger.info(f"Updated worksheet configurations for {len(worksheet_configs)} worksheets")
        
        return {
            "status": "success",
            "message": f"Updated {len(worksheet_configs)} worksheet configurations",
            "updated_count": len(worksheet_configs),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error updating worksheet config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update configurations: {str(e)}")

@app.get("/api/worksheets/config")
async def get_worksheet_config():
    """Get current worksheet configuration settings"""
    try:
        config_file = "worksheet_configs.json"
        
        try:
            import json
            with open(config_file, 'r') as f:
                configurations = json.load(f)
        except FileNotFoundError:
            configurations = {}
        
        return {
            "configurations": configurations,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching worksheet config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch configurations: {str(e)}")

@app.get("/api/orders/overview/quick")
async def get_orders_overview_quick(sheet_url: str):
    """Get a fast overview with basic stats - uses cached data if available, otherwise returns estimated values"""
    try:
        # Try to get cached data first
        cache_key = f"overview_{sheet_url}_None_None_None"
        cached_result = data_cache.get_cached_data(cache_key, None)
        if cached_result:
            logger.info("⚡ INSTANT: Returning cached overview data for quick view")
            return cached_result
        
        # If no cache, try to get basic stats from first worksheet only
        logger.info("🔥 FAST PATH: Getting basic stats from first worksheet...")
        
        if not sheets_manager.client:
            return {"error": "Google Sheets client not initialized"}
        
        try:
            sheet = sheets_manager.client.open_by_url(sheet_url)
            first_worksheet = sheet.get_worksheet(0)
            
            # Get just the first 100 rows for quick stats
            data = first_worksheet.get_all_records(head=100)
            
            if not data:
                return {
                    "overview": {
                        "total_orders": 0,
                        "total_revenue": "$0.00",
                        "orders_today": 0,
                        "pending_orders": 0,
                        "is_partial": True,
                        "message": "Loading full data..."
                    },
                    "status_breakdown": {},
                    "top_products": {},
                    "recent_orders_count": 0,
                    "last_updated": datetime.now().isoformat(),
                    "account_name": sheets_manager.get_account_info()
                }
            
            df = pd.DataFrame(data)
            df = sheets_manager.format_dataframe(df)
            
            # Quick calculations
            total_orders = len(df)
            
            # Quick revenue calculation
            try:
                total_revenue = df['Price'].apply(lambda x: float(str(x).replace('$', '').replace(',', '')) if x else 0).sum()
            except:
                total_revenue = 0
            
            # Today's orders
            try:
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                today = datetime.now().date()
                orders_today = len(df[df['Date'].dt.date == today])
            except:
                orders_today = 0
            
            # Pending orders estimate
            tracking_column = None
            for col in ['Tracking Number', 'Tracking', 'Track Number']:
                if col in df.columns:
                    tracking_column = col
                    break
            
            pending_orders = 0
            if tracking_column:
                pending_orders = len(df[
                    df[tracking_column].isna() | 
                    (df[tracking_column] == '') |
                    (df[tracking_column].astype(str).str.strip() == '')
                ])
            
            return {
                "overview": {
                    "total_orders": total_orders,
                    "total_revenue": f"${total_revenue:,.2f}",
                    "orders_today": orders_today,
                    "pending_orders": pending_orders,
                    "is_partial": True,
                    "message": f"Quick view from first 100 rows • Loading full data..."
                },
                "status_breakdown": {},
                "top_products": {},
                "recent_orders_count": total_orders,
                "last_updated": datetime.now().isoformat(),
                "account_name": sheets_manager.get_account_info()
            }
            
        except Exception as e:
            logger.error(f"Quick overview failed: {e}")
            return {
                "overview": {
                    "total_orders": 0,
                    "total_revenue": "$0.00",
                    "orders_today": 0,
                    "pending_orders": 0,
                    "is_partial": True,
                    "message": "Loading data..."
                },
                "status_breakdown": {},
                "top_products": {},
                "recent_orders_count": 0,
                "last_updated": datetime.now().isoformat(),
                "account_name": sheets_manager.get_account_info()
            }
    
    except Exception as e:
        logger.error(f"Error in quick overview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get quick overview: {str(e)}")

@app.get("/api/orders/overview")
async def get_orders_overview(
    sheet_url: str, 
    date_filter: Optional[str] = None,
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None
):
    """Get overall inventory and pending orders overview with live data from all worksheets"""
    try:
        # Include date parameters in cache key for filtered data
        cache_key = f"overview_{sheet_url}_{date_filter}_{start_date}_{end_date}"
        cached_result = data_cache.get_cached_data(cache_key, None)
        if cached_result:
            logger.info("✅ Fast path: Returning cached overview data")
            return cached_result
        
        # Start timer for performance monitoring
        start_time = time.time()
        logger.info("🚀 Starting fresh data fetch for dashboard...")

        df = await sheets_manager.get_all_worksheets_data(sheet_url)

        if df is None:
            logger.error("❌ get_all_worksheets_data returned None")
            return {"error": "Failed to load data from Google Sheets"}

        if df.empty:
            logger.warning("⚠️ No data found in sheet")
            # Return empty but valid structure instead of error
            return {
                "overview": {
                    "total_orders": 0,
                    "total_revenue": "$0.00",
                    "orders_today": 0,
                    "pending_orders": 0,
                    "pending_quantity": 0,
                    "total_quantity": 0,
                    "received_quantity": 0,
                    "current_month_orders": 0,
                    "current_month_shipped": 0,
                    "current_month_revenue": "$0.00",
                    "current_month_profit": "$0.00",
                    "fulfillment_rate": 0,
                    "average_order_value": "$0.00"
                },
                "status_breakdown": [],
                "top_products": [],
                "recent_orders_count": 0,
                "last_updated": datetime.now().isoformat(),
                "account_name": sheets_manager.get_account_info(),
                "data_source": "empty",
                "message": "No data found in the sheet"
            }
        
        data_fetch_time = time.time() - start_time
        logger.info(f"📊 Data fetch completed in {data_fetch_time:.2f}s")
        
        # Keep original unfiltered data for ALL TIME calculations (deep copy to prevent modifications)
        original_df = df.copy(deep=True)
        logger.info(f"📊 Saved original_df with {len(original_df)} rows for all-time calculations")
        
        # Apply date filtering if specified
        if date_filter or (start_date and end_date):
            logger.info(f"Applying date filter: date_filter={date_filter}, start_date={start_date}, end_date={end_date}")
            original_row_count = len(df) if df is not None else 0
            df = apply_date_filter(df, date_filter, start_date, end_date)

            if df is None:
                logger.error("❌ apply_date_filter returned None")
                return {"error": "Failed to apply date filter"}

            logger.info(f"Date filtering complete: {original_row_count} -> {len(df)} rows")

            if df.empty:
                logger.warning("No data left after date filtering!")
                # Return empty but valid structure instead of error
                return {
                    "overview": {
                        "total_orders": 0,
                        "total_revenue": "$0.00",
                        "orders_today": 0,
                        "pending_orders": 0,
                        "pending_quantity": 0,
                        "total_quantity": 0,
                        "received_quantity": 0,
                        "current_month_orders": 0,
                        "current_month_shipped": 0,
                        "current_month_revenue": "$0.00",
                        "current_month_profit": "$0.00",
                        "fulfillment_rate": 0,
                        "average_order_value": "$0.00"
                    },
                    "status_breakdown": [],
                    "top_products": [],
                    "recent_orders_count": 0,
                    "last_updated": datetime.now().isoformat(),
                    "account_name": sheets_manager.get_account_info(),
                    "data_source": "filtered",
                    "message": "No orders found for the selected date range"
                }
        
        # Calculate key metrics for inventory visibility
        today = datetime.now().date()
        
        # Debug: Let's see what columns we actually have
        logger.info(f"Available columns: {list(df.columns)}")
        logger.info(f"DataFrame shape: {df.shape}")
        
        # DETECT TRACKING COLUMN - needed for multiple calculations
        tracking_column = None
        for col in ['Tracking Number', 'Tracking', 'Track Number', 'Track #', 'Tracking#']:
            if col in df.columns:
                tracking_column = col
                break
        
        # TODAY'S STATS - Core requirement
        # Parse the Date column (first column typically) for today's filtering
        date_column = 'Date' if 'Date' in df.columns else df.columns[1] if len(df.columns) > 1 else None
        
        if date_column:
            # Convert date column to datetime for filtering (work with copies to preserve original data)
            df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
            
            # Filter for today's data only
            todays_data = df[df[date_column].dt.date == today]
            logger.info(f"Today's data: {len(todays_data)} rows out of {len(df)} total")
            
            # Now convert date column in original_df for month filtering
            original_df[date_column] = pd.to_datetime(original_df[date_column], errors='coerce')
            logger.info(f"📊 original_df after date conversion: {len(original_df)} rows")
        else:
            todays_data = pd.DataFrame()  # No date column found
            logger.warning("No date column found for today's filtering")
        
        # TODAY'S REVENUE - Filter all rows by today date, then add up all the rows under the Price column
        todays_revenue = 0.0
        if not todays_data.empty and 'Price' in todays_data.columns:
            # Debug pricing before calculation
            logger.info(f"📊 TODAY'S REVENUE: Filtering {len(todays_data)} rows from today")
            logger.info(f"Today's Price column sample: {todays_data['Price'].head(10).tolist()}")
            todays_revenue = float(todays_data['Price'].apply(
                lambda x: float(str(x).replace('$', '').replace(',', '')) if x and str(x) not in ['nan', '', 'None'] else 0
            ).sum())
            logger.info(f"✅ Calculated today's revenue: ${todays_revenue:,.2f} from {len(todays_data)} orders")
        
        # MONTHLY REVENUE - Filter all rows from current month, then add up all the rows under the Price column
        monthly_revenue = 0.0
        current_month_data = pd.DataFrame()
        if 'Price' in original_df.columns and date_column:
            # Debug: Check date range and conversion issues
            logger.info(f"📊 MONTHLY REVENUE DEBUG:")
            logger.info(f"  - original_df has {len(original_df)} total rows")
            logger.info(f"  - Date column min: {original_df[date_column].min()}")
            logger.info(f"  - Date column max: {original_df[date_column].max()}")
            logger.info(f"  - NaT count in Date: {original_df[date_column].isna().sum()}")
            logger.info(f"  - Looking for month={today.month}, year={today.year}")
            
            # Sample some dates to see what we have
            sample_dates = original_df[date_column].dropna().head(20)
            logger.info(f"  - Sample dates (first 20): {sample_dates.tolist()}")
            
            # Always use current month from ORIGINAL unfiltered data
            current_month_data = original_df[
                (original_df[date_column].dt.month == today.month) &
                (original_df[date_column].dt.year == today.year)
            ]
            logger.info(f"📊 MONTHLY REVENUE: Filtering {len(current_month_data)} rows from {today.year}-{today.month:02d}")
            
            if not current_month_data.empty:
                monthly_revenue = float(current_month_data['Price'].apply(
                    lambda x: float(str(x).replace('$', '').replace(',', '')) if x and str(x) not in ['nan', '', 'None'] else 0
                ).sum())
                logger.info(f"✅ Calculated monthly revenue: ${monthly_revenue:,.2f} from {len(current_month_data)} orders")
            else:
                logger.info("No data available for monthly revenue calculation")
        
        # SELECTED MONTH METRICS for KPI Dashboard (based on filtered data)
        selected_month_orders = 0
        selected_month_shipped = 0
        selected_month_packages_scanned = 0
        selected_month_missing_packages = 0
        selected_month_profit = 0.0
        
        # PREVIOUS MONTH METRICS for comparison
        previous_month_orders = 0
        previous_month_shipped = 0
        previous_month_packages_scanned = 0
        previous_month_missing_packages = 0
        previous_month_profit = 0.0
        
        # Total orders should be from ALL TIME (use original_df)
        total_orders = len(original_df)
        logger.info(f"📊 TOTAL ORDERS (all time): {total_orders}")
        total_revenue = 0.0
        total_profit = 0.0
        total_shipped = 0
        total_packages_scanned = 0
        total_missing_packages = 0

        # TOTAL REVENUE - Add up all the rows under the Price column from ALL TIME (use original_df, not filtered)
        if 'Price' in original_df.columns:
            # Debug: Check what price values we have
            logger.info(f"📊 TOTAL REVENUE: Calculating from {len(original_df)} total rows (all time)")
            logger.info(f"Sample Price values (first 10): {original_df['Price'].head(10).tolist()}")
            logger.info(f"Sample Price values (last 10): {original_df['Price'].tail(10).tolist()}")
            logger.info(f"Non-null Price values: {original_df['Price'].notna().sum()}")
            logger.info(f"Null Price values: {original_df['Price'].isna().sum()}")

            # Parse price values
            def parse_price(x):
                if pd.isna(x) or x is None or str(x).lower() in ['nan', '', 'none']:
                    return 0.0
                try:
                    # Remove $ and commas, then convert to float
                    cleaned = str(x).replace('$', '').replace(',', '').strip()
                    return float(cleaned)
                except (ValueError, TypeError):
                    logger.warning(f"Could not parse price value: {x}")
                    return 0.0

            price_values = original_df['Price'].apply(parse_price)
            total_revenue = float(price_values.sum())

            # Additional debugging
            logger.info(f"Parsed price values sample (first 10): {price_values.head(10).tolist()}")
            logger.info(f"Parsed price values sample (last 10): {price_values.tail(10).tolist()}")
            logger.info(f"Number of non-zero prices: {(price_values > 0).sum()}")
            logger.info(f"Sum of all parsed prices: ${price_values.sum():,.2f}")
            logger.info(f"Max price value: ${price_values.max():,.2f}")
            logger.info(f"Min non-zero price value: ${price_values[price_values > 0].min() if (price_values > 0).any() else 0:,.2f}")
            logger.info(f"✅ Total revenue (all time): ${total_revenue:,.2f} from {len(original_df)} orders")

            # Check if there are other price columns
            price_cols = [col for col in original_df.columns if 'price' in col.lower()]
            logger.info(f"Available price-related columns: {price_cols}")

        # PROFIT - Filter rows in the current month, then add up all rows from the "Commission" column
        profit_col = None
        # Look for "Commission" column (as specified by user)
        profit_cols = ['Commission', 'Comission', 'Comm', 'commission', 'comission', 'comm']
        for col in profit_cols:
            if col in current_month_data.columns:
                profit_col = col
                logger.info(f"📊 PROFIT: Found profit column: {profit_col}")
                break

        # Debug: Check all available columns related to money/profit
        money_cols = [col for col in current_month_data.columns if any(keyword in col.lower() for keyword in ['commission', 'profit', 'price', 'cost', 'revenue', 'total'])]
        logger.info(f"Available money-related columns: {money_cols}")

        if profit_col and not current_month_data.empty:
            logger.info(f"Sample {profit_col} values from current month: {current_month_data[profit_col].head(10).tolist()}")
            total_profit = float(current_month_data[profit_col].apply(
                lambda x: float(str(x).replace('$', '').replace(',', '')) if x and str(x) not in ['nan', '', 'None'] else 0
            ).sum())
            logger.info(f"✅ Current month profit: ${total_profit:,.2f} from {len(current_month_data)} orders in {today.year}-{today.month:02d} (using column '{profit_col}')")
        else:
            logger.warning(f"⚠️ No Commission column found. Available columns: {list(current_month_data.columns) if not current_month_data.empty else 'No data'}")
            total_profit = 0.0

        # Calculate total shipped packages - FROM ALL TIME
        if tracking_column:
            total_shipped = len(original_df[
                original_df[tracking_column].notna() &
                (original_df[tracking_column] != '') &
                (original_df[tracking_column].astype(str).str.strip() != '')
            ])
            logger.info(f"Total shipped (all time): {total_shipped}")

        # Calculate total packages scanned - FROM ALL TIME
        qty_received_col = None
        for col in ['Qty Received', 'QTY Received', 'Quantity Received', 'Received Qty']:
            if col in original_df.columns:
                qty_received_col = col
                break

        if qty_received_col:
            total_packages_scanned = int(original_df[qty_received_col].apply(
                lambda x: float(str(x).replace('$', '').replace(',', '')) if x and str(x) not in ['nan', '', 'None'] else 0
            ).sum())
            logger.info(f"Total packages scanned (all time): {total_packages_scanned}")

        total_missing_packages = total_shipped - total_packages_scanned
        logger.info(f"Total missing packages (all time): {total_missing_packages}")

        # Monthly revenue is already calculated above from current_month_data
        # All dashboard values now use all-time data
        logger.info("📊 Dashboard showing all-time metrics as baseline")

        # Calculate previous month data for comparison
        if date_column and not original_df.empty:
            # Determine the target month and year based on the applied date filter
            if date_filter == 'last_month':
                # When filtering to last month, the target month is the previous month
                if today.month == 1:
                    target_year = today.year - 1
                    target_month = 12
                else:
                    target_year = today.year
                    target_month = today.month - 1
            elif date_filter == 'this_month':
                # When filtering to this month, the target month is the current month
                target_year = today.year
                target_month = today.month
            elif date_filter and len(date_filter) == 7 and date_filter[4] == '-':  # Format: "2025-08"
                # Specific month filter (YYYY-MM format)
                target_year = int(date_filter[:4])
                target_month = int(date_filter[5:7])
            else:
                # No date filter or other filter types - use current month
                target_year = today.year
                target_month = today.month

            # Calculate previous month relative to the target month
            if target_month == 1:
                prev_year = target_year - 1
                prev_month = 12
            else:
                prev_year = target_year
                prev_month = target_month - 1
            
            # Get previous month data from ORIGINAL unfiltered dataframe
            previous_month_data = original_df[
                (original_df[date_column].dt.month == prev_month) & 
                (original_df[date_column].dt.year == prev_year)
            ]
            
            logger.info(f"Previous month calculation: target_month={target_year}-{target_month:02d}, looking for previous month {prev_year}-{prev_month:02d} in original data")
            logger.info(f"Previous month data found: {len(previous_month_data)} rows")
            logger.info(f"Original dataframe total rows: {len(original_df)}")
            logger.info(f"Filtered dataframe total rows: {len(df)}")
            logger.info(f"Date filter applied: {date_filter}")
            
            if not previous_month_data.empty:
                # Calculate previous month metrics
                previous_month_orders = len(previous_month_data)
                
                if tracking_column:
                    previous_month_shipped = len(previous_month_data[
                        previous_month_data[tracking_column].notna() & 
                        (previous_month_data[tracking_column] != '') &
                        (previous_month_data[tracking_column].astype(str).str.strip() != '')
                    ])
                
                # Previous month packages scanned
                qty_received_col = None
                for col in ['Qty Received', 'QTY Received', 'Quantity Received', 'Received Qty']:
                    if col in previous_month_data.columns:
                        qty_received_col = col
                        break
                
                if qty_received_col:
                    previous_month_packages_scanned = int(previous_month_data[qty_received_col].apply(
                        lambda x: float(str(x).replace('$', '').replace(',', '')) if x and str(x) not in ['nan', '', 'None'] else 0
                    ).sum())
                
                previous_month_missing_packages = previous_month_shipped - previous_month_packages_scanned
                
                # Previous month profit
                commission_col = None
                for col in ['Commission', 'Comission', 'Comm', 'Profit']:
                    if col in previous_month_data.columns:
                        commission_col = col
                        break
                
                if commission_col:
                    previous_month_profit = float(previous_month_data[commission_col].apply(
                        lambda x: float(str(x).replace('$', '').replace(',', '')) if x and str(x) not in ['nan', '', 'None'] else 0
                    ).sum())
                
                # Debug: Log the calculated previous month metrics
                logger.info(f"Previous month metrics calculated:")
                logger.info(f"  - Orders: {previous_month_orders}")
                logger.info(f"  - Shipped: {previous_month_shipped}")
                logger.info(f"  - Packages Scanned: {previous_month_packages_scanned}")
                logger.info(f"  - Missing Packages: {previous_month_missing_packages}")
                logger.info(f"  - Profit: ${previous_month_profit:,.2f}")
        
        # Note: total metrics are already calculated above
        
        # Calculate current month metrics (for Analytics page KPIs)
        logger.info(f"📊 CURRENT MONTH METRICS: Calculating from {len(current_month_data)} rows in {today.year}-{today.month:02d}")

        if not current_month_data.empty:
            # 1. Orders - count total rows in current month
            selected_month_orders = len(current_month_data)
            logger.info(f"✅ Current month orders: {selected_month_orders}")

            # Debug: Check date range in current_month_data
            if date_column and date_column in current_month_data.columns:
                logger.info(f"Date range in current month data: {current_month_data[date_column].min()} to {current_month_data[date_column].max()}")
            
            # 2. Shipped - count rows with tracking numbers in current month
            if tracking_column:
                selected_month_shipped = len(current_month_data[
                    current_month_data[tracking_column].notna() & 
                    (current_month_data[tracking_column] != '') &
                    (current_month_data[tracking_column].astype(str).str.strip() != '')
                ])
                logger.info(f"✅ Current month shipped: {selected_month_shipped}")
            
            # 3. Packages Scanned - sum of Qty Received column in current month
            if qty_received_col and qty_received_col in current_month_data.columns:
                selected_month_packages_scanned = int(current_month_data[qty_received_col].apply(
                    lambda x: float(str(x).replace('$', '').replace(',', '')) if x and str(x) not in ['nan', '', 'None'] else 0
                ).sum())
                logger.info(f"✅ Current month packages scanned: {selected_month_packages_scanned} (from column: {qty_received_col})")
            else:
                selected_month_packages_scanned = 0
                logger.warning(f"⚠️ No quantity received column found. Looking for 'Qty Received' column.")
            
            # 4. Missing Packages - shipped minus packages scanned
            selected_month_missing_packages = selected_month_shipped - selected_month_packages_scanned
            logger.info(f"Selected period missing packages calculation: {selected_month_shipped} shipped - {selected_month_packages_scanned} scanned = {selected_month_missing_packages}")
            
            # 5. Profit - sum of Total column in current month (use current_month_data)
            try:
                if profit_col and not current_month_data.empty:
                    selected_month_profit = float(current_month_data[profit_col].apply(
                        lambda x: float(str(x).replace('$', '').replace(',', '')) if x and str(x) not in ['nan', '', 'None'] else 0
                    ).sum())
                    logger.info(f"✅ Selected period profit: ${selected_month_profit:,.2f} (from column: {profit_col}, {len(current_month_data)} rows)")
                else:
                    selected_month_profit = 0.0
                    logger.warning(f"⚠️ No profit column found for selected period. Looking for 'Total' column.")
            except Exception as profit_error:
                logger.error(f"❌ Error calculating profit: {profit_error}")
                selected_month_profit = 0.0
        else:
            # No data available for the selected period
            selected_month_orders = 0
            selected_month_shipped = 0
            selected_month_packages_scanned = 0
            selected_month_missing_packages = 0
            selected_month_profit = 0.0
            logger.warning("No data available for selected period")
        
        # TODAY'S ORDERS - count of rows with today's date
        todays_orders = int(len(todays_data)) if not todays_data.empty else 0
        
        # PENDING ORDERS - use same logic as periodic refresh for consistency
        # Check for orders that are either unverified OR missing tracking numbers
        if tracking_column and 'Status' in df.columns:
            # Debug: Log the filtering logic
            unverified_mask = df['Status'].str.upper() != 'VERIFIED'
            no_tracking_mask = df[tracking_column].isna() | (df[tracking_column] == '')
            combined_mask = unverified_mask | no_tracking_mask
            
            pending_count = len(df[combined_mask])
            
            logger.info(f"Dashboard pending calculation: unverified={unverified_mask.sum()}, no_tracking={no_tracking_mask.sum()}, combined={pending_count}")
            logger.info(f"Status column sample: {df['Status'].value_counts().head(10).to_dict()}")
            logger.info(f"Tracking column sample: {df[tracking_column].value_counts().head(10).to_dict()}")
        else:
            # Fallback to tracking number only if status column not found
            pending_orders_df = filter_pending_orders(df)
            pending_count = len(pending_orders_df)
            logger.info(f"Dashboard pending count (fallback): {pending_count}")
        
        logger.info(f"Dashboard pending count: {pending_count}")
        
        # Note: total_orders is already defined above from filtered data (data_for_metrics)
        
        # Note: total_revenue is already calculated above from filtered data (data_for_metrics)
        
        # Status breakdown - using filtered data
        status_counts = {}
        if 'Missing' in df.columns:
            total_missing = int(df['Missing'].sum()) if not pd.isna(df['Missing'].sum()) else 0
            status_counts = {
                'Complete': int(len(df[df['Missing'] == 0])),
                'Missing Items': total_missing,
                'Pending': int(len(df[df['Missing'] > 0]))
            }
        
        # Product runs breakdown (by worksheet)
        product_runs = {}
        worksheet_breakdown = {}
        if 'Worksheet' in df.columns:
            worksheet_breakdown = {str(k): int(v) for k, v in df['Worksheet'].value_counts().to_dict().items()}
            
        # Products breakdown within each worksheet - Enhanced with detailed metrics
        product_column = 'Item' if 'Item' in df.columns else 'Product'
        detailed_products = {}
        
        try:
            if product_column in df.columns:
                # Get top 10 products by order count
                top_products = df[product_column].value_counts().head(10)
                
                # Calculate detailed metrics for each top product
                for product_name in top_products.index:
                    product_data = df[df[product_column] == product_name]
                    
                    # Basic metrics
                    order_count = len(product_data)
                    
                    # Revenue metrics (use product_ prefix to avoid overwriting main total_revenue)
                    product_total_revenue = 0.0
                    if 'Price' in product_data.columns:
                        product_total_revenue = float(product_data['Price'].apply(
                            lambda x: float(str(x).replace('$', '').replace(',', '')) if x and str(x) not in ['nan', '', 'None'] else 0
                        ).sum())
                    
                    # Profit metrics (use product_ prefix to avoid overwriting main total_profit)
                    product_total_profit = 0.0
                    if 'Commission' in product_data.columns:
                        product_total_profit = float(product_data['Commission'].apply(
                            lambda x: float(str(x).replace('$', '').replace(',', '')) if x and str(x) not in ['nan', '', 'None'] else 0
                        ).sum())
                    elif 'Profit' in product_data.columns:
                        product_total_profit = float(product_data['Profit'].apply(
                            lambda x: float(str(x).replace('$', '').replace(',', '')) if x and str(x) not in ['nan', '', 'None'] else 0
                        ).sum())
                    
                    # Quantity metrics
                    total_quantity = 0
                    if 'Quantity' in product_data.columns:
                        total_quantity = int(product_data['Quantity'].apply(
                            lambda x: float(str(x).replace('$', '').replace(',', '')) if x and str(x) not in ['nan', '', 'None'] else 0
                        ).sum())
                    elif 'Orders' in product_data.columns:
                        total_quantity = int(product_data['Orders'].apply(
                            lambda x: float(str(x).replace('$', '').replace(',', '')) if x and str(x) not in ['nan', '', 'None'] else 0
                        ).sum())
                    
                    # Shipped metrics
                    shipped_count = 0
                    if tracking_column:
                        shipped_count = len(product_data[
                            product_data[tracking_column].notna() & 
                            (product_data[tracking_column] != '') &
                            (product_data[tracking_column].astype(str).str.strip() != '')
                        ])
                    
                    # Average metrics
                    avg_price = product_total_revenue / order_count if order_count > 0 else 0
                    avg_profit = product_total_profit / order_count if order_count > 0 else 0
                    
                    detailed_products[str(product_name)] = {
                        'order_count': order_count,
                        'total_revenue': product_total_revenue,
                        'total_profit': product_total_profit,
                        'total_quantity': total_quantity,
                        'shipped_count': shipped_count,
                        'avg_price': avg_price,
                        'avg_profit': avg_profit,
                        'fulfillment_rate': (shipped_count / order_count * 100) if order_count > 0 else 0
                    }
                
                # Keep the old format for backward compatibility
                product_counts = {str(k): int(v) for k, v in top_products.to_dict().items()}
                
                logger.info(f"Calculated detailed metrics for {len(detailed_products)} top products")
            else:
                product_counts = {}
                logger.warning(f"Product column '{product_column}' not found in data")
        except Exception as e:
            logger.error(f"Error in product metrics calculation: {e}")
            product_counts = {}
            detailed_products = {}
            
        # Clean any NaN/infinity values for JSON compliance
        def clean_for_json(value):
            if isinstance(value, float):
                if pd.isna(value) or not (value == value):  # Check for NaN
                    return 0.0
                if value == float('inf') or value == float('-inf'):  # Check for infinity
                    return 0.0
                return float(value)
            return value
            
        # Add worksheet-based metrics
        if 'Worksheet' in df.columns:
            for worksheet in df['Worksheet'].unique():
                worksheet_df = df[df['Worksheet'] == worksheet]
                missing_col = 'Missing' if 'Missing' in worksheet_df.columns else None
                pending_count = 0
                
                if missing_col:
                    pending_count = int(worksheet_df[missing_col].sum()) if not pd.isna(worksheet_df[missing_col].sum()) else 0
                elif 'Shipped' in worksheet_df.columns and 'Orders' in worksheet_df.columns:
                    pending_count = int(len(worksheet_df[worksheet_df['Shipped'] < worksheet_df['Orders']]))
                
                completion_rate = 0
                if len(worksheet_df) > 0 and pending_count >= 0:
                    completion_rate = max(0, min(100, round((1 - pending_count / len(worksheet_df)) * 100, 1)))
                
                product_runs[str(worksheet)] = {
                    'total_orders': int(len(worksheet_df)),
                    'pending_items': pending_count,
                    'completion_rate': completion_rate
                }
        
        # Recent orders (last 7 days)
        week_ago = today - timedelta(days=7)
        if date_column and not df[date_column].isna().all():
            recent_orders = df[df[date_column].dt.date >= week_ago]
            recent_orders_count = int(len(recent_orders))
        else:
            recent_orders_count = int(len(df))
        
        # Quantity analysis - adapt to your columns
        quantity_col = 'Orders' if 'Orders' in df.columns else 'Quantity'
        received_col = 'Shipped' if 'Shipped' in df.columns else 'QTY Received'
        
        # Helper function to clean NaN/infinity values for JSON
        def clean_numeric(value):
            if pd.isna(value) or not (value == value):  # Check for NaN
                return 0.0
            if value == float('inf') or value == float('-inf'):  # Check for infinity
                return 0.0
            return float(value)
            
        if quantity_col in df.columns:
            total_quantity = int(clean_numeric(df[quantity_col].sum()))
        else:
            total_quantity = 0
            
        if received_col in df.columns:
            received_quantity = int(clean_numeric(df[received_col].sum()))
        else:
            received_quantity = 0
            
        pending_quantity = total_quantity - received_quantity
        
        result = {
            "overview": {
                # TODAY'S STATS (primary focus)
                "todays_revenue": f"${todays_revenue:,.2f}",
                "todays_orders": todays_orders,
                "pending_orders": pending_count,
                
                # CONTEXT STATS
                "total_orders": total_orders,
                "total_revenue": f"${total_revenue:,.2f}",
                "monthly_revenue": f"${monthly_revenue:,.2f}",
                "total_worksheets": len(worksheet_breakdown),
                
                # CURRENT MONTH KPI METRICS (for Analytics page)
                "current_month_orders": selected_month_orders,
                "current_month_shipped": selected_month_shipped,
                "current_month_packages_scanned": selected_month_packages_scanned,
                "current_month_missing_packages": selected_month_missing_packages,
                "current_month_profit": f"${selected_month_profit:,.2f}",
                
                # PREVIOUS MONTH KPI METRICS for comparison
                "previous_month_orders": previous_month_orders,
                "previous_month_shipped": previous_month_shipped,
                "previous_month_packages_scanned": previous_month_packages_scanned,
                "previous_month_missing_packages": previous_month_missing_packages,
                "previous_month_profit": f"${previous_month_profit:,.2f}",
                
                # LEGACY FIELDS (for compatibility)
                "orders_today": todays_orders,
                "pending_quantity": pending_quantity,
                "total_quantity": total_quantity,
                "received_quantity": received_quantity
            },
            "account_name": sheets_manager.get_account_info(),
            "status_breakdown": status_counts,
            "top_products": product_counts,
            "detailed_products": detailed_products,
            "worksheet_breakdown": worksheet_breakdown,
            "product_runs": product_runs,
            "recent_orders_count": recent_orders_count,
            "todays_date": today.isoformat(),
            "last_updated": datetime.now().isoformat(),
            "debug_info": {
                "total_rows": len(df),
                "price_column_exists": 'Price' in df.columns if not df.empty else False,
                "total_revenue_calculated": f"${total_revenue:,.2f}",
                "all_columns": list(df.columns) if not df.empty else []
            }
        }
        
        # Cache the result for 30 seconds
        data_cache.set_cached_data(cache_key, result, None)
        
        # Debug: Log the result structure before returning
        logger.info(f"✅ Overview calculation complete. Result keys: {list(result.keys())}")
        logger.info(f"✅ Overview overview keys: {list(result['overview'].keys())}")
        
        # Debug: Log the key metrics for verification
        logger.info(f"✅ Key metrics summary:")
        logger.info(f"  Current month orders: {result['overview']['current_month_orders']}")
        logger.info(f"  Previous month orders: {result['overview']['previous_month_orders']}")
        logger.info(f"  Current month profit: {result['overview']['current_month_profit']}")
        logger.info(f"  Previous month profit: {result['overview']['previous_month_profit']}")
        
        return result
    
    except Exception as e:
        logger.error(f"💥 Error in get_orders_overview: {e}")
        logger.error(f"💥 Error type: {type(e)}")
        logger.error(f"💥 Error repr: {repr(e)}")
        logger.error(f"💥 Error str: {str(e)}")
        import traceback
        logger.error(f"💥 Traceback: {traceback.format_exc()}")

        # Provide more detailed error message
        error_msg = str(e) if str(e) else f"Unknown error of type {type(e).__name__}"
        raise HTTPException(status_code=500, detail=f"Failed to get overview: {error_msg}")

@app.get("/api/orders/pending")
async def get_pending_orders(
    sheet_url: str,
    date_filter: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get detailed list of pending orders from all worksheets with optional date filtering"""
    try:
        # Get data from all worksheets
        df = await sheets_manager.get_all_worksheets_data(sheet_url)
        
        if df.empty:
            return {"error": "No data found in sheet"}
        
        logger.info(f"📊 Pending Orders - Initial data: {len(df)} total rows")
        
        # Apply date filtering FIRST if specified
        if date_filter or (start_date and end_date):
            logger.info(f"📅 Applying date filter to pending orders: filter={date_filter}, start={start_date}, end={end_date}")
            df = apply_date_filter(df, date_filter, start_date, end_date)
            if df.empty:
                logger.info("⚠️ No data after date filtering")
                return {
                    "pending_orders": [],
                    "total_pending": 0,
                    "last_updated": datetime.now().isoformat(),
                    "message": "No orders found for the selected date range"
                }
            logger.info(f"✅ After date filter: {len(df)} rows")
        
        # PENDING ORDERS - use same comprehensive logic as dashboard for consistency
        # Check for orders that are either unverified OR missing tracking numbers
        tracking_column = None
        for col in ['Tracking Number', 'Tracking', 'Track Number', 'Track #', 'Tracking#']:
            if col in df.columns:
                tracking_column = col
                break
        
        if tracking_column and 'Status' in df.columns:
            pending_df = df[
                (df['Status'].str.upper() != 'VERIFIED') | 
                (df[tracking_column].isna() | (df[tracking_column] == ''))
            ]
        else:
            # Fallback to tracking number only if status column not found
            pending_df = filter_pending_orders(df)
        
        logger.info(f"✅ Pending orders after filtering: {len(pending_df)} rows")
        
        # Sort by date (newest first) if Date column exists
        if 'Date' in pending_df.columns and not pending_df.empty:
            pending_df['Date'] = pd.to_datetime(pending_df['Date'], errors='coerce')
            pending_df = pending_df.sort_values('Date', ascending=False)
        
        # Convert to records for JSON response with row IDs
        pending_orders = []
        for idx, row in pending_df.iterrows():
            order = row.to_dict()
            order['_row_id'] = str(idx + 2)  # +2 because pandas index starts at 0, but sheet rows start at 2 (after header)
            
            # Clean up NaN values for JSON serialization
            for key, value in order.items():
                if pd.isna(value):
                    order[key] = ''
            
            pending_orders.append(order)
        
        return {
            "pending_orders": pending_orders,
            "total_pending": len(pending_orders),
            "last_updated": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pending orders: {e}")

@app.get("/api/orders/all")
async def get_all_orders(
    sheet_url: str,
    limit: int = 100,
    offset: int = 0,
    worksheet: str = None,
    date_filter: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get all orders with pagination, live data, and optional date filtering"""
    try:
        if worksheet:
            # Get data from specific worksheet
            df = await sheets_manager.get_all_data(sheet_url, worksheet)
        else:
            # Get data from all worksheets
            df = await sheets_manager.get_all_worksheets_data(sheet_url)
        
        if df.empty:
            return {"error": "No data found in sheet"}
        
        logger.info(f"📊 All Orders - Initial data: {len(df)} total rows")
        
        # Apply date filtering FIRST if specified
        if date_filter or (start_date and end_date):
            logger.info(f"📅 Applying date filter to all orders: filter={date_filter}, start={start_date}, end={end_date}")
            df = apply_date_filter(df, date_filter, start_date, end_date)
            if df.empty:
                logger.info("⚠️ No data after date filtering")
                return {
                    "orders": [],
                    "total_records": 0,
                    "limit": limit,
                    "offset": offset,
                    "has_next": False,
                    "last_updated": datetime.now().isoformat(),
                    "message": "No orders found for the selected date range"
                }
            logger.info(f"✅ After date filter: {len(df)} rows")
        
        # Sort by date (newest first)
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.sort_values('Date', ascending=False)
        
        # Apply pagination
        total_records = len(df)
        paginated_df = df.iloc[offset:offset + limit]
        
        logger.info(f"✅ All Orders - Returning {len(paginated_df)} rows (page {offset//limit + 1}, total: {total_records})")
        
        # Convert to records with row IDs
        orders = []
        for idx, row in paginated_df.iterrows():
            order = row.to_dict()
            order['_row_id'] = str(idx + 2)  # +2 because pandas index starts at 0, but sheet rows start at 2 (after header)
            
            # Clean up NaN values
            for key, value in order.items():
                if pd.isna(value):
                    order[key] = ''
            
            orders.append(order)
        
        return {
            "orders": orders,
            "total_records": total_records,
            "limit": limit,
            "offset": offset,
            "has_next": offset + limit < total_records,
            "last_updated": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get orders: {e}")

@app.get("/api/analytics/monthly-revenue")
async def get_monthly_revenue(sheet_url: str):
    """Get monthly revenue data for charting from January 2025 onwards"""
    try:
        # Get data from all worksheets
        df = await sheets_manager.get_all_worksheets_data(sheet_url)
        
        if df.empty:
            return {"error": "No data found in sheet"}
        
        # Find date and price columns
        date_columns = ['Date', 'Order Date', 'Created', 'Posted Date']
        price_columns = ['Price', 'Total', 'Amount', 'Revenue']
        
        date_column = None
        price_column = None
        
        for col in date_columns:
            if col in df.columns:
                date_column = col
                break
                
        for col in price_columns:
            if col in df.columns:
                price_column = col
                break
        
        if not date_column or not price_column:
            return {"error": f"Required columns not found. Date: {date_column}, Price: {price_column}"}
        
        # Convert date column to datetime and filter from January 2025
        df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
        df = df.dropna(subset=[date_column])
        
        # Filter from January 2025 onwards
        start_date = datetime(2025, 1, 1)
        df = df[df[date_column] >= start_date]
        
        # Debug logging
        logger.info(f"Date column: {date_column}")
        logger.info(f"Date range: {df[date_column].min()} to {df[date_column].max()}")
        logger.info(f"Total rows after filtering: {len(df)}")
        
        if df.empty:
            # Add fake data for January through June 2025 when no real data exists
            fake_data = [
                {"month": "2025-01", "revenue": 12500.00, "year": 2025, "month_num": 1},
                {"month": "2025-02", "revenue": 15800.00, "year": 2025, "month_num": 2},
                {"month": "2025-03", "revenue": 14200.00, "year": 2025, "month_num": 3},
                {"month": "2025-04", "revenue": 18900.00, "year": 2025, "month_num": 4},
                {"month": "2025-05", "revenue": 16500.00, "year": 2025, "month_num": 5},
                {"month": "2025-06", "revenue": 17800.00, "year": 2025, "month_num": 6}
            ]
            return {
                "monthly_data": fake_data,
                "last_updated": datetime.now().isoformat(),
                "note": "Using sample data - no real orders found"
            }
        
        # Convert price column to numeric, removing any currency symbols
        df[price_column] = df[price_column].astype(str).str.replace(r'[^\d.]', '', regex=True)
        df[price_column] = pd.to_numeric(df[price_column], errors='coerce')
        df = df.dropna(subset=[price_column])
        
        # Group by month and sum revenue
        df['YearMonth'] = df[date_column].dt.to_period('M')
        monthly_revenue = df.groupby('YearMonth')[price_column].sum().reset_index()
        
        # Convert to chart-friendly format
        chart_data = []
        for _, row in monthly_revenue.iterrows():
            year_month = row['YearMonth']
            chart_data.append({
                "month": f"{year_month.year}-{year_month.month:02d}",
                "revenue": round(float(row[price_column]), 2),
                "year": year_month.year,
                "month_num": year_month.month
            })
        
        # Sort by date
        chart_data.sort(key=lambda x: (x['year'], x['month_num']))
        
        # Add fake data for January through June 2025 if they don't exist
        fake_data = [
            {"month": "2025-01", "revenue": 125000.00, "year": 2025, "month_num": 1},
            {"month": "2025-02", "revenue": 158000.00, "year": 2025, "month_num": 2},
            {"month": "2025-03", "revenue": 142000.00, "year": 2025, "month_num": 3},
            {"month": "2025-04", "revenue": 189000.00, "year": 2025, "month_num": 4},
            {"month": "2025-05", "revenue": 165000.00, "year": 2025, "month_num": 5},
            {"month": "2025-06", "revenue": 178000.00, "year": 2025, "month_num": 6}
        ]
        
        # Create a set of existing months to avoid duplicates
        existing_months = {item["month"] for item in chart_data}
        
        # Add fake data for months that don't exist
        for fake_month in fake_data:
            if fake_month["month"] not in existing_months:
                chart_data.append(fake_month)
        
        # Re-sort by date to include the new fake data
        chart_data.sort(key=lambda x: (x['year'], x['month_num']))
        
        return {
            "monthly_data": chart_data,
            "last_updated": datetime.now().isoformat(),
            "note": "Includes sample data for missing months"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get monthly revenue: {e}")

# WebSocket endpoint for real-time updates
@app.websocket("/ws/{sheet_url:path}")
async def websocket_endpoint(websocket: WebSocket, sheet_url: str):
    # Decode the sheet URL (it comes URL-encoded from the frontend)
    from urllib.parse import unquote
    decoded_sheet_url = unquote(sheet_url)
    
    # Connect the websocket with the sheet URL as client ID
    await manager.connect(websocket, decoded_sheet_url)
    
    # Subscribe to sheet updates
    manager.subscribe_to_sheet(websocket, decoded_sheet_url)
    
    logger.info(f"✅ WebSocket connected and subscribed to sheet: {decoded_sheet_url[:50]}...")
    
    # Send connection confirmation
    await websocket.send_text(json.dumps({
        "type": "connection_status",
        "status": "connected",
        "message": "Successfully connected to real-time updates"
    }))
    
    try:
        while True:
            try:
                # Use asyncio.wait_for to add a timeout and prevent hanging
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                
                # Handle ping messages to keep connection alive
                try:
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
                        logger.debug(f"Sent pong to sheet: {decoded_sheet_url[:30]}...")
                    else:
                        # Echo back other messages as JSON
                        await websocket.send_text(json.dumps({"type": "echo", "data": message}))
                except json.JSONDecodeError:
                    # For non-JSON messages, send JSON response
                    await websocket.send_text(json.dumps({"type": "echo", "message": data}))
                    
            except asyncio.TimeoutError:
                # Send a ping to check if connection is still alive
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    logger.warning(f"Connection appears dead for sheet: {decoded_sheet_url[:30]}...")
                    break
                    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected from sheet: {decoded_sheet_url[:50]}...")
    except Exception as e:
        logger.error(f"WebSocket error for sheet {decoded_sheet_url[:30]}...: {e}")
    finally:
        manager.unsubscribe_from_sheet(websocket, decoded_sheet_url)
        manager.disconnect(websocket, decoded_sheet_url)

@app.websocket("/ws/actions/{client_id}")
async def actions_websocket(websocket: WebSocket, client_id: str):
    try:
        await websocket.accept()
        manager.active_connections[client_id] = websocket
        logger.info(f"✅ WebSocket connected for client {client_id}. Active connections: {len(manager.active_connections)}")
        
        # Send a test message to confirm connection
        await websocket.send_json({"type": "connection_confirmed", "client_id": client_id})
        
        while True:
            try:
                message = await websocket.receive_text()
                logger.debug(f"Received message from {client_id}: {message}")
                
                # Handle ping messages
                try:
                    data = json.loads(message)
                    if data.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                        logger.debug(f"Sent pong to {client_id}")
                except:
                    # Not JSON, ignore
                    pass
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling message from {client_id}: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket connection error for {client_id}: {e}")
    finally:
        # Clean up connection
        if client_id in manager.active_connections:
            del manager.active_connections[client_id]
        logger.info(f"🔌 WebSocket disconnected for client {client_id}. Active connections: {len(manager.active_connections)}")

# Write operations - Edit table functionality
@app.put("/api/orders/cell")
async def update_cell(request: CellUpdateRequest, sheet_url: str):
    """Update a single cell in the Google Sheet"""
    try:
        logger.info(f"🔄 Updating cell: row={request.row_id}, column={request.column}, value={request.value}")
        
        # Parse row_id to get actual row number
        row_num = int(request.row_id)
        logger.info(f"📊 Row number: {row_num}")
        
        # Get column mapping from all worksheets
        df = await sheets_manager.get_all_worksheets_data(sheet_url)
        headers = df.columns.tolist()
        logger.info(f"📋 Available columns: {headers}")
        
        if request.column not in headers:
            raise HTTPException(status_code=400, detail=f"Column '{request.column}' not found. Available columns: {headers}")
        
        col_num = headers.index(request.column) + 1  # +1 for 1-indexed sheets
        logger.info(f"📍 Column number: {col_num}")
        
        # Get old value for broadcasting - fix the index calculation
        df_index = row_num - 2  # Convert sheet row to DataFrame index
        if df_index >= 0 and df_index < len(df):
            old_value = df.iloc[df_index][request.column]
            logger.info(f"📝 Old value: {old_value}")
        else:
            old_value = ""
            logger.warning(f"⚠️ Row index {df_index} out of bounds for DataFrame with {len(df)} rows")
        
        # Find which worksheet this row belongs to
        worksheet_name = None
        if hasattr(df, 'attrs') and 'worksheet_name' in df.attrs:
            worksheet_name = df.attrs['worksheet_name']
        else:
            # Try to find the worksheet by checking which one contains this row
            worksheets = sheets_manager.get_worksheet_list(sheet_url)
            for ws_name in worksheets:
                try:
                    ws_df = await sheets_manager.get_all_data(sheet_url, ws_name)
                    if row_num - 2 < len(ws_df):  # Check if row exists in this worksheet
                        worksheet_name = ws_name
                        break
                except Exception as e:
                    logger.warning(f"Could not check worksheet {ws_name}: {e}")
                    continue
        
        logger.info(f"📋 Using worksheet: {worksheet_name}")
        
        # Update the cell with the correct worksheet
        success = await sheets_manager.update_cell(sheet_url, row_num, col_num, request.value, worksheet_name)
        
        if success:
            logger.info(f"✅ Cell updated successfully")
            
            # Clear cache if tracking number was updated (to refresh pending orders)
            tracking_columns = ['Tracking Number', 'Tracking', 'Track Number', 'Track #', 'Tracking#']
            if any(col.lower() in request.column.lower() for col in tracking_columns):
                data_cache.clear_cache(sheet_url)
                logger.info(f"🗑️ Cleared cache due to tracking number update in {request.column}")
            
            # Broadcast the change to all connected clients
            await manager.broadcast_cell_edit(
                sheet_url, 
                request.row_id, 
                request.column, 
                str(old_value), 
                request.value
            )
            
            return {"success": True, "message": "Cell updated successfully"}
        else:
            logger.error(f"❌ Failed to update cell")
            raise HTTPException(status_code=500, detail="Failed to update cell")
            
    except Exception as e:
        logger.error(f"💥 Error updating cell: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update cell: {e}")

@app.put("/api/orders/row")
async def update_row(request: RowUpdateRequest, sheet_url: str):
    """Update multiple cells in a row"""
    try:
        row_num = int(request.row_id)
        
        # Update the row
        success = await sheets_manager.update_row(sheet_url, row_num, request.data)
        
        if success:
            # Clear cache if tracking number was updated in the row
            tracking_columns = ['Tracking Number', 'Tracking', 'Track Number', 'Track #', 'Tracking#']
            if any(col in request.data for col in tracking_columns):
                data_cache.clear_cache(sheet_url)
                logger.info("Cleared cache due to tracking number update in row")
            
            # Broadcast the change
            await manager.broadcast_data_update(sheet_url, "row_update", {
                "row_id": request.row_id,
                "data": request.data
            })
            
            return {"success": True, "message": "Row updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update row")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update row: {e}")

@app.post("/api/orders/new")
async def create_order(request: NewOrderRequest, sheet_url: str):
    """Add a new order to the sheet"""
    try:
        success = await sheets_manager.append_row(sheet_url, request.data)
        
        if success:
            # Broadcast the new order
            await manager.broadcast_data_update(sheet_url, "new_order", request.data)
            
            return {"success": True, "message": "Order created successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to create order")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create order: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, access_log=True)
