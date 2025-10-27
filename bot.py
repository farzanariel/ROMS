import warnings
warnings.filterwarnings('ignore')
import urllib3
urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)

from typing import List, Optional
from collections import deque
import discord
from discord.ext import commands
import logging
from datetime import datetime, timedelta
import asyncio
import os
import re
import csv
import random
import traceback
from io import StringIO
from dotenv import load_dotenv
import psutil
from order_processor import OrderProcessor
import gspread
from tqdm import tqdm
from google.oauth2.service_account import Credentials
from discord.ui import View

# Standard header mapping for consistent column detection
STANDARD_HEADERS = {
    'date': ['date', 'order date', 'created date'],
    'time': ['time', 'order time', 'created time'],
    'product': ['product', 'product name', 'item', 'description'],
    'price': ['price', 'unit price', 'item price'],
    'total': ['total', 'total price', 'amount', 'order total'],
    'commission': ['commission', 'profit', 'earnings'],
    'quantity': ['quantity', 'qty', 'amount', 'count'],
    'profile': ['profile', 'account', 'user profile'],
    'proxy_list': ['proxy list', 'proxy', 'proxies'],
    'order_number': ['order number', 'order', 'order #', 'order id', 'sku'],
    'email': ['email', 'email address', 'customer email'],
    'reference': ['reference #', 'reference', 'ref #', 'ref', 'reference number'],
    'posted_date': ['posted date', 'posted', 'fulfilled date', 'completion date'],
    'tracking_number': ['tracking number', 'tracking', 'tracking #', 'shipment id'],
    'status': ['status', 'order status', 'state'],
    'qty_received': ['qty received', 'received', 'quantity received', 'received qty'],
    'order_id': ['order id', 'internal id', 'system id'],
    'created': ['created', 'created date', 'date created'],
    'modified': ['modified', 'last modified', 'updated', 'last updated']
}

def find_header_column(headers, target_key):
    """Find column index for a header key, case-insensitive with multiple variations"""
    lower_headers = [h.lower().strip() for h in headers]
    possible_names = STANDARD_HEADERS.get(target_key, [target_key])
    
    for possible_name in possible_names:
        if possible_name.lower() in lower_headers:
            return lower_headers.index(possible_name.lower())
    
    return None







from button_manager import ButtonManager
from command_handlers import CommandHandlers
from reconcile_handler import ReconcileChargesHandler
from order_tracker import OrderTracker
from order_cancellation import OrderCancellation
from mark_received import MarkReceived
from auth import (
    is_admin as check_admin_status, is_authorized, needs_setup,
    add_user, remove_user, get_user_profile,
    get_all_users_with_details, set_user_spreadsheet,
    load_user_data, save_user_data
)
from utils import (
    log_button_interaction,
    is_likely_connection_error
)
from sheets_utils import (
    initialize_sheets,
    get_spreadsheet,
    get_worksheet,
    get_worksheets,
    set_user_spreadsheet_in_utils,
    clear_user_spreadsheet_in_utils
)

# Custom logging handler for Discord
class DiscordHandler(logging.Handler):
    def __init__(self, bot_instance, owner_id):
        super().__init__()
        self.bot = bot_instance
        self.owner_id = owner_id
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    def emit(self, record):
        # Only send logs that are WARNING or higher
        if record.levelno >= logging.WARNING:
            log_entry = self.format(record)
            # Ensure the bot is ready before sending messages
            if self.bot.is_ready() and self.owner_id:
                # Schedule the message sending as a task
                asyncio.create_task(self._send_log_to_owner(log_entry, record.levelname))

    async def _send_log_to_owner(self, log_entry, level_name):
        try:
            owner = await safe_discord_call(self.bot.fetch_user, self.owner_id, call_type='user_fetch')
            if owner:
                # Customize message based on level
                if level_name == 'ERROR' or level_name == 'CRITICAL':
                    alert_message = f"```ansi\n\u001b[0;31m🚨 Bot Error Detected (Level: {level_name}):\n{log_entry}\n```"
                else: # For WARNING
                    alert_message = f"```ansi\n\u001b[0;33m⚠️ Bot Warning (Level: {level_name}):\n{log_entry}\n```"

                # Split long messages if necessary
                for chunk in [alert_message[i:i+1900] for i in range(0, len(alert_message), 1900)]:
                    await owner.send(chunk)
        except Exception as e:
            print(f"Error sending log to Discord owner: {e}")

# Set up logging
logging.basicConfig(
    filename='bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv()

# Get owner ID from environment variable
OWNER_ID = int(os.getenv('OWNER_ID', '0'))  # Default to 0 if not set

# Validation functions
def validate_price(price: str) -> bool:
    """Validate price format"""
    try:
        # Remove $ and convert to float
        price = float(price.replace('$', '').strip())
        return price > 0
    except:
        return False

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_quantity(quantity: str) -> bool:
    """Validate quantity is a positive number"""
    try:
        qty = int(quantity)
        return qty > 0
    except:
        return False

def format_currency(amount: float) -> str:
    """Format number as currency"""
    return f"${amount:,.2f}"

def calculate_revenue(orders: List[List[str]]) -> float:
    """Calculate total revenue from orders"""
    total = 0
    for order in orders:
        try:
            price = float(order[3].replace('$', '').strip())  # Price column
            quantity = int(order[4])  # Quantity column
            total += price * quantity
        except (ValueError, IndexError):
            continue
    return total

def is_likely_connection_error(e: Exception) -> bool:
    """Heuristically check if an exception is due to a connection error."""
    error_text = str(e).lower()
    return any(keyword in error_text for keyword in [
        'connection', 'max retries', 'service not known',
        'failed to establish a new connection', 'name or service not known'
    ])

async def send_long_list(channel, title: str, items: list):
    """
    Send a list of items as multiple messages if it exceeds Discord's character limit.
    
    Args:
        channel: Discord channel to send messages to
        title: Title for the list
        items: List of items to send
    """
    if not items:
        return
    
    text = '\n'.join(items)
    max_length = 1800  # Conservative limit to account for title and code block formatting
    
    # If it fits in one message, send it
    if len(text) <= max_length:
        message = f"{title}\n```\n{text}\n```"
        await channel.send(message)
        return
    
    # Split into multiple messages
    current_text = ""
    part_num = 1
    first_message = True
    
    for item in items:
        # Check if adding this item would exceed the limit
        test_text = current_text + ("\n" if current_text else "") + item
        
        if len(test_text) > max_length and current_text:
            # Send current batch
            if first_message:
                message = f"{title} (Part {part_num}):\n```\n{current_text}\n```"
                first_message = False
            else:
                message = f"{title} (Part {part_num}):\n```\n{current_text}\n```"
            
            await channel.send(message)
            current_text = item
            part_num += 1
        else:
            current_text = test_text
    
    # Send remaining items
    if current_text:
        if first_message:
            message = f"{title}\n```\n{current_text}\n```"
        else:
            message = f"{title} (Part {part_num}):\n```\n{current_text}\n```"
        await channel.send(message)

# Discord bot setup
intents = discord.Intents.all()
bot = commands.Bot(
    command_prefix='!',
    intents=intents,
    owner_id=OWNER_ID,
    # Add performance optimizations
    max_messages=10000,  # Reduce memory usage
    chunk_guilds_at_startup=False,  # Disable chunking to reduce startup time
    enable_debug_events=False,  # Disable debug events
    # Add rate limiting
    command_sync_flags=None,
    # Optimize for performance
    help_command=None  # Disable default help command to reduce overhead
)

# Add rate limiting for Discord API calls
import asyncio
from collections import defaultdict
import time

class RateLimiter:
    def __init__(self, max_calls=5, time_window=1.0):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = defaultdict(list)
    
    async def acquire(self, key):
        now = time.time()
        # Clean old calls
        self.calls[key] = [call_time for call_time in self.calls[key] 
                          if now - call_time < self.time_window]
        
        if len(self.calls[key]) >= self.max_calls:
            # Wait until we can make another call
            wait_time = self.time_window - (now - self.calls[key][0])
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        self.calls[key].append(now)

# Create rate limiters for different operations
# Discord rate limits: 50 requests per second per bot, but we'll be more conservative
discord_rate_limiter = RateLimiter(max_calls=1, time_window=1.0)  # 1 call per second (very conservative)
discord_message_limiter = RateLimiter(max_calls=1, time_window=2.0)  # 1 message per 2 seconds for channels
discord_user_limiter = RateLimiter(max_calls=1, time_window=3.0)  # 1 user fetch per 3 seconds (very conservative)
sheets_rate_limiter = RateLimiter(max_calls=2, time_window=1.0)   # 2 calls per second

# Discord API wrapper with rate limiting and retry logic
async def safe_discord_call(func, *args, max_retries=3, call_type='general', **kwargs):
    """Safely execute Discord API calls with rate limiting and retry logic"""
    for attempt in range(max_retries):
        try:
            # Apply appropriate rate limiting based on call type
            if call_type == 'message':
                await discord_message_limiter.acquire('message_send')
            elif call_type == 'user_fetch':
                await discord_user_limiter.acquire('user_fetch')
            else:
                await discord_rate_limiter.acquire('discord_api')
            
            # Execute the Discord API call
            result = await func(*args, **kwargs)
            return result
            
        except discord.HTTPException as e:
            if e.status == 429:  # Rate limited
                if attempt < max_retries - 1:
                    # Extract retry_after from response headers or use exponential backoff
                    retry_after = getattr(e, 'retry_after', 2.0) * (2 ** attempt)  # More conservative exponential backoff
                    # Add extra delay based on call type
                    if call_type == 'message':
                        retry_after += 2.0
                    elif call_type == 'user_fetch':
                        retry_after += 3.0  # Extra delay for user fetching
                    logging.warning(f"Discord rate limited ({call_type}), retrying in {retry_after:.1f} seconds... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    logging.error(f"Discord rate limit exceeded after {max_retries} attempts ({call_type}): {str(e)}")
                    raise
            else:
                # Other HTTP errors, don't retry
                raise
        except Exception as e:
            logging.error(f"Unexpected error in Discord API call ({call_type}): {str(e)}")
            raise

# Monkey patch Discord API methods to use rate limiting
def patch_discord_methods():
    """Patch Discord API methods to use rate limiting"""
    # Store original methods
    original_send = discord.abc.Messageable.send
    original_edit = discord.Message.edit
    original_send_message = discord.InteractionResponse.send_message
    original_followup_send = discord.Webhook.send
    
    async def rate_limited_send(self, *args, **kwargs):
        return await safe_discord_call(original_send, self, *args, call_type='message', **kwargs)
    
    async def rate_limited_edit(self, *args, **kwargs):
        return await safe_discord_call(original_edit, self, *args, call_type='edit', **kwargs)
    
    async def rate_limited_send_message(self, *args, **kwargs):
        return await safe_discord_call(original_send_message, self, *args, call_type='message', **kwargs)
    
    async def rate_limited_followup_send(self, *args, **kwargs):
        return await safe_discord_call(original_followup_send, self, *args, call_type='message', **kwargs)
    
    # Apply patches
    discord.abc.Messageable.send = rate_limited_send
    discord.Message.edit = rate_limited_edit
    discord.InteractionResponse.send_message = rate_limited_send_message
    discord.Webhook.send = rate_limited_followup_send

# Add chunking utility for large operations
async def chunk_operation(items, chunk_size=50, operation_func=None, progress_callback=None):
    """Process items in chunks to avoid blocking the event loop"""
    results = []
    total_chunks = (len(items) + chunk_size - 1) // chunk_size
    
    for i in range(0, len(items), chunk_size):
        chunk = items[i:i + chunk_size]
        
        # Process chunk
        if operation_func:
            chunk_result = await operation_func(chunk)
            results.extend(chunk_result)
        
        # Update progress
        if progress_callback:
            chunk_num = (i // chunk_size) + 1
            await progress_callback(chunk_num, total_chunks)
        
        # Yield control to event loop
        await asyncio.sleep(0.01)  # Small delay to prevent blocking
    
    return results

# Add background task for heavy operations
async def background_task_manager():
    """Manage background tasks to prevent blocking the main event loop"""
    while True:
        try:
            # Process any pending background tasks
            await asyncio.sleep(0.1)
        except Exception as e:
            logging.error(f"Background task manager error: {e}")
            await asyncio.sleep(1.0)

# Authorization decorators - must be defined before any commands that use them
def is_owner():
    """Custom check to see if the user is the bot owner."""
    def predicate(ctx_or_interaction):
        # Determine the user ID from context or interaction
        user_id = ctx_or_interaction.user.id if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author.id
        if user_id != bot.owner_id:
            # For interactions, we should defer or respond to acknowledge them
            if isinstance(ctx_or_interaction, discord.Interaction):
                if not ctx_or_interaction.response.is_done():
                    asyncio.create_task(ctx_or_interaction.response.send_message("You are not authorized to use this command.", ephemeral=True))
            return False
        return True
    return commands.check(predicate)

def is_admin():
    """Custom check for admin users."""
    async def predicate(ctx_or_interaction):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        # Owner bypasses all checks
        if user.id == bot.owner_id or check_admin_status(user.id):
            return True
        
        # If not authorized, send an ephemeral message
        if isinstance(ctx_or_interaction, discord.Interaction):
            if not ctx_or_interaction.response.is_done():
                await ctx_or_interaction.response.send_message("🤖 You do not have permission to use this command.", ephemeral=True)
        else:
            # For text commands, just send a simple message
            await ctx_or_interaction.send("🤖 You do not have permission to use this command.")
            
        return False
    return commands.check(predicate)

def is_authorized_user():
    """Custom check for authorized users (owner, admin, or user)."""
    async def predicate(ctx_or_interaction):
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        
        # Owner and admins bypass all checks
        if user.id == bot.owner_id or check_admin_status(user.id):
            return True
            
        # For regular authorized users, allow both interactions and text commands
        if is_authorized(user.id):
            return True

        # If not authorized at all, send a message
        if isinstance(ctx_or_interaction, discord.Interaction):
            if not ctx_or_interaction.response.is_done():
                await ctx_or_interaction.response.send_message("🤖 You are not authorized to use this bot.", ephemeral=True)
        else:
            await ctx_or_interaction.send("🤖 You are not authorized to use this bot.")
            
        return False
    return commands.check(predicate)

# Initialize mode
bot_mode = None

# Message storage
pending_rows = deque()

# Load environment variables first
load_dotenv()

# Get configuration from environment variables
OWNER_ID = int(os.getenv('OWNER_ID', 0))
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    raise ValueError("No Discord token found in environment variables")

# Initialize Google Sheets
if not initialize_sheets():
    print("Error: Failed to initialize Google Sheets. Please check your credentials and try again.")
    exit(1)

# Load user roles at startup
load_user_data()
if OWNER_ID and not check_admin_status(OWNER_ID):
    add_user(OWNER_ID, 'admin')
    print(f"Bot owner (ID: {OWNER_ID}) has been automatically added as an admin.")

# Add these at the top with other global variables
last_upload = {
    'rows': [],
    'timestamp': None
}

# Add this near the top with other global variables
active_sheet = 'Sheet1'  # Default sheet

# Add this near the top with other global variables
last_created_sheet = None  # Track the most recently created sheet

# Add this near the top with other global variables
last_created_sheets = []  # Keep track of last 3 created sheets

# In-memory user state for the upload flow
user_upload_state = {}

# Activity logging (no notifications, just storage)
import json

def log_activity(user_id: int, action: str, details: str = "", interaction_type: str = "command", button_label: str = "", sheet_name: str = "", file_name: str = "", order_count: int = 0):
    """Enhanced logging with detailed user interaction tracking"""
    try:
        activity_log = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'action': action,
            'details': details,
            'interaction_type': interaction_type,  # command, button, modal, select
            'button_label': button_label,  # What button was pressed
            'sheet_name': sheet_name,  # Which sheet was affected
            'file_name': file_name,  # File uploaded/processed
            'order_count': order_count,  # Number of orders processed
            'session_id': f"{user_id}_{int(time.time() // 300)}"  # 5-minute session grouping
        }
        
        # Append to activity log file
        with open('activity_log.json', 'a') as f:
            f.write(json.dumps(activity_log) + '\n')
    except Exception as e:
        print(f"Error logging activity: {e}")

def log_button_interaction(interaction: discord.Interaction, action: str, details: str = "", sheet_name: str = "", file_name: str = "", order_count: int = 0):
    """Log button interactions with detailed information"""
    button_label = interaction.data.get('custom_id', '') or interaction.message.components[0].children[0].label if interaction.message.components else "Unknown Button"
    log_activity(
        user_id=interaction.user.id,
        action=action,
        details=details,
        interaction_type="button",
        button_label=button_label,
        sheet_name=sheet_name,
        file_name=file_name,
        order_count=order_count
    )

# Import dashboard after bot is initialized
from dashboard import Dashboard

# Google Sheets setup
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Initialize Google Sheets connection
gc = None
spreadsheet = None
worksheet = None
worksheets = []  # List to store all worksheets

# Function to initialize Google Sheets asynchronously
async def initialize_google_sheets():
    global gc, spreadsheet, worksheet, worksheets
    try:
        print("Attempting to connect to Google Sheets...")
        with tqdm(total=3, desc="Connecting", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}') as pbar:
            # Step 1: Load credentials
            print("Step 1/3: Loading credentials...")
            creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
            time.sleep(0.5)  # Small delay for visual effect
            pbar.update(1)
            
            # Step 2: Authorize with timeout handling
            print("Step 2/3: Authorizing with Google Sheets API...")
            
            # Cross-platform timeout handling
            import threading
            import queue
            import platform
            
            def authorize_with_timeout():
                try:
                    return gspread.authorize(creds)
                except Exception as e:
                    return e
            
            # Use signal-based timeout on Unix systems (macOS, Linux)
            if platform.system() != 'Windows':
                try:
                    import signal
                    
                    def timeout_handler(signum, frame):
                        raise TimeoutError("Google Sheets authorization timed out after 30 seconds")
                    
                    # Set timeout for authorization (30 seconds)
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(30)
                    
                    try:
                        gc = gspread.authorize(creds)
                        signal.alarm(0)  # Cancel the alarm
                    except TimeoutError:
                        signal.alarm(0)  # Cancel the alarm
                        raise Exception("Google Sheets authorization timed out. Please check your internet connection and try again.")
                    except Exception as auth_error:
                        signal.alarm(0)  # Cancel the alarm
                        raise Exception(f"Authorization failed: {str(auth_error)}")
                        
                except ImportError:
                    # Fallback to threading method if signal is not available
                    pass
                else:
                    # Signal method worked, we're done
                    pass
            else:
                # Use threading-based timeout on Windows
                result_queue = queue.Queue()
                thread = threading.Thread(target=lambda: result_queue.put(authorize_with_timeout()))
                thread.daemon = True
                thread.start()
                thread.join(timeout=30)
                
                if thread.is_alive():
                    raise Exception("Google Sheets authorization timed out after 30 seconds. Please check your internet connection.")
                
                result = result_queue.get()
                if isinstance(result, Exception):
                    raise result
                gc = result
            
            time.sleep(0.5)
            pbar.update(1)
            
            # Step 3: Open spreadsheet and get worksheets with timeout
            print("Step 3/3: Opening spreadsheet and loading worksheets...")
            try:
                spreadsheet = gc.open('Successful-Orders')
                worksheet = spreadsheet.sheet1  # Set the default worksheet
                worksheets = spreadsheet.worksheets()
                time.sleep(0.5)
                pbar.update(1)
            except Exception as sheet_error:
                raise Exception(f"Failed to open spreadsheet 'Successful-Orders': {str(sheet_error)}. Please check if the spreadsheet exists and is shared with the service account.")
        
        # Check headers in each sheet silently
        print("Setting up sheet headers...")
        headers = [
            'Date',
            'Time',
            'Product',
            'Price',
            'Quantity',
            'Profile',
            'Proxy List',
            'Order Number',
            'Email'
        ]
        
        for sheet in worksheets:
            try:
                existing_headers = sheet.row_values(1)
                if not existing_headers:
                    sheet.append_row(headers)
            except Exception as header_error:
                print(f"Warning: Could not set up headers for sheet {sheet.title}: {str(header_error)}")
        
        print("Successfully connected to Google Sheets!")
    except Exception as e:
        print(f"Error connecting to Google Sheets: {e}")
        print("Troubleshooting steps:")
        print("1. Check if credentials.json exists and is valid")
        print("2. Verify the service account has access to the 'Successful-Orders' spreadsheet")
        print("3. Check your internet connection")
        print("4. Try restarting the bot")
        gc = None
        spreadsheet = None
        worksheet = None
        worksheets = []

# Google Sheets will be initialized after bot is ready

# Add rate limiting and API error handling
def safe_sheets_operation(func):
    async def wrapper(*args, **kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except gspread.exceptions.APIError as e:
                if e.response.status_code == 429:  # Quota exceeded
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) + random.uniform(0, 1)  # Exponential backoff
                        logging.warning(f"API quota exceeded, retrying in {wait_time:.1f} seconds... (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logging.error(f"API quota exceeded after {max_retries} attempts: {str(e)}")
                        raise e
                else:
                    logging.error(f"Google Sheets API Error: {str(e)}")
                    raise e
            except Exception as e:
                logging.error(f"Error in {func.__name__}: {str(e)}\n{traceback.format_exc()}")
                raise e
    return wrapper

# Helper function to safely batch update sheets with rate limiting
async def safe_batch_update(sheet, updates_list, sheet_name=""):
    """Safely perform batch updates with rate limiting and retries"""
    max_retries = 3  # Reduced retries for better performance
    for attempt in range(max_retries):
        try:
            # Use rate limiter for Google Sheets API
            await sheets_rate_limiter.acquire('batch_update')
            
            # Process large batches in chunks to prevent blocking
            if len(updates_list) > 100:
                chunk_size = 50
                for i in range(0, len(updates_list), chunk_size):
                    chunk = updates_list[i:i + chunk_size]
                    await asyncio.to_thread(sheet.batch_update, chunk)
                    await asyncio.sleep(0.1)  # Small delay between chunks
            else:
                await asyncio.to_thread(sheet.batch_update, updates_list)
            
            logging.info(f"Successfully applied batch updates to sheet {sheet.title}")
            return True
        except Exception as e:
            if is_likely_connection_error(e):
                logging.error(f"Connection error during batch update for sheet {sheet.title}: {str(e)}")
                raise e # Re-raise to be caught by the calling function.
            elif isinstance(e, gspread.exceptions.APIError) and e.response.status_code == 429:  # Rate limit
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(1, 3)  # Reduced exponential backoff
                    logging.warning(f"Rate limit hit updating sheet {sheet.title}, retrying in {wait_time:.1f} seconds... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logging.error(f"Rate limit hit updating sheet {sheet.title} after {max_retries} attempts: {str(e)}")
                    raise e
            else:
                logging.error(f"Unexpected error during batch update for sheet {sheet.title}: {str(e)}")
                raise e

# Add this function to safely update individual cells with rate limiting
async def safe_update_cell(sheet, cell, value):
    """Safely update a single cell with rate limiting and retries"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            await asyncio.sleep(1.0)  # 1 second delay between updates
            await asyncio.to_thread(sheet.update, cell, value)
            await asyncio.sleep(0.5)  # Small delay after update
            return True
        except Exception as e:
            if is_likely_connection_error(e):
                logging.error(f"Connection error updating cell {cell} in sheet {sheet.title}: {str(e)}")
                raise e # Re-raise to be caught by the calling function.
            elif isinstance(e, gspread.exceptions.APIError) and e.response.status_code == 429:  # Rate limit
                if attempt < max_retries - 1:
                    wait_time = (3 ** attempt) + random.uniform(3, 8)
                    logging.warning(f"Rate limit hit updating cell {cell} in sheet {sheet.title}, retrying in {wait_time:.1f} seconds... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logging.error(f"Rate limit hit updating cell {cell} in sheet {sheet.title} after {max_retries} attempts: {str(e)}")
                    raise e
            else:
                logging.error(f"Unexpected error updating cell {cell} in sheet {sheet.title}: {str(e)}")
                raise e

# Add this function to safely get sheet values with rate limiting
async def safe_get_sheet_values(sheet):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await asyncio.sleep(0.5)  # Increased delay to 0.5 seconds
            return await asyncio.to_thread(sheet.get_all_values)
        except Exception as e:
            if is_likely_connection_error(e):
                logging.error(f"Connection error getting sheet values from {sheet.title}: {str(e)}")
                raise e # Re-raise to be caught by the calling function.
            elif isinstance(e, gspread.exceptions.APIError) and e.response.status_code == 429:  # Rate limit
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(1, 3)
                    logging.warning(f"Rate limit hit while reading sheet {sheet.title}, retrying in {wait_time:.1f} seconds... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logging.error(f"Rate limit hit while reading sheet {sheet.title} after {max_retries} attempts: {str(e)}")
                    raise e
            else:
                logging.error(f"Error getting sheet values from {sheet.title}: {str(e)}")
                raise e

# Modify get_all_orders to use safe operation
async def get_all_orders():
    """Get all orders from all sheets with error handling"""
    all_orders = []
    for sheet in worksheets:
        try:
            values = await safe_get_sheet_values(sheet)
            if values:
                all_orders.extend(values[1:])  # Skip header row
        except Exception as e:
            logging.error(f"Error reading sheet {sheet.title}: {str(e)}")
    return all_orders

def parse_message(text):
    """Extract data from a single message"""
    try:
        data = {}
        
        # Extract each field using updated regex patterns
        product_match = re.search(r'Product\n(.*?)(?:\n|$)', text)
        price_match = re.search(r'Price\n\$(.*?)(?:\n|$)', text)
        profile_match = re.search(r'Profile\n(.*?)(?:\n|$)', text)
        proxy_match = re.search(r'Proxy (?:List|Details)\n(.*?)(?:\n|$)', text)
        order_match = re.search(r'Order Number\n#?(.*?)(?:\n|$)', text)  # Made # optional
        email_match = re.search(r'Email\n(.*?)(?:\n|$)', text)
        quantity_match = re.search(r'Quantity\n(.*?)(?:\n|$)', text)
        
        # Extract data with fallbacks
        data['Product'] = product_match.group(1) if product_match else ''
        data['Price'] = price_match.group(1) if price_match else ''
        data['Profile'] = profile_match.group(1) if profile_match else ''
        data['Proxy List'] = proxy_match.group(1) if proxy_match else ''
        data['Order Number'] = order_match.group(1) if order_match else ''
        data['Email'] = email_match.group(1) if email_match else ''
        data['Quantity'] = quantity_match.group(1) if quantity_match else '1'
        
        # Debug logging for proxy list extraction
        if not data['Proxy List']:
            logging.warning(f"Proxy List not found in message. Text preview: {text[:200]}...")
            # Try alternate patterns
            alt_proxy_patterns = [
                r'Proxy (?:List|Details):(.*?)(?:\n|$)',  # With colon
                r'Proxy\n(.*?)(?:\n|$)',      # Short form with newline
                r'Proxy:(.*?)(?:\n|$)',       # Short form with colon
                r'Proxies\n(.*?)(?:\n|$)',    # Plural form
                r'proxy (?:list|details)\n(.*?)(?:\n|$)', # Lowercase
                r'Proxy (?:List|Details)\s+(.*?)(?:\n|$)' # With extra spaces
            ]
            for i, pattern in enumerate(alt_proxy_patterns):
                alt_match = re.search(pattern, text, re.IGNORECASE)
                if alt_match:
                    data['Proxy List'] = alt_match.group(1).strip()
                    logging.info(f"Found proxy list using alternate pattern {i+1}: '{data['Proxy List']}'")
                    break
        
        # Clean up the data
        data = {k: v.strip() for k, v in data.items()}
        
        # Validate data
        if not data['Product'] or not data['Price']:
            logging.error("Missing required fields: Product or Price")
            return None
            
        if not validate_price(data['Price']):
            logging.error(f"Invalid price format: {data['Price']}")
            return None
            
        if not validate_quantity(data['Quantity']):
            logging.error(f"Invalid quantity: {data['Quantity']}")
            return None
            
        if data['Email'] and not validate_email(data['Email']):
            logging.warning(f"Invalid email format: {data['Email']}")
            
        # Log successful parse
        logging.info(f"Successfully parsed order: {data['Product']} - ${data['Price']} x {data['Quantity']}")
        
        return data
    except Exception as e:
        logging.error(f"Error parsing message: {str(e)}")
        return None

async def process_rows():
    global worksheet, pending_rows
    
    while True:
        if pending_rows:
            try:
                # Process all pending rows at once
                rows = list(pending_rows)
                pending_rows.clear()
                
                # Use chunking for large batches
                if len(rows) > 100:
                    await chunk_operation(
                        rows, 
                        chunk_size=50,
                        operation_func=lambda chunk: asyncio.create_task(process_row_chunk(chunk))
                    )
                else:
                    await process_row_chunk(rows)
                
                print(f"Added batch of {len(rows)} rows to spreadsheet")
                
            except Exception as e:
                print(f"Error batch processing rows: {e}")
                # Put rows back if there was an error
                pending_rows.extend(rows)
        
        await asyncio.sleep(0.05)  # Reduced from 0.1 to 0.05 seconds

async def process_row_chunk(rows):
    """Process a chunk of rows with rate limiting"""
    await sheets_rate_limiter.acquire('append_rows')
    worksheet.append_rows(rows)

@bot.event
async def on_ready():
    global bot_mode
    print(f'\nLogged in as {bot.user}')
    print("\n🤖 Discord Order Bot is ready!")
    print(f"Version: 2.0.1 | Mode: {'Production' if bot_mode == 'production' else 'Development'}")
    print(f"Memory Usage: {get_memory_usage():.2f} MB")
    
    # Apply Discord rate limiting patches
    print("🔄 Applying Discord rate limiting patches...")
    patch_discord_methods()
    print("✅ Discord rate limiting enabled")
    
    # Start background task manager for performance optimization
    print("🔄 Starting background task manager...")
    bot.loop.create_task(background_task_manager())
    
    # Start Google Sheets initialization in background
    print("🔄 Initializing Google Sheets connection...")
    bot.loop.create_task(initialize_google_sheets())
    
    # Register the persistent view so it works after restarts
    bot.add_view(WelcomeView(bot))
    
    # Auto-configure the owner's spreadsheet if it's not set up yet
    if OWNER_ID and needs_setup(OWNER_ID):
        print("Attempting to auto-configure owner's default spreadsheet...")
        try:
            # This uses the fallback in get_spreadsheet to open 'Successful-Orders'
            # Already imported at top
            default_sheet = await get_spreadsheet() 
            if default_sheet:
                set_user_spreadsheet(OWNER_ID, default_sheet.id, default_sheet.title)
                print(f"✅ Automatically configured '{default_sheet.title}' for the bot owner.")
            else:
                print("⚠️ Could not open the default 'Successful-Orders' sheet. Owner will need to set it up manually via the prompt.")
        except Exception as e:
            print(f"❌ Error during owner's sheet auto-configuration: {e}")

    # Start dashboard task if in production
    if bot_mode == 'production':
        print("Starting production dashboard task...")
        bot.loop.create_task(update_dashboard_task())
    
    # Send startup notification to owner
    if bot_mode == 'production':
        try:
            owner = await safe_discord_call(bot.fetch_user, OWNER_ID, call_type='user_fetch')
            if owner:
                await owner.send("**✅ Bot is online and ready!**")
                print("✅ Startup notification sent to owner.")
        except Exception as e:
            print(f"❌ Could not send startup notification: {e}")
            
    # Set up the custom logging handler to send errors to the owner
    try:
        handler = DiscordHandler(bot, OWNER_ID)
        logging.getLogger().addHandler(handler)
        if bot_mode == 'production':
             print("✅ Discord logging handler added!")
    except Exception as e:
        print(f"❌ Error setting up Discord logging handler: {e}")
    
    # Start performance monitoring
    try:
        from performance_monitor import PerformanceMonitor
        monitor = PerformanceMonitor(bot)
        bot.loop.create_task(monitor.start_monitoring())
        print("✅ Performance monitoring started!")
    except Exception as e:
        print(f"❌ Error starting performance monitoring: {e}")

@bot.event
async def on_message(message):
    # Use the global datetime import
    
    # Ignore messages from the bot itself to prevent infinite loops
    if message.author == bot.user:
        return

    # Log every incoming message for debugging
    logging.info(f"Received message from {message.author.name} ({message.author.id}): {message.content[:50]}...")

    # --- Start of DM-based file upload flows ---
    if isinstance(message.channel, discord.DMChannel) and message.attachments and message.author.id in user_upload_state:
        # Get the correct spreadsheet for the user who sent the message
        try:
            user_spreadsheet = await get_spreadsheet(user_id=message.author.id)
            if not user_spreadsheet:
                await message.channel.send("❌ Your Google Sheet is not configured correctly. Please try setting it up again.")
                user_upload_state.pop(message.author.id, None)
                return
        except Exception as e:
            await message.channel.send(f"❌ Could not access your Google Sheet: {str(e)}")
            user_upload_state.pop(message.author.id, None)
            return

        state = user_upload_state[message.author.id]
        
        # --- Cancel Orders Button Flow (OPTIMIZED) ---
        if 'cancel_sheet_choice' in state or 'cancel_sheet_choices' in state:
            attachment = message.attachments[0]
            if not (attachment.filename.endswith('.csv') or attachment.filename.endswith('.txt')):
                await message.channel.send("❌ Please attach a CSV or TXT file for cancellation.")
                user_upload_state.pop(message.author.id, None)
                return
            
            # Log file upload for cancellation
            log_activity(
                user_id=message.author.id,
                action="Uploaded file for cancellation",
                details=f"File: {attachment.filename}",
                interaction_type="file_upload",
                file_name=attachment.filename,
                order_count=0
            )
            
            try:
                # Initialize the optimized OrderCancellation handler
                cancellation_handler = OrderCancellation(user_upload_state)
                cancellation_handler.message = message
                cancellation_handler.user_id = message.author.id
                
                # Determine which sheets to process
                sheet_names = []
                if 'cancel_sheet_choices' in state:
                    # New flow - multiple sheets
                    sheet_names = state['cancel_sheet_choices']
                elif 'cancel_sheet_choice' in state:
                    # Legacy flow - single sheet handling
                    choice = state['cancel_sheet_choice']
                    if choice == 'sheet1':
                        sheet_names = ['Sheet1']
                    elif choice.startswith('existing:'):
                        sheet_names = [choice.split(':', 1)[1]]
                    elif choice == 'cancel_new':
                        sheet_name = state.get('new_sheet_name')
                        if sheet_name:
                            sheet_names = [sheet_name]
                    elif choice == 'cancel_both':
                        sheet_names = ['Sheet1']
                        if state.get('new_sheet_name'):
                            sheet_names.append(state['new_sheet_name'])
                    elif choice == 'multiple':
                        sheet_names = state.get('selected_sheets', [])
                
                if not sheet_names:
                    await message.channel.send("❌ No sheets selected for cancellation.")
                    user_upload_state.pop(message.author.id, None)
                    return
                
                # Process cancellations using the optimized handler
                if len(sheet_names) == 1:
                    success = await cancellation_handler.process_cancellation_file(attachment, sheet_names[0])
                else:
                    success = await cancellation_handler.process_multiple_sheets(attachment, sheet_names)
                
                # Clean up
                user_upload_state.pop(message.author.id, None)
                
                if success:
                    log_activity(
                        user_id=message.author.id,
                        action="Cancelled orders",
                        details=f"Processed {len(sheet_names)} sheet(s)",
                        interaction_type="cancellation",
                        file_name=attachment.filename,
                        order_count=0
                    )
                
                return
                
            except Exception as e:
                logging.error(f"Error in optimized cancel flow: {str(e)}")
                await message.channel.send(f"❌ Error processing cancellation: {str(e)}")
                user_upload_state.pop(message.author.id, None)
                return
        
        # --- End Cancel Orders Button Flow ---
        # --- Tracking Button Flow ---
        if 'tracking_sheet_choice' in state:
            attachment = message.attachments[0]
            if not attachment.filename.endswith('.csv'):
                await message.channel.send("❌ Please attach a CSV file for tracking update.")
                user_upload_state.pop(message.author.id, None)
                return
            
            # Log file upload for tracking
            log_activity(
                user_id=message.author.id,
                action="Uploaded file for tracking update",
                details=f"File: {attachment.filename}",
                interaction_type="file_upload",
                file_name=attachment.filename,
                order_count=0
            )
            try:
                csv_content = await attachment.read()
                csv_text = csv_content.decode('utf-8')
                csv_rows = list(csv.DictReader(csv_text.splitlines()))
                if not csv_rows:
                    await message.channel.send("❌ The CSV file is empty")
                    user_upload_state.pop(message.author.id, None)
                    return
                # Check for order column (flexible naming)
                order_col = None
                tracking_col = None
                headers = list(csv_rows[0].keys())
                
                # Look for order column variations
                for header in headers:
                    header_lower = header.lower().strip()
                    if header_lower in ['order', 'order number', 'order_number']:
                        order_col = header
                        break
                
                # Look for tracking column variations  
                for header in headers:
                    header_lower = header.lower().strip()
                    if header_lower in ['tracking', 'tracking number', 'tracking_number']:
                        tracking_col = header
                        break
                
                if not order_col or not tracking_col:
                    missing = []
                    if not order_col:
                        missing.append("Order column (accepted: 'Order', 'Order Number', or 'order_number')")
                    if not tracking_col:
                        missing.append("Tracking column (accepted: 'Tracking', 'Tracking Number', or 'tracking_number')")
                    
                    await message.channel.send(
                        f"❌ Invalid CSV format. Missing required columns:\n• " + "\n• ".join(missing)
                    )
                    user_upload_state.pop(message.author.id, None)
                    return
                # Helper to process a single sheet
                async def process_tracking_on_sheet(target_sheet, sheet_label, csv_rows, order_col, tracking_col):
                    """Inner function to process tracking for a single sheet"""
                    try:
                        all_sheet_data = await safe_get_sheet_values(target_sheet)
                        if not all_sheet_data:
                            await message.channel.send(f"⚠️ Sheet `{sheet_label}` is empty.")
                            return 0, [], [], []
                        all_sheet_data = await safe_get_sheet_values(target_sheet)
                        
                        header = all_sheet_data[0]
                        
                        # Find the 'Order Number' and 'Tracking' columns (flexible naming)
                        order_col_index = None
                        tracking_col_index = None
                        
                        for idx, col_name in enumerate(header):
                            col_lower = col_name.lower().strip()
                            if col_lower in ['order number', 'order', 'order_number']:
                                order_col_index = idx
                            elif col_lower in ['tracking', 'tracking number', 'tracking_number']:
                                tracking_col_index = idx
                        
                        # Check if required columns exist
                        if order_col_index is None:
                            missing = []
                            missing.append("Order column (accepted: 'Order', 'Order Number', or 'order_number')")
                            if tracking_col_index is None:
                                missing.append("Tracking column (accepted: 'Tracking', 'Tracking Number', or 'tracking_number')")
                            
                            await message.channel.send(f"❌ Sheet `{sheet_label}` is missing: " + ", ".join(missing))
                            return 0, [], [], []
                        
                        # Auto-create tracking column if it doesn't exist
                        if tracking_col_index is None:
                            # Find email column (N) to add tracking after it
                            email_col_index = None
                            for idx, col_name in enumerate(header):
                                col_lower = col_name.lower().strip()
                                if col_lower == 'email':
                                    email_col_index = idx
                                    break
                            
                            # Add Tracking Number column after email column (N) or at the end if email not found
                            insert_pos = email_col_index + 1 if email_col_index is not None else len(header)
                            header.insert(insert_pos, 'Tracking Number')
                            tracking_col_index = insert_pos
                            
                            # Update sheet headers
                            await asyncio.to_thread(target_sheet.update, 'A1', [header])
                            all_sheet_data = await safe_get_sheet_values(target_sheet)
                            header = all_sheet_data[0]
                            
                            await message.channel.send(f"✅ Added 'Tracking Number' column to {sheet_label} after email column")
                        
                        # Create a mapping of order number to its row index for quick lookups
                        # Skip header row (index 0) and use case-insensitive matching with stripped values
                        order_to_row_map = {}
                        for i, row in enumerate(all_sheet_data[1:], start=2):  # Start from row 2 (skip header)
                            if len(row) > order_col_index and row[order_col_index].strip():
                                order_key = row[order_col_index].strip().lower()
                                order_to_row_map[order_key] = i
                        
                        # Debug logging
                        logging.info(f"Sheet {sheet_label}: Found {len(order_to_row_map)} orders")
                        if order_to_row_map:
                            sample_sheet_orders = list(order_to_row_map.keys())[:3]
                            logging.info(f"Sample sheet orders: {sample_sheet_orders}")
                        
                        # First, group all tracking numbers by order number
                        # This handles cases where one order has multiple shipments/tracking numbers
                        order_tracking_map = {}  # {order_number: [tracking1, tracking2, ...]}
                        
                        for row in csv_rows:
                            order_number = row[order_col].strip()
                            tracking_number = row[tracking_col].strip()
                            
                            if not order_number or not tracking_number:
                                continue
                            
                            if order_number not in order_tracking_map:
                                order_tracking_map[order_number] = []
                            
                            # Only add if not already in the list (avoid duplicates)
                            if tracking_number not in order_tracking_map[order_number]:
                                order_tracking_map[order_number].append(tracking_number)
                        
                        # Debug logging
                        logging.info(f"CSV: Found {len(order_tracking_map)} unique orders")
                        if order_tracking_map:
                            sample_csv_orders = list(order_tracking_map.keys())[:3]
                            logging.info(f"Sample CSV orders: {sample_csv_orders}")
                        
                        # Now process each unique order number
                        updated_count = 0
                        already_had_tracking = []
                        not_found_orders = []
                        updated_tracking_numbers = []
                        batch_updates = []
                        multi_tracking_orders = []  # Track orders with multiple tracking numbers
                        
                        for order_number, tracking_list in order_tracking_map.items():
                            # Use lowercase for case-insensitive lookup
                            order_key = order_number.strip().lower()
                            if order_key in order_to_row_map:
                                row_index = order_to_row_map[order_key]
                                # Check if tracking is already present
                                existing_tracking = all_sheet_data[row_index - 1][tracking_col_index] if len(all_sheet_data[row_index - 1]) > tracking_col_index else ""
                                
                                # Parse existing tracking numbers (may be comma-separated)
                                existing_tracking_list = []
                                if existing_tracking and existing_tracking.strip():
                                    # Split by comma and clean up each tracking number
                                    existing_tracking_list = [t.strip() for t in existing_tracking.split(',') if t.strip()]
                                
                                # Combine existing and new tracking numbers, removing duplicates while preserving order
                                all_trackings = existing_tracking_list.copy()
                                for new_tracking in tracking_list:
                                    if new_tracking not in all_trackings:
                                        all_trackings.append(new_tracking)
                                
                                # ONLY update if there are NEW tracking numbers to add
                                # This prevents unnecessary updates when all CSV trackings already exist in the sheet
                                if len(all_trackings) > len(existing_tracking_list):
                                    # Combine all tracking numbers with comma separator
                                    combined_tracking = ", ".join(all_trackings)
                                    
                                    # Update the 'Tracking' column for the matched row
                                    batch_updates.append({
                                        'range': f"{gspread.utils.rowcol_to_a1(row_index, tracking_col_index + 1)}",
                                        'values': [[combined_tracking]]
                                    })
                                    updated_count += 1
                                    
                                    # Track the new tracking numbers that were added
                                    new_trackings = [t for t in tracking_list if t not in existing_tracking_list]
                                    updated_tracking_numbers.extend(new_trackings)
                                    
                                    # Track if this order has multiple tracking numbers
                                    if len(all_trackings) > 1:
                                        multi_tracking_orders.append(f"{order_number} ({len(all_trackings)} trackings total, {len(new_trackings)} new)")
                                else:
                                    # All tracking numbers from CSV already exist in the sheet
                                    already_had_tracking.append(order_number)
                            else:
                                not_found_orders.append(order_number)
                                # Debug: log first few not-found orders
                                if len(not_found_orders) <= 3:
                                    logging.warning(f"Order not found in sheet: '{order_number}' (key: '{order_key}')")

                        # Apply batch updates if any
                        if batch_updates:
                            try:
                                # Use batch update to reduce API calls
                                await safe_batch_update(target_sheet, batch_updates, sheet_label)
                            except Exception as e:
                                logging.error(f"Batch update failed, falling back to individual updates: {str(e)}")
                                # Fallback to individual updates
                                for update in batch_updates:
                                    try:
                                        await safe_update_cell(target_sheet, update['range'], update['values'])
                                    except Exception as cell_error:
                                        logging.error(f"Failed to update cell {update['range']}: {str(cell_error)}")
                        # Build summary message
                        summary_parts = [f"✅ {updated_count} orders updated in {sheet_label}"]
                        
                        if multi_tracking_orders:
                            summary_parts.append(f"📦 {len(multi_tracking_orders)} orders with multiple tracking numbers:")
                            # Show first 5 multi-tracking orders
                            for order_info in multi_tracking_orders[:5]:
                                summary_parts.append(f"  • {order_info}")
                            if len(multi_tracking_orders) > 5:
                                summary_parts.append(f"  • ... and {len(multi_tracking_orders) - 5} more")
                        
                        if already_had_tracking:
                            summary_parts.append(f"ℹ️ Already up-to-date (no new tracking numbers): {len(already_had_tracking)}")
                        
                        if not_found_orders:
                            summary_parts.append(f"⚠️ Not found in sheet: {len(not_found_orders)}")
                            if len(not_found_orders) <= 5:
                                summary_parts.append(f"  Orders: {', '.join(not_found_orders)}")
                        
                        await message.channel.send("\n".join(summary_parts))
                        return updated_count, already_had_tracking, not_found_orders, updated_tracking_numbers
                    except Exception as e:
                        await message.channel.send(f"❌ Error updating tracking in {sheet_label}: {str(e)}")
                        return 0, [], [], []
                # Determine which sheet(s) to use
                updated_total = 0
                already_had = []
                not_found = []
                all_tracking_numbers = []
                if state['tracking_sheet_choice'] == 'sheet1':
                    # Get the user's specific spreadsheet
                    user_spreadsheet = await get_spreadsheet(user_id=message.author.id)
                    if not user_spreadsheet:
                        await message.channel.send("❌ Your Google Sheet is not configured correctly. Please try setting it up again.")
                        user_upload_state.pop(message.author.id, None)
                        return
                    user_sheet1 = user_spreadsheet.worksheet('Sheet1')
                    count, had, nf, trackings = await process_tracking_on_sheet(user_sheet1, 'Sheet1', csv_rows, order_col, tracking_col)
                    updated_total += count
                    already_had += had
                    not_found += nf
                    all_tracking_numbers.extend(trackings)
                elif state['tracking_sheet_choice'].startswith('existing:'):
                    sheet_name = state['tracking_sheet_choice'].split(':', 1)[1]
                    try:
                        # Get the user's specific spreadsheet
                        user_spreadsheet = await get_spreadsheet(user_id=message.author.id)
                        if not user_spreadsheet:
                            await message.channel.send("❌ Your Google Sheet is not configured correctly. Please try setting it up again.")
                            user_upload_state.pop(message.author.id, None)
                            return
                        target_sheet = user_spreadsheet.worksheet(sheet_name)
                        count, had, nf, trackings = await process_tracking_on_sheet(target_sheet, sheet_name, csv_rows, order_col, tracking_col)
                        updated_total += count
                        already_had += had
                        not_found += nf
                        all_tracking_numbers.extend(trackings)
                    except Exception as e:
                        await message.channel.send(f"❌ Sheet '{sheet_name}' not found: {str(e)}")
                elif state['tracking_sheet_choice'] == 'tracking_new':
                    sheet_name = state.get('new_sheet_name')
                    if not sheet_name:
                        await message.channel.send("❌ No custom sheet name provided.")
                    else:
                        try:
                            # Get the user's specific spreadsheet
                            user_spreadsheet = await get_spreadsheet(user_id=message.author.id)
                            if not user_spreadsheet:
                                await message.channel.send("❌ Your Google Sheet is not configured correctly. Please try setting it up again.")
                                user_upload_state.pop(message.author.id, None)
                                return
                            target_sheet = user_spreadsheet.worksheet(sheet_name)
                            count, had, nf, trackings = await process_tracking_on_sheet(target_sheet, sheet_name, csv_rows, order_col, tracking_col)
                            updated_total += count
                            already_had += had
                            not_found += nf
                            all_tracking_numbers.extend(trackings)
                        except Exception as e:
                            await message.channel.send(f"❌ Sheet '{sheet_name}' not found: {str(e)}")
                elif state['tracking_sheet_choice'] == 'tracking_both':
                    # Get the user's specific spreadsheet
                    user_spreadsheet = await get_spreadsheet(user_id=message.author.id)
                    if not user_spreadsheet:
                        await message.channel.send("❌ Your Google Sheet is not configured correctly. Please try setting it up again.")
                        user_upload_state.pop(message.author.id, None)
                        return
                    # Sheet1
                    user_sheet1 = user_spreadsheet.worksheet('Sheet1')
                    count, had, nf, trackings = await process_tracking_on_sheet(user_sheet1, 'Sheet1', csv_rows, order_col, tracking_col)
                    updated_total += count
                    already_had += had
                    not_found += nf
                    all_tracking_numbers.extend(trackings)
                    # Custom
                    sheet_name = state.get('new_sheet_name')
                    if not sheet_name:
                        await message.channel.send("❌ No custom sheet name provided for second sheet.")
                    else:
                        try:
                            target_sheet = user_spreadsheet.worksheet(sheet_name)
                            count, had, nf, trackings = await process_tracking_on_sheet(target_sheet, sheet_name, csv_rows, order_col, tracking_col)
                            updated_total += count
                            already_had += had
                            not_found += nf
                            all_tracking_numbers.extend(trackings)
                        except Exception as e:
                            await message.channel.send(f"❌ Sheet '{sheet_name}' not found: {str(e)}")
                elif state['tracking_sheet_choice'] == 'multiple':
                    # Process multiple sheets
                    selected_sheets = state.get('selected_sheets', [])
                    if not selected_sheets:
                        await message.channel.send("❌ No sheets selected for multiple processing.")
                        user_upload_state.pop(message.author.id, None)
                        return
                    # Get the user's specific spreadsheet
                    user_spreadsheet = await get_spreadsheet(user_id=message.author.id)
                    if not user_spreadsheet:
                        await message.channel.send("❌ Your Google Sheet is not configured correctly. Please try setting it up again.")
                        user_upload_state.pop(message.author.id, None)
                        return
                    # Show initial progress message
                    progress_msg = await message.channel.send(f"🔄 Processing {len(selected_sheets)} sheets...")
                    per_sheet_results = []
                    found_anywhere = set()
                    already_had_anywhere = set()
                    for i, sheet_name in enumerate(selected_sheets, 1):
                        try:
                            await progress_msg.edit(content=f"🔄 Processing sheet {i}/{len(selected_sheets)}: {sheet_name}")
                            # Get the sheet from user's spreadsheet
                            target_sheet = user_spreadsheet.worksheet(sheet_name)
                            # Pass a fresh copy of csv_rows to each call
                            count, had, nf, trackings = await process_tracking_on_sheet(target_sheet, sheet_name, csv_rows, order_col, tracking_col)
                            updated_total += count
                            all_tracking_numbers.extend(trackings)
                            # Track which orders were found in this sheet (updated or already had tracking)
                            found_in_this_sheet = set()
                            for row in csv_rows:
                                order_number = row[order_col].strip()
                                if order_number not in nf:
                                    found_in_this_sheet.add(order_number)
                            found_anywhere.update(found_in_this_sheet)
                            for order in had:
                                already_had_anywhere.add(order)
                            per_sheet_results.append((sheet_name, count, had, nf))
                        except gspread.exceptions.WorksheetNotFound:
                            await message.channel.send(f"⚠️ Sheet `{sheet_name}` not found. Skipping.")
                            continue
                        except Exception as e:
                            if is_likely_connection_error(e):
                                await message.channel.send(f"❌ **Connection Error**: Could not process sheet `{sheet_name}`. Aborting operation.")
                                break # Stop processing more sheets
                            await message.channel.send(f"⚠️ Error processing sheet '{sheet_name}': {str(e)}. Continuing with remaining sheets...")
                            continue
                    # Calculate truly not found orders (not found in any sheet)
                    all_order_numbers = set(row[order_col].strip() for row in csv_rows)
                    not_found_anywhere = list(all_order_numbers - found_anywhere)
                    # Show final summary for multiple sheets
                    view_to_send = None
                    if per_sheet_results:
                        summary_lines = []
                        for sheet_name, updated_count, already_had_list, not_found_list in per_sheet_results:
                            # Only count as 'not found' those not found in any sheet
                            truly_not_found = [order for order in not_found_list if order in not_found_anywhere]
                            line = f"**{sheet_name}**: {updated_count} updated"
                            if already_had_list:
                                line += f", {len(already_had_list)} already had tracking"
                            if truly_not_found:
                                line += f", {len(truly_not_found)} not found"
                            summary_lines.append(line)
                        summary_text = f"✅ **Multi-Sheet Tracking Complete**\n\n**Total Orders Updated:** {updated_total}\n\n**Results by Sheet:**\n" + "\n".join(summary_lines)
                        if not_found_anywhere:
                            summary_text += f"\n\n❌ {len(not_found_anywhere)} order(s) not found in any sheet."
                            view_to_send = ViewAllOrdersView("View All Not Found (Any Sheet)", not_found_anywhere, "Not found in any sheet")
                        await progress_msg.edit(content=summary_text, view=view_to_send)
                    else:
                        await progress_msg.edit(content="❌ No orders were found or updated in any of the selected sheets.")
                    # Show copy button if any tracking numbers were updated
                    if all_tracking_numbers:
                        await message.channel.send(
                            f"📋 **{len(all_tracking_numbers)} tracking numbers updated!**\nClick the button below to copy all tracking numbers to clipboard:",
                            view=CopyTrackingView(all_tracking_numbers)
                        )
                    user_upload_state.pop(message.author.id, None)
                    return
                user_upload_state.pop(message.author.id, None)
                return
            except Exception as e:
                await message.channel.send(f"❌ Error processing tracking file: {str(e)}")
                user_upload_state.pop(message.author.id, None)
                return
        # --- End Tracking Button Flow ---
        # --- Order Upload Button Flow ---
        if 'sheet_choice' in state:
            attachment = message.attachments[0]
            if not attachment.filename.endswith('.txt'):
                await message.channel.send("❌ Please attach a .txt file with orders.")
                user_upload_state.pop(message.author.id, None)
                return
            
            # Log file upload for order processing
            log_activity(
                user_id=message.author.id,
                action="Uploaded file for order processing",
                details=f"File: {attachment.filename}",
                interaction_type="file_upload",
                file_name=attachment.filename,
                order_count=0
            )
            try:
                content = await attachment.read()
                content = content.decode('utf-8')
                messages = content.split("Successful Checkout")
                messages = [msg.strip() for msg in messages if msg.strip()]
                if not messages:
                    await message.channel.send("❌ No orders found in file.")
                    user_upload_state.pop(message.author.id, None)
                    return
                # Progress feedback
                progress_msg = await message.channel.send(f"📦 Processing {len(messages)} orders... Please wait.")
                rows_to_add = []
                failed = []
                for i, msg in enumerate(messages, 1):
                    msg = "Successful Checkout" + msg
                    order_data = parse_message(msg)
                    if order_data:
                        now = datetime.now()
                        
                        # Format price as currency
                        try:
                            price_value = float(order_data['Price'])
                            formatted_price = f"${price_value:,.2f}"
                        except (ValueError, TypeError):
                            formatted_price = order_data['Price']  # Keep original if can't parse
                        
                        # Format quantity as integer
                        try:
                            qty_value = int(order_data['Quantity'])
                            formatted_qty = qty_value
                        except (ValueError, TypeError):
                            formatted_qty = order_data['Quantity']  # Keep original if can't parse
                        
                        row = [
                            now.strftime('%Y-%m-%d'),
                            now.strftime('%I:%M:%S %p'),
                            order_data['Product'],
                            formatted_price,
                            formatted_qty,
                            order_data['Profile'],
                            order_data['Proxy List'],
                            order_data['Order Number'],
                            order_data['Email']
                        ]
                        rows_to_add.append(row)
                    else:
                        failed.append(f"Order {i}: Invalid format")
                    # Update progress every 25 orders or at the end
                    if i % 25 == 0 or i == len(messages):
                        progress = int((i / len(messages)) * 100)
                        bar_length = 20
                        filled_length = int(bar_length * i // len(messages))
                        bar = '█' * filled_length + '░' * (bar_length - filled_length)
                        await progress_msg.edit(content=f"```\nProgress: [{bar}] {progress}%\nProcessed {i}/{len(messages)} orders...\n{len(rows_to_add)} valid, {len(failed)} failed\n```")
                # Upload to the selected sheet
                try:
                    # Get the user's specific spreadsheet
                    user_spreadsheet = await get_spreadsheet(user_id=message.author.id)
                    if not user_spreadsheet:
                        await message.channel.send("❌ Your Google Sheet is not configured correctly. Please try setting it up again.")
                        user_upload_state.pop(message.author.id, None)
                        return
                    
                    if state['sheet_choice'] == 'sheet1':
                        # Get Sheet1 from the user's spreadsheet
                        user_sheet1 = user_spreadsheet.worksheet('Sheet1')
                        user_sheet1.append_rows(rows_to_add)
                        sheet_name = "Sheet1"
                    elif state['sheet_choice'].startswith('existing:'):
                        sheet_name = state['sheet_choice'].split(':', 1)[1]
                        target_sheet = user_spreadsheet.worksheet(sheet_name)
                        target_sheet.append_rows(rows_to_add)
                    elif state['sheet_choice'] == 'new' or state['sheet_choice'] == 'both':
                        sheet_name = state.get('new_sheet_name')
                        if not sheet_name:
                            await message.channel.send("❌ No custom sheet name provided.")
                            user_upload_state.pop(message.author.id, None)
                            return
                        new_sheet = user_spreadsheet.add_worksheet(sheet_name, 1000, 19)
                        # Use your standard header format
                        headers = [
                            'Date', 'Time', 'Product', 'Price', 'Total', 'Commission', 'Quantity', 
                            'Profile', 'Proxy List', 'Order Number', 'Email', 'Reference #', 
                            'Posted Date', 'Tracking Number', 'Status', 'QTY Received', 
                            'Order ID', 'Created', 'Modified'
                        ]
                        new_sheet.append_row(headers)
                        new_sheet.format('A1:S1', {"textFormat": {"bold": True}})
                        
                        # Process orders using OrderProcessor
                        order_processor = OrderProcessor(new_sheet)
                        mapped_rows, process_failed = await order_processor.process_orders(rows_to_add)
                        
                        # Add any processing failures to the failed list
                        if process_failed:
                            failed.extend(process_failed)
                        sheet_name = new_sheet.title
                    else:
                        await message.channel.send("❌ Unknown sheet selection.")
                        user_upload_state.pop(message.author.id, None)
                        return
                    # Final summary
                    await progress_msg.edit(content=f"✅ Uploaded {len(rows_to_add)} orders to {sheet_name}!\n" + (f"\n❌ Failed to process {len(failed)} messages. Showing first 10:\n" + "\n".join(failed[:10]) if failed else ""))
                    response = f"✅ Uploaded {len(rows_to_add)} orders to {sheet_name}"
                    if failed:
                        response += f"\n❌ Failed to process {len(failed)} messages. Showing first 10:\n" + "\n".join(failed[:10])
                    await message.channel.send(response)
                    
                    # Log activity with detailed information
                    log_activity(
                        user_id=message.author.id,
                        action="Upload Orders",
                        details=f"Uploaded {len(rows_to_add)} orders to {sheet_name}",
                        interaction_type="file_upload",
                        sheet_name=sheet_name,
                        file_name=attachment.filename,
                        order_count=len(rows_to_add)
                    )
                    

                except Exception as e:
                    await progress_msg.edit(content=f"❌ Error uploading to sheet: {str(e)}")
                    await message.channel.send(f"❌ Error uploading to sheet: {str(e)}")
                user_upload_state.pop(message.author.id, None)
            except Exception as e:
                await message.channel.send(f"❌ Error processing file: {str(e)}")
                user_upload_state.pop(message.author.id, None)
            return
        # --- End Order Upload Button Flow ---
        # --- Mark Received Button Flow ---
        if 'mark_received_sheet_choice' in state:
            attachment = message.attachments[0]
            if not attachment.filename.endswith('.csv'):
                await message.channel.send("❌ Please attach a CSV file for received tracking update.")
                user_upload_state.pop(message.author.id, None)
                return
            
            # Log file upload for mark received
            log_activity(
                user_id=message.author.id,
                action="Uploaded file for mark received update",
                details=f"File: {attachment.filename}",
                interaction_type="file_upload",
                file_name=attachment.filename,
                order_count=0
            )
            # Use global imports
            
            try:
                
                # Read and parse CSV
                csv_content = await attachment.read()
                csv_text = csv_content.decode('utf-8')
                csv_reader = list(csv.DictReader(csv_text.splitlines()))
                
                if not csv_reader:
                    await message.channel.send("❌ The CSV file is empty")
                    user_upload_state.pop(message.author.id, None)
                    return
                
                # Validate required columns
                header_row = {h.lower().strip() for h in csv_reader[0].keys()}
                
                # Check for tracking number column (accept either tracking_number or tracking_id)
                tracking_col_name = None
                if 'tracking_number' in header_row:
                    tracking_col_name = 'tracking_number'
                elif 'tracking_id' in header_row:
                    tracking_col_name = 'tracking_id'
                else:
                    await message.channel.send(f"❌ Invalid CSV format. Missing column: tracking_number or tracking_id")
                    user_upload_state.pop(message.author.id, None)
                    return
                
                # Check for other required columns
                required_columns = ['total', 'qty', 'commission', 'status', 'order_number', 'created', 'modified']
                missing_columns = [col for col in required_columns if col not in header_row]
                
                if missing_columns:
                    await message.channel.send(f"❌ Invalid CSV format. Missing columns: {', '.join(missing_columns)}")
                    user_upload_state.pop(message.author.id, None)
                    return
                
                # Helper function to process a single sheet
                async def process_mark_received_sheet(target_sheet, sheet_name, csv_data):
                    # Use the global datetime import
                    try:
                        # Read sheet data
                        values = await safe_get_sheet_values(target_sheet)
                        if not values or len(values) < 2:
                            await message.channel.send(f"❌ No data found in {sheet_name}.")
                            return {
                                'updated': [], 'already_same': [], 'not_found': [], 'skipped': [],
                                'total_updated': [], 'commission_updated': [], 'status_updated': [],
                                'qty_received_updated': [], 'order_id_updated': [], 'created_updated': [], 'modified_updated': []
                            }
                        

                            # Re-read the corrected values
                            values = await safe_get_sheet_values(target_sheet)
                        
                        headers = values[0]
                        lower_headers = [h.lower() for h in headers]
                        
                        # Find existing columns using standard header mapping
                        tracking_col_idx = find_header_column(headers, 'tracking_number')
                        product_col_idx = find_header_column(headers, 'product')
                        total_col_idx = find_header_column(headers, 'total')
                        commission_col_idx = find_header_column(headers, 'commission')
                        status_col_idx = find_header_column(headers, 'status')
                        qty_received_col_idx = find_header_column(headers, 'qty_received')
                        order_id_col_idx = find_header_column(headers, 'order_id')
                        created_col_idx = find_header_column(headers, 'created')
                        modified_col_idx = find_header_column(headers, 'modified')
                        
                        if tracking_col_idx is None:
                            await message.channel.send(f"❌ 'Tracking Number' column not found in {sheet_name}.")
                            return {'updated': [], 'already_same': [], 'not_found': [], 'skipped': [],
                                   'total_updated': [], 'commission_updated': [], 'status_updated': [],
                                   'qty_received_updated': [], 'order_id_updated': [], 'created_updated': [], 'modified_updated': []}
                        
                        # Only add columns that are truly missing based on your standard format
                        columns_to_add = []
                        
                        # Check each required column and only add if missing
                        if total_col_idx is None:
                            # Add Total after Price (position 5 in standard format)
                            price_col_idx = find_header_column(headers, 'price')
                            insert_pos = price_col_idx + 1 if price_col_idx is not None else len(headers)
                            columns_to_add.append(('Total', insert_pos))
                            
                        if commission_col_idx is None:
                            # Add Commission after Total (position 6 in standard format)  
                            insert_pos = len(headers)
                            columns_to_add.append(('Commission', insert_pos))
                            
                        if status_col_idx is None:
                            # Add Status after Tracking Number (position 15 in standard format)
                            insert_pos = tracking_col_idx + 1 if tracking_col_idx is not None else len(headers)
                            columns_to_add.append(('Status', insert_pos))
                            
                        if qty_received_col_idx is None:
                            # Add QTY Received after Status (position 16 in standard format)
                            insert_pos = len(headers)
                            columns_to_add.append(('QTY Received', insert_pos))
                            
                        if order_id_col_idx is None:
                            # Add Order ID after QTY Received (position 17 in standard format)
                            insert_pos = len(headers)
                            columns_to_add.append(('Order ID', insert_pos))
                            
                        if created_col_idx is None:
                            # Add Created after Order ID (position 18 in standard format)
                            insert_pos = len(headers)
                            columns_to_add.append(('Created', insert_pos))
                            
                        if modified_col_idx is None:
                            # Add Modified after Created (position 19 in standard format)
                            insert_pos = len(headers)
                            columns_to_add.append(('Modified', insert_pos))
                        
                        # Add missing columns to headers
                        updated_headers = list(headers)
                        
                        for col_name, insert_pos in columns_to_add:
                            actual_pos = min(insert_pos, len(updated_headers))
                            updated_headers.insert(actual_pos, col_name)
                            # Update positions for subsequent insertions
                            for i, (other_col, other_pos) in enumerate(columns_to_add):
                                if other_pos >= actual_pos and other_col != col_name:
                                    columns_to_add[i] = (other_col, other_pos + 1)
                        
                        # Update sheet headers if changed
                        if updated_headers != headers:
                            await asyncio.to_thread(target_sheet.update, 'A1', [updated_headers])
                            values = await safe_get_sheet_values(target_sheet)
                            headers = values[0]
                            lower_headers = [h.lower() for h in headers]  # Refresh lower_headers after adding columns
                        
                        # Get column indices using standard header mapping
                        col_indices = {
                            'Total': find_header_column(headers, 'total'),
                            'Commission': find_header_column(headers, 'commission'),
                            'Status': find_header_column(headers, 'status'),
                            'QTY Received': find_header_column(headers, 'qty_received'),
                            'Order ID': find_header_column(headers, 'order_id'),
                            'Created': find_header_column(headers, 'created'),
                            'Modified': find_header_column(headers, 'modified')
                        }
                        
                        # Build tracking to row mapping
                        tracking_to_row = {}
                        for row_idx, row in enumerate(values[1:], start=2):
                            if len(row) > tracking_col_idx:
                                tracking_val = row[tracking_col_idx].strip().upper()
                                if tracking_val:
                                    tracking_to_row[tracking_val] = row_idx
                        
                        # Process CSV data
                        results = {
                            'updated': [], 'already_same': [], 'not_found': [], 'skipped': [],
                            'total_updated': [], 'commission_updated': [], 'status_updated': [],
                            'qty_received_updated': [], 'order_id_updated': [], 'created_updated': [], 'modified_updated': []
                        }
                        
                        batch_updates = []
                        
                        for csv_row in csv_data:
                            # Clean tracking number from CSV (use whichever column name was found)
                            raw_tracking = csv_row[tracking_col_name]
                            tracking = clean_tracking(raw_tracking).upper()
                            
                            if tracking not in tracking_to_row:
                                results['not_found'].append(tracking)
                                continue
                            
                            row_idx = tracking_to_row[tracking]
                            sheet_row = values[row_idx - 1]
                            row_updated = False
                            
                            # Process each column
                            csv_mappings = {
                                'Total': ('total', lambda x: f"${float(x):,.2f}" if x and x != '0.00' else None),
                                'Commission': ('commission', lambda x: f"${float(x):.2f}" if x and x != '0.00' else ""),
                                'Status': ('status', lambda x: x.upper() if x.upper() in ['VERIFIED', 'UNVERIFIED'] else ""),
                                'QTY Received': ('qty', lambda x: int(x) if x and x != '0' else None),
                                'Order ID': ('order_number', lambda x: x),
                                'Created': ('created', lambda x: x),
                                'Modified': ('modified', lambda x: x)
                            }
                            
                            for col_name, (csv_col, formatter) in csv_mappings.items():
                                if col_indices[col_name] is None:
                                    continue
                                
                                col_idx = col_indices[col_name]
                                csv_value = csv_row.get(csv_col, '').strip()
                                existing_value = sheet_row[col_idx].strip() if len(sheet_row) > col_idx else ""
                                
                                if not csv_value:
                                    continue
                                
                                # Format the new value
                                try:
                                    new_value = formatter(csv_value)
                                    if new_value is None:
                                        continue
                                except (ValueError, TypeError):
                                    continue
                                
                                should_update = False
                                
                                # Special handling for QTY Received column
                                if col_name == 'QTY Received':
                                    # Only update if existing value is zero/empty or if it's a different non-zero value
                                    try:
                                        existing_qty = int(existing_value) if existing_value and existing_value.strip() else 0
                                        new_qty = new_value
                                        
                                        # Only update if existing value was 0 and new value is different
                                        if existing_qty == 0 and new_qty != 0:
                                            should_update = True
                                        elif existing_qty != 0 and existing_qty != new_qty:
                                            # Don't update if existing value is non-zero
                                            results['already_same'].append(f"{tracking} ({col_name})")
                                        else:
                                            results['already_same'].append(f"{tracking} ({col_name})")
                                    except (ValueError, TypeError):
                                        # If existing value can't be parsed as int, treat as 0
                                        if new_value != 0:
                                            should_update = True
                                        else:
                                            results['already_same'].append(f"{tracking} ({col_name})")
                                # Special handling for Total column (currency formatting)
                                elif col_name == 'Total':
                                    # For Total column, always update if value is different (no zero restriction like QTY)
                                    try:
                                        # Clean existing value by removing currency symbols and converting to float
                                        existing_clean = existing_value.replace('$', '').replace(',', '').strip()
                                        existing_total = float(existing_clean) if existing_clean else 0.0
                                        
                                        # Clean new value (which is now formatted currency) to compare
                                        new_clean = new_value.replace('$', '').replace(',', '').strip()
                                        new_total = float(new_clean) if new_clean else 0.0
                                        
                                        if existing_total != new_total:
                                            should_update = True
                                        else:
                                            results['already_same'].append(f"{tracking} ({col_name})")
                                    except (ValueError, TypeError):
                                        # If existing value can't be parsed as float, update anyway
                                        should_update = True
                                # Special handling for timestamps
                                elif col_name in ['Created', 'Modified']:
                                    if not existing_value:
                                        should_update = True
                                    else:
                                        # Parse timestamps and compare
                                        try:
                                            csv_time = datetime.strptime(csv_value, '%m-%d-%Y, %H:%M:%S')
                                            existing_time = datetime.strptime(existing_value, '%m-%d-%Y, %H:%M:%S')
                                            if csv_time > existing_time:
                                                should_update = True
                                            else:
                                                results['already_same'].append(f"{tracking} ({col_name})")
                                        except ValueError:
                                            # If parsing fails, update anyway
                                            should_update = True
                                else:
                                    # For other columns
                                    if not existing_value:
                                        should_update = True
                                    elif existing_value != str(new_value):
                                        should_update = True
                                    else:
                                        results['already_same'].append(f"{tracking} ({col_name})")
                                
                                if should_update:
                                    cell = chr(ord('A') + col_idx) + str(row_idx)
                                    batch_updates.append({'range': cell, 'values': [[new_value]]})
                                    results[f"{col_name.lower().replace(' ', '_')}_updated"].append(tracking)
                                    row_updated = True
                            
                            if row_updated:
                                results['updated'].append(tracking)
                        
                        # Apply batch updates
                        if batch_updates:
                            try:
                                await safe_batch_update(target_sheet, batch_updates, sheet_name)
                            except Exception as e:
                                logging.error(f"Batch update failed for {sheet_name}: {str(e)}")
                        
                        return results
                        
                    except Exception as e:
                        await message.channel.send(f"❌ Error processing {sheet_name}: {str(e)}")
                        return {'updated': [], 'already_same': [], 'not_found': [], 'skipped': [],
                               'total_updated': [], 'commission_updated': [], 'status_updated': [],
                               'qty_received_updated': [], 'order_id_updated': [], 'created_updated': [], 'modified_updated': []}
                
                # Determine which sheets to process
                sheet_choices = state.get('selected_sheets', [])
                if not sheet_choices:
                    if state['mark_received_sheet_choice'].startswith('existing:'):
                        sheet_choices = [state['mark_received_sheet_choice'].split(':', 1)[1]]
                    else:
                        await message.channel.send("❌ No sheets selected for processing.")
                        user_upload_state.pop(message.author.id, None)
                        return
                
                progress_msg = await message.channel.send(f"🔄 Processing {len(sheet_choices)} sheet(s)...")
                
                # Track results across all sheets
                all_results = {
                    'updated': set(), 'already_same': [], 'not_found_anywhere': set(), 'skipped': [],
                    'total_updated': set(), 'commission_updated': set(), 'status_updated': set(),
                    'qty_received_updated': set(), 'order_id_updated': set(), 'created_updated': set(), 'modified_updated': set()
                }
                all_found_trackings = set()
                
                # Get user's spreadsheet
                user_spreadsheet = await get_spreadsheet(user_id=message.author.id)
                if not user_spreadsheet:
                    await message.channel.send("❌ Your Google Sheet is not configured correctly. Please try setting it up again.")
                    user_upload_state.pop(message.author.id, None)
                    return
                
                # Process each sheet
                for i, sheet_name in enumerate(sheet_choices, 1):
                    try:
                        await progress_msg.edit(content=f"🔄 Processing sheet {i}/{len(sheet_choices)}: `{sheet_name}`")
                        
                        target_sheet = user_spreadsheet.worksheet(sheet_name)
                        sheet_results = await process_mark_received_sheet(target_sheet, sheet_name, csv_reader)
                        
                        # Merge results
                        all_results['updated'].update(sheet_results['updated'])
                        all_results['already_same'].extend(sheet_results['already_same'])
                        all_found_trackings.update(sheet_results['updated'])
                        all_found_trackings.update([t.split(' (')[0] for t in sheet_results['already_same']])
                        
                        for key in ['total_updated', 'commission_updated', 'status_updated', 'qty_received_updated', 'order_id_updated', 'created_updated', 'modified_updated']:
                            all_results[key].update(sheet_results[key])
                        
                    except gspread.exceptions.WorksheetNotFound:
                        await message.channel.send(f"⚠️ Sheet `{sheet_name}` not found. Skipping.")
                        continue
                    except Exception as e:
                        if is_likely_connection_error(e):
                            await message.channel.send(f"❌ **Connection Error**: Could not process sheet `{sheet_name}`. Aborting operation.")
                            break
                        await message.channel.send(f"⚠️ Error processing sheet `{sheet_name}`: {str(e)}. Continuing...")
                        continue
                
                # Calculate trackings not found in any sheet
                all_csv_trackings = set()
                for csv_row in csv_reader:
                    raw_tracking = csv_row['tracking_number']
                    tracking = clean_tracking(raw_tracking).upper()
                    all_csv_trackings.add(tracking)
                
                not_found_anywhere = all_csv_trackings - all_found_trackings
                
                # Create summary
                summary_lines = [
                    "✅ **Mark Received Update Complete!**",
                    "",
                    f"📊 **CSV Summary**: {len(all_csv_trackings)} trackings processed",
                    "",
                    "🔄 **Results**:"
                ]
                
                if all_results['updated']:
                    summary_lines.append(f"• {len(all_results['updated'])} trackings updated")
                if all_results['total_updated']:
                    summary_lines.append(f"• {len(all_results['total_updated'])} total amounts updated")
                if all_results['commission_updated']:
                    summary_lines.append(f"• {len(all_results['commission_updated'])} commission amounts updated")
                if all_results['status_updated']:
                    summary_lines.append(f"• {len(all_results['status_updated'])} statuses updated")
                if all_results['qty_received_updated']:
                    summary_lines.append(f"• {len(all_results['qty_received_updated'])} quantities updated")
                if all_results['order_id_updated']:
                    summary_lines.append(f"• {len(all_results['order_id_updated'])} order IDs updated")
                if all_results['created_updated']:
                    summary_lines.append(f"• {len(all_results['created_updated'])} created timestamps updated")
                if all_results['modified_updated']:
                    summary_lines.append(f"• {len(all_results['modified_updated'])} modified timestamps updated")
                
                if all_results['already_same']:
                    summary_lines.append(f"• {len(all_results['already_same'])} fields already had same data")
                
                if not_found_anywhere:
                    summary_lines.append(f"• {len(not_found_anywhere)} trackings not found in any sheet")
                
                # Show results
                view = None
                if not_found_anywhere:
                    view = ViewAllOrdersView("View Not Found", list(not_found_anywhere), "Not found in any sheet")
                
                await progress_msg.edit(content="\n".join(summary_lines), view=view)
                user_upload_state.pop(message.author.id, None)
                return
                
            except Exception as e:
                await message.channel.send(f"❌ Error processing mark received file: {str(e)}")
                user_upload_state.pop(message.author.id, None)
                return

        # --- Reconcile Charges Button Flow ---
        if 'reconcile_charges_sheet_choices' in state:
            # Handle multiple CSV files for multiple sheets
            if len(message.attachments) == 0:
                await message.channel.send("❌ Please attach at least one CSV file for reconcile charges.")
                user_upload_state.pop(message.author.id, None)
                return
            
            # Validate all attachments are CSV files
            for attachment in message.attachments:
                if not attachment.filename.endswith('.csv'):
                    await message.channel.send(f"❌ File '{attachment.filename}' is not a CSV file. Please attach only CSV files.")
                    user_upload_state.pop(message.author.id, None)
                    return
            
            sheet_choices = state.get('reconcile_charges_sheet_choices', [])
            mode = state.get('reconcile_charges_mode', 'single_csv')
            
            # Determine processing strategy based on number of files vs sheets
            if len(message.attachments) == 1:
                # Single CSV - process against all selected sheets
                try:
                    attachment = message.attachments[0]
                    csv_content = await attachment.read()
                    csv_text = csv_content.decode('utf-8')
                    csv_reader = list(csv.DictReader(csv_text.splitlines()))
                    if not csv_reader:
                        await message.channel.send("❌ The CSV file is empty")
                        user_upload_state.pop(message.author.id, None)
                        return

                    # Validate required columns
                    header_row = {h.lower().strip() for h in csv_reader[0].keys()}
                    required_columns = {'extended details', 'reference', 'date'}
                    
                    missing_columns = []
                    for col in required_columns:
                        if col not in header_row:
                            missing_columns.append(col)
                    
                    if missing_columns:
                        await message.channel.send(f"❌ Invalid CSV format. Missing required columns: {', '.join(missing_columns)}")
                        user_upload_state.pop(message.author.id, None)
                        return

                    # Process each sheet
                    sheet_choices = state.get('reconcile_charges_sheet_choices', [])
                    if not sheet_choices:
                        await message.channel.send("❌ No sheets selected for processing.")
                        user_upload_state.pop(message.author.id, None)
                        return

                    progress_msg = await message.channel.send(f"🔄 Processing {len(sheet_choices)} sheet(s)...")
                    total_updated_across_all_sheets = 0

                    for i, sheet_name in enumerate(sheet_choices, 1):
                        try:
                            await progress_msg.edit(content=f"🔄 Processing sheet {i}/{len(sheet_choices)}: `{sheet_name}`")
                            
                            # Get the user's specific spreadsheet
                            user_spreadsheet = await get_spreadsheet(user_id=message.author.id)
                            if not user_spreadsheet:
                                await message.channel.send("❌ Your Google Sheet is not configured correctly. Please try setting it up again.")
                                user_upload_state.pop(message.author.id, None)
                                return
                            
                            target_sheet = user_spreadsheet.worksheet(sheet_name)
                            values = await safe_get_sheet_values(target_sheet)
                            if not values or len(values) < 2:
                                await message.channel.send(f"❌ No data found in {sheet_name}.")
                                continue
                            
                            # Get headers from first row
                            headers = values[0]
                            lower_headers = [h.lower() for h in headers]

                            # Find the Order Number column in the Google Sheet
                            order_col_idx = find_header_column(headers, 'order_number')

                            if order_col_idx is None:
                                await message.channel.send(f"❌ Order Number column not found in sheet `{sheet_name}`.")
                                continue

                            # Find Email column to add Reference # after it
                            email_col_idx = find_header_column(headers, 'email')
                            
                            # Add Reference # column if it doesn't exist
                            ref_col_idx = find_header_column(headers, 'reference')
                            if ref_col_idx is None:
                                # Add after Email column if exists, otherwise add after Order Number
                                insert_idx = email_col_idx + 1 if email_col_idx is not None else order_col_idx + 1
                                headers.insert(insert_idx, 'Reference #')
                                await asyncio.to_thread(target_sheet.update, 'A1', [headers])
                                ref_col_idx = insert_idx
                                values = await safe_get_sheet_values(target_sheet)  # Refresh values
                                lower_headers = [h.lower() for h in headers]  # Refresh lower_headers after adding column

                            # Add Posted Date column if it doesn't exist
                            date_col_idx = find_header_column(headers, 'posted_date')
                            if date_col_idx is None:
                                # Add after Reference # column
                                headers.insert(ref_col_idx + 1, 'Posted Date')
                                await asyncio.to_thread(target_sheet.update, 'A1', [headers])
                                date_col_idx = ref_col_idx + 1
                                values = await safe_get_sheet_values(target_sheet)  # Refresh values
                                lower_headers = [h.lower() for h in headers]  # Refresh lower_headers after adding column

                            # Check if Tracking Number column exists and position it correctly
                            tracking_col_idx = find_header_column(headers, 'tracking_number')
                            if tracking_col_idx is None:
                                # Add Tracking Number column after Date column
                                headers.insert(date_col_idx + 1, 'Tracking Number')
                                await asyncio.to_thread(target_sheet.update, 'A1', [headers])
                                tracking_col_idx = date_col_idx + 1
                                values = await safe_get_sheet_values(target_sheet)  # Refresh values
                                lower_headers = [h.lower() for h in headers]  # Refresh lower_headers after adding column

                            # Build a map of order number -> row index from the sheet
                            order_to_row = {}
                            for row_idx, row in enumerate(values[1:], start=2):
                                if len(row) > order_col_idx:
                                    order_val = row[order_col_idx].strip()
                                    if order_val:
                                        order_to_row[order_val] = row_idx

                            # Process each row in the CSV
                            batch_updates = []
                            all_updated = []
                            not_found_orders = []
                            skipped_updates = []
                            last_progress_update = datetime.now()
                            
                            for csv_row_idx, csv_row in enumerate(csv_reader):
                                # Extract order number from Extended Details
                                # Find the Extended Details column case-insensitively
                                extended_details_key = next((k for k in csv_row.keys() if k.lower() == 'extended details'), None)
                                if not extended_details_key:
                                    continue
                                
                                # Handle multiline Extended Details
                                desc = csv_row[extended_details_key].strip()
                                desc_lines = desc.splitlines()
                                
                                # Find the line containing Description and extract order number
                                order_number = None
                                for line in desc_lines:
                                    if 'Description : ' in line:
                                        # Extract text between "Description : " and " Price : "
                                        parts = line.split('Description : ')[1].split(' Price : ')[0].strip()
                                        if parts:
                                            # Skip category names and look for actual order numbers
                                            # Order numbers typically contain numbers/dashes and are longer
                                            if (len(parts) > 5 and 
                                                any(char.isdigit() for char in parts) and
                                                parts not in ['RESTAURANTS', 'ELEC SLS', 'N/A']):
                                                order_number = parts
                                                break
                                
                                if not order_number:
                                    continue

                                if order_number not in order_to_row:
                                    not_found_orders.append(order_number)
                                    continue

                                row_idx = order_to_row[order_number]
                                row_was_updated = False
                                skipped_fields = []

                                reference_key = next((k for k in csv_row.keys() if k.lower() == 'reference'), None)
                                date_key = next((k for k in csv_row.keys() if k.lower() == 'date'), None)
                                
                                # Update Reference # (independent check)
                                if reference_key:
                                    ref_number = csv_row[reference_key].strip("'")  # Remove quotes
                                    if ref_number:
                                        # Check if reference already exists
                                        existing_ref = values[row_idx - 1][ref_col_idx] if len(values[row_idx - 1]) > ref_col_idx else ""
                                        if not existing_ref.strip():
                                            # Update Reference #
                                            ref_cell = chr(ord('A') + ref_col_idx) + str(row_idx)
                                            batch_updates.append({'range': ref_cell, 'values': [[ref_number]]})
                                            row_was_updated = True
                                        else:
                                            skipped_fields.append('Reference #')

                                # Update Date (independent check)
                                if date_key:
                                    date_value = csv_row[date_key].strip()
                                    if date_value:
                                        existing_date = values[row_idx - 1][date_col_idx] if len(values[row_idx - 1]) > date_col_idx else ""
                                        if not existing_date.strip():
                                            date_cell = chr(ord('A') + date_col_idx) + str(row_idx)
                                            batch_updates.append({'range': date_cell, 'values': [[date_value]]})
                                            row_was_updated = True
                                        else:
                                            skipped_fields.append('Date')

                                # Update Date (case-insensitive matching)
                                date_key = None
                                for col_name in csv_row.keys():
                                    if col_name.lower() == 'date':
                                        date_key = col_name
                                        break
                                
                                if date_key:
                                    date_val = csv_row[date_key].strip()
                                    if date_val:
                                        # Check if date already exists
                                        existing_date = values[row_idx - 1][date_col_idx] if len(values[row_idx - 1]) > date_col_idx else ""
                                        if existing_date.strip():
                                            skipped_fields.append('Date')
                                        else:
                                            date_cell = chr(ord('A') + date_col_idx) + str(row_idx)
                                            batch_updates.append({'range': date_cell, 'values': [[date_val]]})
                                            row_was_updated = True
                                            logging.info(f"Adding date update for order {order_number}: {date_val} to cell {date_cell}")
                                    else:
                                        logging.warning(f"Date value is empty for order {order_number}")
                                else:
                                    logging.warning(f"No date column found in CSV for order {order_number}")

                                if row_was_updated:
                                    all_updated.append(order_number)
                                if skipped_fields:
                                    skipped_updates.append((order_number, skipped_fields))

                                # Update progress bar less frequently and only if enough time has passed
                                if ((csv_row_idx + 1) % 25 == 0 or csv_row_idx == len(csv_reader) - 1) and \
                                   (datetime.now() - last_progress_update).total_seconds() >= 1.5:
                                    progress = int(((csv_row_idx + 1) / len(csv_reader)) * 100)
                                    bar_length = 20
                                    filled_length = int(bar_length * (csv_row_idx + 1) // len(csv_reader))
                                    bar = '█' * filled_length + '░' * (bar_length - filled_length)
                                    await progress_msg.edit(content=f"```\nProcessing sheet {sheet_name}...\nProgress: [{bar}] {progress}%\nProcessed {csv_row_idx + 1}/{len(csv_reader)} orders...\n```")
                                    last_progress_update = datetime.now()

                            # Apply batch updates
                            if batch_updates:
                                try:
                                    await safe_batch_update(target_sheet, batch_updates, sheet_name)
                                    total_updated_across_all_sheets += len(all_updated)
                                except Exception as e:
                                    logging.error(f"Batch update failed: {str(e)}")
                                    await message.channel.send(f"⚠️ Error updating sheet `{sheet_name}`: {str(e)}")
                                    continue

                            # Summary message for this sheet  
                            csv_reader_count = len(csv_reader) if 'csv_reader' in locals() else 0
                            summary = f"**{sheet_name}**\n"
                            summary += f"```\n"
                            summary += f"Total rows: {csv_reader_count}\n"
                            summary += f"Updated: {len(all_updated)}\n"
                            summary += f"Already had data: {len(skipped_updates) if skipped_updates else 0}\n"
                            summary += f"Not found: {len(not_found_orders)}\n"
                            summary += f"```"
                            
                            await message.channel.send(summary)
                            
                            # Show not found orders if any (with message length checking)
                            if not_found_orders:
                                sorted_not_found = sorted(not_found_orders)
                                await send_long_list(message.channel, f"**Orders not found in {sheet_name}:**", sorted_not_found)

                        except gspread.exceptions.WorksheetNotFound:
                            await message.channel.send(f"⚠️ Sheet `{sheet_name}` not found. Skipping.")
                            continue
                        except Exception as e:
                            if is_likely_connection_error(e):
                                await message.channel.send(f"❌ **Connection Error**: Could not process sheet `{sheet_name}`. Aborting operation.")
                                break
                            await message.channel.send(f"⚠️ Error processing sheet `{sheet_name}`: {str(e)}. Continuing...")
                            continue

                    await progress_msg.edit(content=f"✅ **Multi-Sheet Update Complete!**\n\nTotal orders updated across all sheets: **{total_updated_across_all_sheets}**")
                    user_upload_state.pop(message.author.id, None)
                    return

                except Exception as e:
                    await message.channel.send(f"❌ Error processing reconcile charges file: {str(e)}")
                    user_upload_state.pop(message.author.id, None)
                    return
            
            # Handle multiple CSV files
                        # Handle multiple CSV files
            elif len(message.attachments) > 1:
                # Multiple CSVs - process each CSV against all selected sheets
                total_updated_across_all_sheets = 0
                try:
                    progress_msg = await message.channel.send(f"🔄 Processing {len(message.attachments)} CSV files against {len(sheet_choices)} sheets...")

                    # Process each CSV file
                    for i, attachment in enumerate(message.attachments, 1):
                        
                        # First read and validate the CSV
                        try:
                            csv_content = await attachment.read()
                            csv_text = csv_content.decode('utf-8')
                            csv_reader = list(csv.DictReader(csv_text.splitlines()))

                            if not csv_reader:
                                await message.channel.send(f"⚠️ CSV file '{attachment.filename}' is empty. Skipping.")
                                continue

                            # Validate required columns
                            header_row = {h.lower().strip() for h in csv_reader[0].keys()}
                            required_columns = {'extended details', 'reference', 'date'}
                            missing_columns = [col for col in required_columns if col not in header_row]

                            if missing_columns:
                                await message.channel.send(f"⚠️ CSV file '{attachment.filename}' has invalid format. Missing columns: {', '.join(missing_columns)}. Skipping.")
                                continue

                            # Initialize tracking for this CSV across all sheets
                            csv_total_rows = len(csv_reader)
                            csv_found_orders = set()  # Orders found in ANY sheet
                            csv_updated_orders = set()  # Orders actually updated
                            csv_skipped_orders = set()  # Orders found but already had data
                            csv_invalid_rows = 0  # Rows with no Extended Details or no valid order number
                            sheet_results = []  # Results per sheet for this CSV

                            # Pre-process CSV to count invalid rows (only once)
                            csv_valid_orders = set()
                            csv_invalid_details = []  # Store details of invalid rows
                            for csv_row_idx, csv_row in enumerate(csv_reader, 1):
                                extended_details_key = next((k for k in csv_row.keys() if k.lower() == 'extended details'), None)
                                reference_key = next((k for k in csv_row.keys() if k.lower() == 'reference'), None)
                                
                                if not extended_details_key:
                                    csv_invalid_rows += 1
                                    # Capture what we can from this row
                                    ref_value = csv_row.get(reference_key, 'N/A') if reference_key else 'N/A'
                                    csv_invalid_details.append(f"Row {csv_row_idx}: No Extended Details column - Reference: {ref_value}")
                                    continue

                                desc = csv_row[extended_details_key].strip()
                                order_number = None
                                for line in desc.splitlines():
                                    if 'Description : ' in line:
                                        parts = line.split('Description : ')[1].split(' Price : ')[0].strip()
                                        if parts:
                                            if (len(parts) > 5 and 
                                                any(char.isdigit() for char in parts) and
                                                parts not in ['RESTAURANTS', 'ELEC SLS', 'N/A']):
                                                order_number = parts
                                                break

                                if not order_number:
                                    csv_invalid_rows += 1
                                    # Capture the extended details for debugging
                                    truncated_desc = desc[:100] + "..." if len(desc) > 100 else desc
                                    csv_invalid_details.append(f"Row {csv_row_idx}: {truncated_desc}")
                                else:
                                    csv_valid_orders.add(order_number)

                            # Now try this CSV against each selected sheet
                            for sheet_name in sheet_choices:
                                try:
                                    await progress_msg.edit(content=f"🔄 Processing file {i}/{len(message.attachments)}: `{attachment.filename}` → `{sheet_name}`")

                                    # Get and validate spreadsheet
                                    user_spreadsheet = await get_spreadsheet(user_id=message.author.id)
                                    if not user_spreadsheet:
                                        await message.channel.send(f"❌ Your Google Sheet is not configured correctly for sheet '{sheet_name}'. Please try setting it up again.")
                                        continue
                                    
                                    target_sheet = user_spreadsheet.worksheet(sheet_name)
                                    values = await safe_get_sheet_values(target_sheet)
                                    if not values or len(values) < 2:
                                        await message.channel.send(f"❌ No data found in {sheet_name}. Skipping.")
                                        continue


                                        # Re-read the corrected values
                                        values = await safe_get_sheet_values(target_sheet)
                                    
                                    headers = values[0]
                                    lower_headers = [h.lower() for h in headers]

                                    # Find required column indices
                                    order_col_idx = find_header_column(headers, 'order_number')

                                    if order_col_idx is None:
                                        await message.channel.send(f"❌ Order Number column not found in sheet `{sheet_name}`. Skipping.")
                                        continue

                                    # Find or create Reference # column
                                    email_col_idx = find_header_column(headers, 'email')
                                    ref_col_idx = find_header_column(headers, 'reference')

                                    if ref_col_idx is None:
                                        insert_idx = email_col_idx + 1 if email_col_idx is not None else order_col_idx + 1
                                        headers.insert(insert_idx, 'Reference #')
                                        await asyncio.to_thread(target_sheet.update, 'A1', [headers])
                                        ref_col_idx = insert_idx
                                        values = await safe_get_sheet_values(target_sheet)
                                        lower_headers = [h.lower() for h in headers]

                                    # Find or create Posted Date column
                                    date_col_idx = find_header_column(headers, 'posted_date')
                                    if date_col_idx is None:
                                        headers.insert(ref_col_idx + 1, 'Posted Date')
                                        await asyncio.to_thread(target_sheet.update, 'A1', [headers])
                                        date_col_idx = ref_col_idx + 1
                                        values = await safe_get_sheet_values(target_sheet)
                                        lower_headers = [h.lower() for h in headers]

                                    # Build order number to row index map
                                    order_to_row = {
                                        row[order_col_idx].strip(): row_idx 
                                        for row_idx, row in enumerate(values[1:], start=2) 
                                        if len(row) > order_col_idx and row[order_col_idx].strip()
                                    }

                                    # Process CSV rows
                                    batch_updates = []
                                    all_updated = []
                                    not_found_orders = []
                                    skipped_updates = []
                                    
                                    for csv_row_idx, csv_row in enumerate(csv_reader):
                                        extended_details_key = next((k for k in csv_row.keys() if k.lower() == 'extended details'), None)
                                        if not extended_details_key:
                                            continue

                                        desc = csv_row[extended_details_key].strip()
                                        order_number = None
                                        for line in desc.splitlines():
                                            if 'Description : ' in line:
                                                parts = line.split('Description : ')[1].split(' Price : ')[0].strip()
                                                if parts:
                                                    # Skip category names and look for actual order numbers
                                                    # Order numbers typically contain numbers/dashes and are longer
                                                    if (len(parts) > 5 and 
                                                        any(char.isdigit() for char in parts) and
                                                        parts not in ['RESTAURANTS', 'ELEC SLS', 'N/A']):
                                                        order_number = parts
                                                        break

                                        if not order_number:
                                            continue

                                        if order_number not in order_to_row:
                                            if order_number:
                                                not_found_orders.append(order_number)
                                            continue

                                        # Track that this order was found in this sheet
                                        csv_found_orders.add(order_number)

                                        row_idx = order_to_row[order_number]
                                        row_was_updated = False
                                        skipped_fields = []

                                        reference_key = next((k for k in csv_row.keys() if k.lower() == 'reference'), None)
                                        date_key = next((k for k in csv_row.keys() if k.lower() == 'date'), None)

                                        # Update Reference # (independent check)
                                        if reference_key:
                                            ref_number = csv_row[reference_key].strip("'")
                                            if ref_number:
                                                existing_ref = values[row_idx - 1][ref_col_idx] if len(values[row_idx - 1]) > ref_col_idx else ""
                                                if not existing_ref.strip():
                                                    ref_cell = chr(ord('A') + ref_col_idx) + str(row_idx)
                                                    batch_updates.append({'range': ref_cell, 'values': [[ref_number]]})
                                                    row_was_updated = True
                                                else:
                                                    skipped_fields.append('Reference #')

                                        # Update Date (independent check)
                                        if date_key:
                                            date_value = csv_row[date_key].strip()
                                            if date_value:
                                                existing_date = values[row_idx - 1][date_col_idx] if len(values[row_idx - 1]) > date_col_idx else ""
                                                if not existing_date.strip():
                                                    date_cell = chr(ord('A') + date_col_idx) + str(row_idx)
                                                    batch_updates.append({'range': date_cell, 'values': [[date_value]]})
                                                    row_was_updated = True
                                                else:
                                                    skipped_fields.append('Date')

                                        # Track the results for overall CSV summary
                                        if row_was_updated:
                                            all_updated.append(order_number)
                                            csv_updated_orders.add(order_number)
                                        if skipped_fields:
                                            skipped_updates.append((order_number, skipped_fields))
                                            csv_skipped_orders.add(order_number)

                                    # Apply batch updates
                                    if batch_updates:
                                        try:
                                            await safe_batch_update(target_sheet, batch_updates, sheet_name)
                                            total_updated_across_all_sheets += len(all_updated)
                                        except Exception as e:
                                            logging.error(f"Batch update failed for {sheet_name}: {str(e)}")
                                            await message.channel.send(f"⚠️ Error updating sheet `{sheet_name}`: {str(e)}")
                                            continue

                                    # Store summary for this sheet
                                    sheet_summary = f"  • {sheet_name}: {len(all_updated)} updated"
                                    if skipped_updates:
                                        sheet_summary += f", {len(skipped_updates)} skipped"
                                    if not_found_orders:
                                        sheet_summary += f", {len(not_found_orders)} not found"
                                    sheet_results.append(sheet_summary)

                                except gspread.exceptions.WorksheetNotFound:
                                    await message.channel.send(f"⚠️ Sheet `{sheet_name}` not found. Skipping.")
                                    continue
                                except Exception as e:
                                    if is_likely_connection_error(e):
                                        await message.channel.send(f"❌ **Connection Error**: Could not process sheet `{sheet_name}`. Aborting operation.")
                                        break
                                    await message.channel.send(f"⚠️ Error processing sheet `{sheet_name}`: {str(e)}. Continuing...")
                                    continue

                            # Calculate final stats for this CSV
                            csv_not_found_orders = csv_valid_orders - csv_found_orders
                            csv_not_found = len(csv_not_found_orders)
                            
                            # Send clean, copyable summary
                            summary_msg = f"**{attachment.filename}**\n"
                            summary_msg += f"```\n"
                            summary_msg += f"Total rows: {csv_total_rows}\n"
                            summary_msg += f"Updated: {len(csv_updated_orders)}\n"
                            summary_msg += f"Already had data: {len(csv_skipped_orders)}\n"
                            summary_msg += f"Not found in ANY sheet: {csv_not_found}\n"
                            if csv_invalid_rows > 0:
                                summary_msg += f"Invalid/skipped rows: {csv_invalid_rows}\n"
                            summary_msg += f"```"
                            
                            await message.channel.send(summary_msg)
                            
                            # Show not found orders if any (with message length checking)
                            if csv_not_found_orders:
                                not_found_list = sorted(list(csv_not_found_orders))
                                await send_long_list(message.channel, f"**Orders not found in ANY sheet:**", not_found_list)
                            
                            # Show invalid rows details if any (with message length checking)
                            if csv_invalid_details:
                                await send_long_list(message.channel, f"**Invalid/Skipped Rows from {attachment.filename}:**", csv_invalid_details)

                        except Exception as e:
                            await message.channel.send(f"❌ Error processing CSV file '{attachment.filename}': {str(e)}")
                            continue

                    # Send final summary
                    await progress_msg.edit(content=f"✅ **Reconciliation Complete!**\n\n```\nTotal updated across all files: {total_updated_across_all_sheets}\n```")
                    user_upload_state.pop(message.author.id, None)
                    return

                except Exception as e:
                    await message.channel.send(f"❌ Error processing reconcile charges file: {str(e)}")
                    user_upload_state.pop(message.author.id, None)
                    return
        # --- End Reconcile Charges Button Flow ---

    # If the message is not part of the button-based file upload flow, process as a command
    logging.info(f"Processing command or regular message from {message.author.name}")
    await bot.process_commands(message)

@bot.command(name='batch')
@is_authorized_user()
async def batch_process(ctx, *, content):
    """Process multiple messages at once"""
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
        
    if "Successful Checkout | Refract" in content:
        # Split into individual messages
        messages = content.split("Successful Checkout | Refract")
        messages = [m for m in messages if m.strip()]  # Remove empty splits
        
        rows_to_add = []
        successful = 0
        failed = []
        
        for msg in messages:
            try:
                data = parse_message(msg)
                if data:
                    now = datetime.now()
                    rows_to_add.append([
                        now.strftime('%Y-%m-%d'),
                        now.strftime('%I:%M:%S %p'),
                        data['Product'],
                        data['Price'],
                        data['Quantity'],
                        data['Profile'],
                        data['Proxy List'],
                        data['Order Number'],
                        data['Email']
                    ])
                    successful += 1
                else:
                    failed.append(f"Message #{len(rows_to_add) + 1}")
            except Exception as e:
                failed.append(f"Message #{len(rows_to_add) + 1}: {str(e)}")
        
        if rows_to_add:
            try:
                # Get the user's specific spreadsheet
                user_spreadsheet = await get_spreadsheet(user_id=ctx.author.id)
                if not user_spreadsheet:
                    await ctx.send("❌ Your Google Sheet is not configured correctly. Please try setting it up again.")
                    return
                user_sheet1 = user_spreadsheet.worksheet('Sheet1')
                user_sheet1.append_rows(rows_to_add)
                response = f"✅ Successfully added {successful} orders to spreadsheet"
                if failed:
                    response += f"\n❌ Failed to process {len(failed)} messages:\n" + "\n".join(failed)
                await ctx.send(response)
            except Exception as e:
                await ctx.send(f"❌ Error adding to spreadsheet: {str(e)}")
        else:
            await ctx.send("❌ No valid orders found in message")
    else:
        await ctx.send("Please include messages that contain 'Successful Checkout | Refract'")

# Helper function to get the bot's memory usage
def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # Convert bytes to MB

@bot.command(name='adduser')
@is_admin()
async def add_user_command(ctx, user: str, role: str):
    """Adds a user with a specified role (admin/user) by Discord ID or mention. Can be used in DMs."""
    if role.lower() not in ['admin', 'user']:
        await ctx.send("❌ Invalid role. Please use 'admin' or 'user'.")
        return

    role = role.lower()
    # Try to extract user ID from mention or string
    import re
    user_id = None
    mention_match = re.match(r'<@!?(\d+)>', user)
    if mention_match:
        user_id = int(mention_match.group(1))
    else:
        try:
            user_id = int(user)
        except ValueError:
            await ctx.send("❌ Please provide a valid Discord user ID or mention.")
            return
    try:
        user_obj = await safe_discord_call(bot.fetch_user, user_id, call_type='user_fetch')
    except Exception:
        user_obj = None
    if not user_obj:
        await ctx.send(f"❌ Could not find a user with ID `{user_id}`.")
        return
    profile = get_user_profile(user_id)
    if profile:
        # User exists, check if role is being updated
        if profile.get('role') == role:
            await ctx.send(f"⚠️ **{user_obj.display_name}** is already an **{role.capitalize()}**.")
        else:
            add_user(user_id, role) # This will update the role
            await ctx.send(f"✅ Role for **{user_obj.display_name}** has been updated to **{role.capitalize()}**.")
    else:
        # New user
        if add_user(user_id, role):
            log_activity(ctx.author.id, "Add User", f"Added {user_obj.display_name} as {role}")
            await ctx.send(f"✅ **{user_obj.display_name}** has been added as an **{role.capitalize()}**. They will now be able to use the bot.")
        else:
            await ctx.send("❌ An unexpected error occurred while adding the user.")

@bot.command(name='removeuser')
@is_admin()
async def remove_user_command(ctx, user: str):
    """Removes a user from all roles by Discord ID or mention. Can be used in DMs."""
    import re
    user_id = None
    mention_match = re.match(r'<@!?(\d+)>', user)
    if mention_match:
        user_id = int(mention_match.group(1))
    else:
        try:
            user_id = int(user)
        except ValueError:
            await ctx.send("❌ Please provide a valid Discord user ID or mention.")
            return
    try:
        user_obj = await safe_discord_call(bot.fetch_user, user_id, call_type='user_fetch')
    except Exception:
        user_obj = None
    if remove_user(user_id):
        set_user_spreadsheet(user_id, None, None)  # Clear spreadsheet info
        log_activity(ctx.author.id, "Remove User", f"Removed {user_obj.display_name if user_obj else user_id}")
        if user_obj:
            await ctx.send(f"✅ **{user_obj.display_name}** has been removed from the bot.")
        else:
            await ctx.send(f"✅ User `{user_id}` has been removed from the bot.")
    else:
        if user_obj:
            await ctx.send(f"⚠️ **{user_obj.display_name}** was not found in the user list.")
        else:
            await ctx.send(f"⚠️ User `{user_id}` was not found in the user list.")

@bot.command(name='listusers')
@is_admin()
async def list_users_command(ctx):
    """Lists all authorized users and their roles."""
    all_users = get_all_users_with_details()
    
    embed = discord.Embed(
        title="Authorized Users",
        color=discord.Color.blue()
    )
    
    if not all_users:
        embed.description = "No users have been added yet."
        await ctx.send(embed=embed)
        return

    admin_list = []
    user_list = []

    for user_id_str, profile in all_users.items():
        try:
            user = await safe_discord_call(bot.fetch_user, int(user_id_str), call_type='user_fetch')
            sheet_info = f"GSheet: `{profile.get('spreadsheet_name', 'Not Set')}`"
            user_info = f"• {user.display_name} (`{user_id_str}`)\n  - {sheet_info}"
            if profile.get('role') == 'admin':
                admin_list.append(user_info)
            else:
                user_list.append(user_info)
        except (discord.NotFound, ValueError):
            user_info = f"• *Unknown User* (`{user_id_str}`)"
            if profile.get('role') == 'admin':
                admin_list.append(user_info)
            else:
                user_list.append(user_info)

    embed.add_field(name="👑 Admins", value="\n".join(admin_list) if admin_list else "None", inline=False)
    embed.add_field(name="👤 Users", value="\n".join(user_list) if user_list else "None", inline=False)
    
    await ctx.send(embed=embed)


@bot.command(name='ratelimit')
@is_admin()
async def rate_limit_status(ctx):
    """Shows the current rate limiting status for Discord and Google Sheets APIs."""
    try:
        # Get rate limiter status
        discord_queue = len(discord_rate_limiter.calls.get('discord_api', []))
        discord_msg_queue = len(discord_message_limiter.calls.get('message_send', []))
        sheets_queue = len(sheets_rate_limiter.calls.get('batch_update', []))
        
        # Get websocket status
        ws_status = "🟢 Normal" if not bot.is_ws_ratelimited() else "🔴 Rate Limited"
        
        embed = discord.Embed(
            title="🚦 Rate Limiting Status",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="Discord API",
            value=f"Queue: {discord_queue} calls\nLimit: 2 calls/second",
            inline=True
        )
        
        embed.add_field(
            name="Discord Messages",
            value=f"Queue: {discord_msg_queue} calls\nLimit: 1 call/2 seconds",
            inline=True
        )
        
        embed.add_field(
            name="Google Sheets",
            value=f"Queue: {sheets_queue} calls\nLimit: 2 calls/second",
            inline=True
        )
        
        embed.add_field(
            name="WebSocket Status",
            value=ws_status,
            inline=True
        )
        
        embed.add_field(
            name="Rate Limiting Features",
            value="✅ Automatic retry with exponential backoff\n✅ Conservative limits to prevent 429 errors\n✅ Separate limits for different API types",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error getting rate limit status: {str(e)}")


class WelcomeView(View):
    def __init__(self, bot_instance):
        super().__init__(timeout=None)  # No timeout for persistent views
        self.bot = bot_instance

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Central check for all buttons in this view."""
        user = interaction.user
        
        # 1. Check if user is authorized at all
        if not (user.id == self.bot.owner_id or is_authorized(user.id)):
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "🤖 You are not authorized to use this bot. Please contact the bot owner for access.", 
                    ephemeral=True
                )
            return False

        # 2. Check if the user needs to set up their spreadsheet.
        # This now applies to the owner as well to ensure everyone has a configured sheet.
        if needs_setup(user.id):
            if not interaction.response.is_done():
                # Defer the response first, as the setup might take time
                await interaction.response.defer(ephemeral=True)
                await self.prompt_for_spreadsheet_setup(interaction)
            return False
            
        return True

    async def prompt_for_spreadsheet_setup(self, interaction: discord.Interaction):
        """Guides a new user through setting up their Google Sheet."""
        user = interaction.user
        
        # Read the service account email from credentials.json
        try:
            with open('credentials.json', 'r') as f:
                creds_data = json.load(f)
                service_email = creds_data.get('client_email')
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            await interaction.followup.send("❌ **Bot Error:** Could not read service account email from `credentials.json`. Please contact the bot owner.", ephemeral=True)
            return
            
        setup_message = (
            f"👋 **Welcome, {user.mention}!** To get started, I need access to your Google Sheet.\n\n"
            "**Please follow these steps:**\n"
            "1. **Create a Google Sheet** where you want me to store order data.\n"
            "2. **Click the 'Share' button** in your Google Sheet (top right).\n"
            f"3. **Invite this email address as an `Editor`**: ```{service_email}```\n"
            "4. **Copy the full URL** of your Google Sheet from your browser's address bar.\n"
            "5. **Paste the URL here in this DM and press Enter.**"
        )
        
        await interaction.followup.send(setup_message, ephemeral=True)

        def check(m):
            # Check if the message is from the user in the same DM channel
            return m.author == user and isinstance(m.channel, discord.DMChannel)

        try:
            # Wait for the user to reply with the URL
            msg = await self.bot.wait_for('message', check=check, timeout=300.0)
            url = msg.content.strip()
            
            # Extract spreadsheet ID from URL
            match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
            if not match:
                await msg.reply("❌ That doesn't look like a valid Google Sheet URL. Please try again.", ephemeral=True)
                return
            
            spreadsheet_id = match.group(1)
            
            # Test the connection to the sheet
            await msg.reply("⏳ Validating your sheet, please wait...", ephemeral=True)
            try:
                # Use a temporary gspread client to test this specific sheet
                from google.oauth2.service_account import Credentials
                creds = Credentials.from_service_account_file('credentials.json', scopes=['https://www.googleapis.com/auth/spreadsheets'])
                temp_gc = gspread.authorize(creds)
                
                new_sheet = await asyncio.to_thread(temp_gc.open_by_key, spreadsheet_id)
                spreadsheet_name = new_sheet.title

                # Save the user's spreadsheet info
                set_user_spreadsheet(user.id, spreadsheet_id, spreadsheet_name)
                # Also set it in the sheet_utils cache for immediate use
                set_user_spreadsheet(user.id, new_sheet.id, new_sheet.title)

                await msg.reply(f"✅ **Success!** I've connected to your sheet: **`{spreadsheet_name}`**. You can now use the bot commands.", ephemeral=True)

            except gspread.exceptions.SpreadsheetNotFound:
                await msg.reply(f"❌ **Failed!** I couldn't find a spreadsheet with that URL. Make sure it was shared correctly with my email address (`{service_email}`).", ephemeral=True)
            except Exception as e:
                logging.error(f"Error during user sheet setup for {user.id}: {e}")
                await msg.reply("❌ An unexpected error occurred. Please try again or contact the owner.", ephemeral=True)

        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Your setup request timed out. Please click a button again to restart.", ephemeral=True)


    @discord.ui.button(label="Upload Orders", style=discord.ButtonStyle.success, custom_id="upload_button")
    async def upload_orders(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Defer with ephemeral=True to keep the response private and prevent timeout
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Log the button interaction with detailed information
        log_button_interaction(interaction, "Clicked Upload Orders button", "User initiated order upload process")
        
        # Create a view with two options: Custom Sheet and Existing Sheet
        class UploadSheetSelectView(View):
            def __init__(self, user_id):
                super().__init__(timeout=180)
                self.user_id = user_id

            @discord.ui.button(label="📝 Custom Sheet", style=discord.ButtonStyle.primary)
            async def custom_sheet(self, select_interaction: discord.Interaction, button: discord.ui.Button):
                # Log the button interaction
                log_button_interaction(select_interaction, "Clicked Custom Sheet button", "User chose to create custom sheet for upload")
                await select_interaction.response.send_modal(SheetNameModal(self.user_id, "new"))
                self.stop()

            @discord.ui.button(label="📋 Existing Sheet", style=discord.ButtonStyle.secondary)
            async def existing_sheet(self, select_interaction: discord.Interaction, button: discord.ui.Button):
                # Log the button interaction
                log_button_interaction(select_interaction, "Clicked Existing Sheet button", "User chose to use existing sheet for upload")
                await select_interaction.response.defer(ephemeral=True)
                
                try:
                    # Already imported at top
                    # Pass user ID to get their specific worksheets
                    user_sheets = await get_worksheets(user_id=self.user_id)
                    
                    if not user_sheets:
                        await select_interaction.followup.send("❌ No sheets found in your Google Sheet. Please check that your sheet is properly shared with the bot.", ephemeral=True)
                        return
                    
                    # Show all sheets to the user
                    options = [
                        discord.SelectOption(label=sheet.title, value=sheet.title)
                        for sheet in user_sheets
                    ]
                    
                    if len(user_sheets) > 10:
                        content = f"⚠️ You have {len(user_sheets)} sheets! Only the first 10 are shown.\nSelect a sheet to upload orders to:"
                    else:
                        content = "Select a sheet to upload orders to:"
                        
                    select = discord.ui.Select(
                        placeholder="Select a sheet...",
                        min_values=1,
                        max_values=1,
                        options=options
                    )
                    async def select_callback(select_interaction2):
                        sheet_name = select.values[0]
                        user_upload_state[self.user_id] = {"sheet_choice": f"existing:{sheet_name}"}
                        await select_interaction2.response.send_message(f"✅ {sheet_name} selected. Now, please attach your text file with orders to this DM.", ephemeral=True)
                    select.callback = select_callback
                    view = View()
                    view.add_item(select)
                    await select_interaction.followup.send(content, view=view, ephemeral=True)
                except Exception as e:
                    await select_interaction.followup.send(f"❌ Error loading sheets: {str(e)}. Please try again in a moment.", ephemeral=True)
        
        # Show the two options
        content = "📦 **Upload Orders**\n\nChoose how you want to upload your orders:"
        view = UploadSheetSelectView(interaction.user.id)
        await interaction.followup.send(content, view=view, ephemeral=True)

    @discord.ui.button(label="Cancel Orders", style=discord.ButtonStyle.danger, custom_id="cancel_orders_button")
    async def cancel_orders(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle the cancel orders button click."""
        await interaction.response.defer(ephemeral=False)
        
        # Log the button interaction
        log_button_interaction(interaction, "Clicked Cancel Orders button", "User initiated cancel orders process")
        try:
            # Get user's worksheets
            user_sheets = await get_worksheets(user_id=interaction.user.id)
            
            if not user_sheets:
                await interaction.followup.send("❌ No sheets found in your Google Sheet. Please check that your sheet is properly shared with the bot.", ephemeral=True)
                return
            
            # Show all sheets to the user
            options = [
                discord.SelectOption(label=sheet.title, value=sheet.title)
                for sheet in user_sheets[:10]  # Limit to 10 sheets
            ]
            
            if len(user_sheets) > 10:
                content = f"⚠️ You have {len(user_sheets)} sheets! Only the first 10 are shown.\nSelect one or more sheets to cancel orders from:"
            else:
                content = "Select one or more sheets to cancel orders from:"
                
            select = discord.ui.Select(
                placeholder="Select one or more sheets...",
                min_values=1,
                max_values=min(10, len(user_sheets)),
                options=options
            )
            
            async def select_callback(select_interaction):
                sheet_names = select.values
                
                if len(sheet_names) == 1:
                    # Single sheet - use existing format
                    user_upload_state[interaction.user.id] = {
                        "cancel_sheet_choice": f"existing:{sheet_names[0]}"
                    }
                    await select_interaction.response.send_message(
                        f"✅ Selected: {sheet_names[0]}. Please upload your cancellation file (CSV or TXT with order numbers).",
                        ephemeral=True
                    )
                else:
                    # Multiple sheets - use existing format
                    user_upload_state[interaction.user.id] = {
                        "cancel_sheet_choice": "multiple",
                        "selected_sheets": sheet_names
                    }
                    await select_interaction.response.send_message(
                        f"✅ Selected {len(sheet_names)} sheets. Please upload your cancellation file (CSV or TXT with order numbers).",
                        ephemeral=True
                    )
            
            select.callback = select_callback
            view = View()
            view.add_item(select)
            await interaction.followup.send(content, view=view, ephemeral=True)
            
        except Exception as e:
            logging.error(f"Error in cancel_orders button: {str(e)}")
            await interaction.followup.send(f"❌ Error loading sheets: {str(e)}. Please try again.", ephemeral=True)

    @discord.ui.button(label="Track Orders", style=discord.ButtonStyle.primary, custom_id="tracking_button")
    async def track_orders(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle the tracking button click."""
        await interaction.response.defer(ephemeral=False)
        
        # Log the button interaction with detailed information
        log_button_interaction(interaction, "Clicked Track Orders button", "User initiated tracking upload process")
        try:
            # Already imported at top
            # Pass user ID to get their specific worksheets
            user_sheets = await get_worksheets(user_id=interaction.user.id)
            
            if not user_sheets:
                await interaction.followup.send("❌ No sheets found in your Google Sheet. Please check that your sheet is properly shared with the bot.", ephemeral=True)
                return
            
            # Show all sheets to the user (don't filter out any)
            options = [
                discord.SelectOption(label=sheet.title, value=sheet.title)
                for sheet in user_sheets
            ]
            
            if len(user_sheets) > 10:
                content = f"⚠️ You have {len(user_sheets)} sheets! Only the first 10 are shown.\nSelect one or more sheets:"
            else:
                content = "Select one or more sheets:"
                
            select = discord.ui.Select(
                placeholder="Select one or more sheets...",
                min_values=1,
                max_values=min(10, len(user_sheets)),
                options=options
            )
            async def select_callback(select_interaction):
                sheet_names = select.values
                user_upload_state[interaction.user.id] = {"tracking_sheet_choice": "multiple", "selected_sheets": sheet_names}
                await select_interaction.response.send_message(f"✅ Selected: {', '.join(sheet_names)}. Now, please attach your CSV file with tracking numbers to this DM.", ephemeral=True)
            select.callback = select_callback
            view = View()
            view.add_item(select)
            await interaction.followup.send(content, view=view, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error loading sheets: {str(e)}. Please try again in a moment.", ephemeral=True)

    @discord.ui.button(label="Mark received", style=discord.ButtonStyle.success, custom_id="mark_received_button")
    async def mark_received(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=False)
        
        # Log the button interaction with detailed information
        log_button_interaction(interaction, "Clicked Mark Received button", "User initiated mark received process")
        try:
            await asyncio.sleep(1.0)
            # Already imported at top
            # Pass user ID to get their specific worksheets
            user_sheets = await get_worksheets(user_id=interaction.user.id)
            
            if not user_sheets:
                await interaction.followup.send("❌ No sheets found in your Google Sheet. Please check that your sheet is properly shared with the bot.", ephemeral=True)
                return
            
            # Show all sheets to the user (don't filter out any)
            options = [
                discord.SelectOption(label=sheet.title, value=sheet.title)
                for sheet in user_sheets
            ]
            
            if len(user_sheets) > 10:
                content = f"⚠️ You have {len(user_sheets)} sheets! Only the first 10 are shown.\nSelect one or more sheets:"
            else:
                content = "Select one or more sheets:"
                
            select = discord.ui.Select(
                placeholder="Select one or more sheets...",
                min_values=1,
                max_values=min(10, len(user_sheets)),
                options=options
            )
            async def select_callback(select_interaction):
                sheet_names = select.values
                user_upload_state[interaction.user.id] = {"mark_received_sheet_choice": "multiple", "selected_sheets": sheet_names}
                await select_interaction.response.send_message(f"✅ Selected: {', '.join(sheet_names)}. Now, please attach your CSV file with received trackings to this DM.", ephemeral=True)
            select.callback = select_callback
            view = View()
            view.add_item(select)
            await interaction.followup.send(content, view=view, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error loading sheets: {str(e)}. Please try again in a moment.", ephemeral=True)

    @discord.ui.button(label="Reconcile Charges", style=discord.ButtonStyle.secondary, custom_id="reconcile_charges_button")
    async def reconcile_charges(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=False)
        
        # Log the button interaction with detailed information
        log_button_interaction(interaction, "Clicked Reconcile Charges button", "User initiated charge reconciliation process")
        try:
            await asyncio.sleep(1.0)
            # Already imported at top
            # Pass user ID to get their specific worksheets
            user_sheets = await get_worksheets(user_id=interaction.user.id)
            
            if not user_sheets:
                await interaction.followup.send("❌ No sheets found in your Google Sheet. Please check that your sheet is properly shared with the bot.", ephemeral=True)
                return
            
            # Show all sheets to the user (don't filter out any)
            options = [
                discord.SelectOption(label=sheet.title, value=sheet.title)
                for sheet in user_sheets
            ]
            
            if len(user_sheets) > 10:
                content = f"⚠️ You have {len(user_sheets)} sheets! Only the first 10 are shown.\nSelect one or more sheets:"
            else:
                content = "Select one or more sheets:"
                
            select = discord.ui.Select(
                placeholder="Select one or more sheets...",
                min_values=1,
                max_values=min(10, len(user_sheets)),
                options=options
            )
            async def select_callback(select_interaction):
                sheet_names = select.values
                user_upload_state[interaction.user.id] = {
                    "reconcile_charges_sheet_choices": sheet_names,
                    "reconcile_charges_mode": "multi_csv"  # New mode for multiple CSV support
                }
                
                if len(sheet_names) == 1:
                    # Single sheet - simple mode
                    await select_interaction.response.send_message(
                        f"✅ Selected: {sheet_names[0]}. Please attach your CSV file with credit card charges to this DM.", 
                        ephemeral=True
                    )
                else:
                    # Multiple sheets - multi-CSV mode
                    await select_interaction.response.send_message(
                        f"✅ Selected {len(sheet_names)} sheets: {', '.join(sheet_names)}\n\n"
                        f"**Multi-CSV Mode**: You can now upload multiple CSV files.\n"
                        f"• Upload one CSV to process against all selected sheets\n"
                        f"• Upload multiple CSVs to match specific files to specific sheets\n\n"
                        f"Please attach your CSV file(s) to this DM.", 
                        ephemeral=True
                    )
            select.callback = select_callback
            view = View()
            view.add_item(select)
            await interaction.followup.send(content, view=view, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error loading sheets: {str(e)}. Please try again in a moment.", ephemeral=True)

class SheetSelectView(View):
    def __init__(self, user_id):
        super().__init__(timeout=180) # Timeout after 3 minutes
        self.user_id = user_id

    @discord.ui.button(label="Sheet1", style=discord.ButtonStyle.primary)
    async def sheet1(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_upload_state[self.user_id] = {"sheet_choice": "sheet1"}
        await interaction.response.send_message("✅ Sheet1 selected. Now, please attach your text file with orders to this DM.", ephemeral=True)
        self.stop()

    @discord.ui.button(label="New Sheet", style=discord.ButtonStyle.secondary)
    async def new_sheet(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SheetNameModal(self.user_id, "new"))
        self.stop()

    @discord.ui.button(label="Sheet1 + New Sheet", style=discord.ButtonStyle.secondary)
    async def both_sheets(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SheetNameModal(self.user_id, "both"))
        self.stop()

    @discord.ui.button(label="Existing Sheet", style=discord.ButtonStyle.success)
    async def existing_sheet(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)  # Defer to avoid timeout
        
        try:
            # Add delay before reading sheets to prevent rate limiting
            await asyncio.sleep(1.0)
            
            # Already imported at top
            filtered_sheets = [sheet for sheet in get_worksheets() if sheet.title != "Sheet1"]
            recent_sheets = filtered_sheets[:10]
            options = [
                discord.SelectOption(label=sheet.title, value=sheet.title)
                for sheet in recent_sheets
            ]
            if not options:
                await interaction.channel.send("❌ No other sheets available.", ephemeral=True)
                return
            if len(filtered_sheets) > 10:
                content = "⚠️ Too many sheets! Only the 10 leftmost sheets (closest to Sheet1) are shown.\nSelect an existing sheet:"
            else:
                content = "Select an existing sheet:"
            select = discord.ui.Select(
                placeholder="Select an existing sheet...",
                min_values=1,
                max_values=1,
                options=options
            )
            async def select_callback(select_interaction):
                sheet_name = select.values[0]
                user_upload_state[self.user_id] = {"sheet_choice": f"existing:{sheet_name}"}
                await select_interaction.response.send_message(f"✅ {sheet_name} selected. Now, please attach your text file with orders to this DM.", ephemeral=True)
                self.stop()
            select.callback = select_callback
            view = View()
            view.add_item(select)
            await interaction.followup.send(content, view=view, ephemeral=True)
        except Exception as e:
            await interaction.channel.send(f"❌ Error loading sheets: {str(e)}. Please try again in a moment.", ephemeral=True)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.grey, row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Go back to the main menu
        welcome_msg = (
            "🤖 **Discord Order Bot**\n\n"
            "Welcome! Use the button below to upload orders."
        )
        await interaction.response.edit_message(content=welcome_msg, view=WelcomeView(interaction.client)) # Pass bot instance to WelcomeView
        self.stop()

class SheetNameModal(discord.ui.Modal, title='Enter Sheet Name'):
    def __init__(self, user_id, sheet_type):
        super().__init__()
        self.user_id = user_id
        self.sheet_type = sheet_type
        self.sheet_name_input = discord.ui.TextInput(label='Sheet Name', placeholder='e.g., Orders_July_2024')
        self.add_item(self.sheet_name_input)

    async def on_submit(self, interaction: discord.Interaction):
        sheet_name = self.sheet_name_input.value.strip()
        if not sheet_name:
            await interaction.response.send_message("❌ Sheet name cannot be empty. Operation cancelled.", ephemeral=True)
            return
        user_upload_state[self.user_id] = {"sheet_choice": self.sheet_type, "new_sheet_name": sheet_name}
        await interaction.response.send_message(f"✅ '{sheet_name}' selected. Now, please attach your text file with orders to this DM.", ephemeral=True)

class UndoView(View):
    def __init__(self, undo_action_callback):
        super().__init__(timeout=300) # 5 minutes to undo
        self.undo_action_callback = undo_action_callback

    @discord.ui.button(label="Undo Last Upload", style=discord.ButtonStyle.red)
    async def undo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            await self.undo_action_callback(interaction)
            await interaction.followup.send("✅ Last upload successfully undone!", ephemeral=False)
            self.stop()
        except Exception as e:
            logging.error(f"Error during undo operation: {e}")
            await interaction.followup.send(f"❌ Failed to undo last upload: {e}", ephemeral=False)

class SummaryView(View):
    def __init__(self, ctx):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.value = None

    @discord.ui.button(label="Today", style=discord.ButtonStyle.primary)
    async def today(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.value = "today"
        self.stop()

    @discord.ui.button(label="This Week", style=discord.ButtonStyle.primary)
    async def week(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.value = "week"
        self.stop()

    @discord.ui.button(label="This Month", style=discord.ButtonStyle.primary)
    async def month(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.value = "month"
        self.stop()

    @discord.ui.button(label="All Time", style=discord.ButtonStyle.primary)
    async def all(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.value = "all"
        self.stop()

class FileUploadView(View):
    def __init__(self, ctx):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.value = None
        # Dynamically add the select if there are existing sheets
        if worksheets:
            self.add_item(ExistingSheetSelect(self))

    @discord.ui.button(label="Upload to Sheet1", style=discord.ButtonStyle.green)
    async def sheet1(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "sheet1"
        await interaction.response.send_message("✅ Will upload to Sheet1")
        self.stop()

    @discord.ui.button(label="Create New Sheet", style=discord.ButtonStyle.primary)
    async def new_sheet(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "new"
        await interaction.response.send_message("✅ Will create a new sheet with today's date")
        self.stop()

    @discord.ui.button(label="Custom Sheet Name", style=discord.ButtonStyle.secondary)
    async def custom_sheet(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Please enter your custom sheet name:", ephemeral=True)
        
        def check(m):
            return m.author == self.ctx.author and m.channel == self.ctx.channel
        
        try:
            msg = await self.ctx.bot.wait_for('message', check=check, timeout=60.0)
            self.value = f"custom:{msg.content.strip()}"
            await interaction.followup.send(f"✅ Will create new sheet: {msg.content.strip()}", ephemeral=True)
            self.stop()
        except asyncio.TimeoutError:
            await interaction.followup.send("❌ No sheet name provided. Operation cancelled.", ephemeral=True)
            self.value = None
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = None
        await interaction.response.send_message("❌ Operation cancelled")
        self.stop()

class ExistingSheetSelect(discord.ui.Select):
    def __init__(self, parent_view):
        # List all sheet names except Sheet1 (since it's already a button)
        options = [
            discord.SelectOption(label=sheet.title, value=sheet.title)
            for sheet in worksheets if sheet.title != "Sheet1"
        ]
        super().__init__(
            placeholder="Select an existing sheet...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        sheet_name = self.values[0]
        self.parent_view.value = f"existing:{sheet_name}"
        await interaction.response.send_message(f"✅ Will upload to existing sheet: {sheet_name}")
        self.parent_view.stop()

class MainMenuView(View):
    def __init__(self, ctx):
        super().__init__(timeout=None)  # No timeout for main menu
        self.ctx = ctx

    @discord.ui.button(label="📁 Upload Orders", style=discord.ButtonStyle.green, emoji="📁")
    async def upload_orders(self, interaction: discord.Interaction, button: discord.ui.Button):
        log_activity(interaction.user.id, "Button Click", "Upload Orders button")
        await interaction.response.defer()
        
        # Create file upload view
        view = FileUploadView(self.ctx)
        await self.ctx.send("📁 **Upload Orders**\n\nPlease attach a text file with orders:", view=view)
        
        # Wait for button interaction
        await view.wait()
        
        if view.value is None:
            await self.ctx.send("❌ Operation cancelled")
            return
            
        # Store the sheet choice for later use
        self.ctx.bot.sheet_choice = view.value
        
        # Now ask for file upload
        await self.ctx.send("✅ Sheet selected! Now please attach your text file with orders.")

    @discord.ui.button(label="❌ Cancel Orders", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel_orders(self, interaction: discord.Interaction, button: discord.ui.Button):
        log_activity(interaction.user.id, "Button Click", "Cancel Orders button")
        await interaction.response.defer()
        
        # Go directly to existing sheets dropdown since we're cancelling existing orders
        try:
            # Already imported at top
            filtered_sheets = [sheet for sheet in get_worksheets() if sheet.title != "Sheet1"]
            recent_sheets = filtered_sheets[:10]
            options = [
                discord.SelectOption(label=sheet.title, value=sheet.title)
                for sheet in recent_sheets
            ]
            if not options:
                await interaction.followup.send("❌ No other sheets available for cancellation.", ephemeral=True)
                return
            if len(filtered_sheets) > 10:
                content = "⚠️ Too many sheets! Only the 10 leftmost sheets (closest to Sheet1) are shown.\nSelect an existing sheet to cancel orders from:"
            else:
                content = "Select an existing sheet to cancel orders from:"
            select = discord.ui.Select(
                placeholder="Select an existing sheet...",
                min_values=1,
                max_values=1,
                options=options
            )
            async def select_callback(select_interaction):
                sheet_name = select.values[0]
                user_upload_state[interaction.user.id] = {"cancel_sheet_choice": f"existing:{sheet_name}"}
                await select_interaction.response.send_message(f"✅ {sheet_name} selected. Now, please attach your CSV or TXT file with order numbers to this DM.", ephemeral=True)
            select.callback = select_callback
            view = View()
            view.add_item(select)
            await interaction.followup.send(content, view=view)
        except Exception as e:
            await interaction.channel.send(f"❌ Error loading sheets: {str(e)}. Please try again in a moment.", ephemeral=True)

    @discord.ui.button(label="📦 Upload Trackings", style=discord.ButtonStyle.primary, emoji="📦")
    async def upload_trackings(self, interaction: discord.Interaction, button: discord.ui.Button):
        log_activity(interaction.user.id, "Button Click", "Upload Trackings button")
        await interaction.response.defer()
        
        # Create tracking sheet selection view
        view = TrackingSheetSelectionView(self.ctx)
        await self.ctx.send("📦 **Upload Trackings**\n\nPlease attach a CSV file with tracking numbers, then select which sheet to update:", view=view)

    @discord.ui.button(label="📊 Summary", style=discord.ButtonStyle.secondary, emoji="📊")
    async def show_summary(self, interaction: discord.Interaction, button: discord.ui.Button):
        log_activity(interaction.user.id, "Button Click", "Summary button")
        await interaction.response.defer()
        
        # Create summary view
        view = SummaryView(self.ctx)
        await self.ctx.send("📊 Select time period for summary:", view=view)
        
        # Wait for button interaction
        await view.wait()
        
        if view.value is None:
            await self.ctx.send("❌ Operation timed out")
            return
            
        # Get the period from button selection
        period = view.value
        
        try:
            # Get all orders from all sheets
            all_values = get_all_orders()
            
            if not all_values:
                await self.ctx.send("❌ No data found in any sheet")
                return
                
            now = datetime.now()
            
            # Determine date range based on selected period
            if period == "all":
                start_date = None
                period_name = "All Time"
            elif period == "today":
                start_date = now.strftime('%Y-%m-%d')
                period_name = "Today"
            elif period == "week":
                start_date = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
                period_name = "This Week"
            elif period == "month":
                start_date = now.replace(day=1).strftime('%Y-%m-%d')
                period_name = "This Month"
                
            # Process orders and create summary
            matching_orders = []
            canceled_orders = 0
            
            for row in all_values:
                try:
                    if start_date is None or row[0] >= start_date:
                        # Check if order is canceled
                        if len(row) > 8 and row[8].lower() == 'canceled':
                            canceled_orders += 1
                            continue
                        matching_orders.append(row)
                except (ValueError, IndexError) as e:
                    continue
                    
            if matching_orders:
                # Calculate statistics
                total_revenue = 0
                product_stats = {}
                tracking_uploaded = 0
                
                for order in matching_orders:
                    try:
                        price = float(order[3].replace('$', '').strip())
                        quantity = int(order[4])
                        order_revenue = price * quantity
                        total_revenue += order_revenue
                        
                        # Product stats
                        product = order[2]
                        if product not in product_stats:
                            product_stats[product] = 0
                        product_stats[product] += quantity
                        
                        # Check if tracking was uploaded
                        if len(order) > 8 and order[8].strip():  # Assuming tracking is in column 9
                            tracking_uploaded += 1
                        
                    except (ValueError, IndexError) as e:
                        continue
                
                # Create clean summary message
                summary = f"📊 **{period_name}'s Summary**\n\n"
                
                # Products Ordered
                summary += f"📦 **Products Ordered:**\n"
                if product_stats:
                    for product, qty in product_stats.items():
                        summary += f"• {product}: {qty} units\n"
                else:
                    summary += "• No products ordered\n"
                
                # Trackings Uploaded
                summary += f"\n📋 **Trackings Uploaded:** {tracking_uploaded}\n"
                
                # Order Totals
                summary += f"💰 **Order Totals:** {format_currency(total_revenue)}\n"
                
                # Orders Canceled
                summary += f"❌ **Orders Canceled:** {canceled_orders}\n"
                
                # Total Orders
                summary += f"📈 **Total Orders:** {len(matching_orders)}"
                
                await self.ctx.send(summary)
            else:
                await self.ctx.send(f"No orders found for {period_name.lower()}")
                
        except Exception as e:
            error_msg = f"Error in summary command: {str(e)}"
            logging.error(error_msg)
            await self.ctx.send(f"❌ {error_msg}")

    @discord.ui.button(label="❓ Help", style=discord.ButtonStyle.secondary, emoji="❓")
    async def show_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        help_text = """
🤖 **Discord Order Bot - Main Menu**

**Available Actions:**

📁 **Upload Orders** - Upload a text file with orders to process
❌ **Cancel Orders** - Cancel orders using a CSV file with order numbers
📦 **Upload Trackings** - Update tracking numbers using a CSV file
📊 **Summary** - View order summaries for different time periods
❓ **Help** - Show this help message

**How to use:**
1. Click any button to start that action
2. Follow the prompts and attach files when requested
3. Use the interactive buttons to make selections

**File Formats:**
• **Orders**: Text files with "Successful Checkout" messages
• **Cancellations**: CSV files with order numbers
• **Trackings**: CSV files with Order and Tracking columns

**Need more options?** Use `!commands` to see all available text commands.
"""
        await self.ctx.send(help_text)

class CancelSheetSelectView(View):
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id

    @discord.ui.button(label="Sheet1", style=discord.ButtonStyle.primary)
    async def sheet1(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_upload_state[self.user_id] = {"cancel_sheet_choice": "sheet1"}
        await interaction.response.send_message("✅ Sheet1 selected. Now, please attach your CSV or TXT file with order numbers to this DM.", ephemeral=True)
        self.stop()

    @discord.ui.button(label="New Sheet", style=discord.ButtonStyle.secondary)
    async def new_sheet(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SheetNameModal(self.user_id, "cancel_new"))
        self.stop()

    @discord.ui.button(label="Sheet1 + New Sheet", style=discord.ButtonStyle.secondary)
    async def both_sheets(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SheetNameModal(self.user_id, "cancel_both"))
        self.stop()

    @discord.ui.button(label="Multiple Sheets", style=discord.ButtonStyle.success)
    async def multiple_sheets(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)  # Defer to avoid timeout
        
        try:
            # Add delay before reading sheets to prevent rate limiting
            await asyncio.sleep(1.0)
            
            # Already imported at top
            all_sheets = get_worksheets()
            
            if not all_sheets:
                await interaction.channel.send("❌ No sheets available.", ephemeral=True)
                return
            
            # Create a beautiful multi-sheet selection interface
            content = "📋 **Multi-Sheet Selection**\n\nSelect the sheets you want to search for orders:"
            
            class MultiSheetSelectView(View):
                def __init__(self, user_id, sheets):
                    super().__init__(timeout=300)  # 5 minute timeout
                    self.user_id = user_id
                    self.sheets = sheets
                    self.selected_sheets = set()
                    
                    # Create sheet selection buttons (max 20 to keep UI clean)
                    for i, sheet in enumerate(sheets[:20]):
                        row = min(i // 4, 4)  # Cap row at 4
                        
                        def make_callback(sheet_name):
                            async def callback(interaction: discord.Interaction):
                                if sheet_name in self.selected_sheets:
                                    self.selected_sheets.remove(sheet_name)
                                    # Update button style to show deselected
                                    interaction.data["components"][0]["components"][i]["style"] = 2  # Secondary
                                    await interaction.response.send_message(f"❌ Removed **{sheet_name}** from selection", ephemeral=True)
                                else:
                                    self.selected_sheets.add(sheet_name)
                                    # Update button style to show selected
                                    interaction.data["components"][0]["components"][i]["style"] = 3  # Success
                                    await interaction.response.send_message(f"✅ Added **{sheet_name}** to selection", ephemeral=True)
                            return callback
                        
                        # Create button with checkbox emoji
                        button = discord.ui.Button(
                            label=f"☐ {sheet.title}",
                            style=discord.ButtonStyle.secondary,
                            row=row,
                            custom_id=f"sheet_{sheet.title}"
                        )
                        button.callback = make_callback(sheet.title)
                        self.add_item(button)
                    
                    # Add action buttons at the bottom
                    if len(sheets) > 20:
                        info_button = discord.ui.Button(
                            label=f"📊 Showing 20 of {len(sheets)} sheets",
                            style=discord.ButtonStyle.grey,
                            row=5,
                            disabled=True
                        )
                        self.add_item(info_button)
                    
                    # Confirm button
                    confirm_button = discord.ui.Button(
                        label="✅ Confirm Selection",
                        style=discord.ButtonStyle.green,
                        row=6
                    )
                    async def confirm_callback(confirm_interaction):
                        if not self.selected_sheets:
                            await confirm_interaction.response.send_message("❌ **No sheets selected!** Please select at least one sheet.", ephemeral=True)
                            return
                        
                        selected_list = list(self.selected_sheets)
                        user_upload_state[self.user_id] = {"cancel_sheet_choice": "multiple", "selected_sheets": selected_list}
                        
                        # Create a nice summary message
                        if len(selected_list) == 1:
                            summary = f"✅ **1 sheet selected:** {selected_list[0]}"
                        else:
                            summary = f"✅ **{len(selected_list)} sheets selected:**\n• " + "\n• ".join(selected_list)
                        
                        await confirm_interaction.response.send_message(f"{summary}\n\n📎 **Next step:** Please attach your CSV or TXT file with order numbers to this DM.", ephemeral=True)
                        self.stop()
                    
                    confirm_button.callback = confirm_callback
                    self.add_item(confirm_button)
                    
                    # Cancel button
                    cancel_button = discord.ui.Button(
                        label="❌ Cancel",
                        style=discord.ButtonStyle.red,
                        row=6
                    )
                    async def cancel_callback(cancel_interaction):
                        await cancel_interaction.response.send_message("❌ **Sheet selection cancelled.**", ephemeral=True)
                        self.stop()
                    
                    cancel_button.callback = cancel_callback
                    self.add_item(cancel_button)
            
            view = MultiSheetSelectView(self.user_id, all_sheets)
            await interaction.followup.send(content, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.channel.send(f"❌ Error loading sheets: {str(e)}. Please try again in a moment.", ephemeral=True)

    @discord.ui.button(label="Existing Sheet", style=discord.ButtonStyle.success)
    async def existing_sheet(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)  # Defer to avoid timeout
        
        try:
            # Add delay before reading sheets to prevent rate limiting
            await asyncio.sleep(1.0)
            
            # Already imported at top
            filtered_sheets = [sheet for sheet in get_worksheets() if sheet.title != "Sheet1"]
            recent_sheets = filtered_sheets[:10]
            options = [
                discord.SelectOption(label=sheet.title, value=sheet.title)
                for sheet in recent_sheets
            ]
            if not options:
                await interaction.channel.send("❌ No other sheets available.", ephemeral=True)
                return
            if len(filtered_sheets) > 10:
                content = "⚠️ Too many sheets! Only the 10 leftmost sheets (closest to Sheet1) are shown.\nSelect an existing sheet:"
            else:
                content = "Select an existing sheet:"
            select = discord.ui.Select(
                placeholder="Select an existing sheet...",
                min_values=1,
                max_values=1,
                options=options
            )
            async def select_callback(select_interaction):
                sheet_name = select.values[0]
                user_upload_state[self.user_id] = {"cancel_sheet_choice": f"existing:{sheet_name}"}
                await select_interaction.response.send_message(f"✅ {sheet_name} selected. Now, please attach your CSV or TXT file with order numbers to this DM.", ephemeral=True)
                self.stop()
            select.callback = select_callback
            view = View()
            view.add_item(select)
            await interaction.followup.send(content, view=view, ephemeral=True)
        except Exception as e:
            await interaction.channel.send(f"❌ Error loading sheets: {str(e)}. Please try again in a moment.", ephemeral=True)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.grey, row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Go back to the main menu
        welcome_msg = (
            "🤖 **Discord Order Bot**\n\n"
            "Welcome! Use the button below to upload orders."
        )
        await interaction.response.edit_message(content=welcome_msg, view=WelcomeView(interaction.client)) # Pass bot instance to WelcomeView
        self.stop()

class TrackingSheetSelectView(View):
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id

    @discord.ui.button(label="Sheet1", style=discord.ButtonStyle.primary)
    async def sheet1(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_upload_state[self.user_id] = {"tracking_sheet_choice": "sheet1"}
        await interaction.response.send_message("✅ Sheet1 selected. Now, please attach your CSV file with tracking numbers to this DM.", ephemeral=True)
        self.stop()

    @discord.ui.button(label="New Sheet", style=discord.ButtonStyle.secondary)
    async def new_sheet(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SheetNameModal(self.user_id, "tracking_new"))
        self.stop()

    @discord.ui.button(label="Sheet1 + New Sheet", style=discord.ButtonStyle.secondary)
    async def both_sheets(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SheetNameModal(self.user_id, "tracking_both"))
        self.stop()

    @discord.ui.button(label="Existing Sheet", style=discord.ButtonStyle.success)
    async def existing_sheet(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)  # Defer to avoid timeout
        
        try:
            # Add delay before reading sheets to prevent rate limiting
            await asyncio.sleep(1.0)
            
            # Already imported at top
            filtered_sheets = [sheet for sheet in get_worksheets() if sheet.title != "Sheet1"]
            recent_sheets = filtered_sheets[:10]
            options = [
                discord.SelectOption(label=sheet.title, value=sheet.title)
                for sheet in recent_sheets
            ]
            if not options:
                await interaction.channel.send("❌ No other sheets available.", ephemeral=True)
                return
            if len(filtered_sheets) > 10:
                content = "⚠️ Too many sheets! Only the 10 leftmost sheets (closest to Sheet1) are shown.\nSelect an existing sheet:"
            else:
                content = "Select an existing sheet:"
            select = discord.ui.Select(
                placeholder="Select an existing sheet...",
                min_values=1,
                max_values=1,
                options=options
            )
            async def select_callback(select_interaction):
                sheet_name = select.values[0]
                user_upload_state[self.user_id] = {"tracking_sheet_choice": f"existing:{sheet_name}"}
                await select_interaction.response.send_message(f"✅ {sheet_name} selected. Now, please attach your CSV file with tracking numbers to this DM.", ephemeral=True)
                self.stop()
            select.callback = select_callback
            view = View()
            view.add_item(select)
            await interaction.followup.send(content, view=view, ephemeral=True)
        except Exception as e:
            await interaction.channel.send(f"❌ Error loading sheets: {str(e)}. Please try again in a moment.", ephemeral=True)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.grey, row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Go back to the main menu
        welcome_msg = (
            "🤖 **Discord Order Bot**\n\n"
            "Welcome! Use the button below to upload orders."
        )
        await interaction.response.edit_message(content=welcome_msg, view=WelcomeView(interaction.client)) # Pass bot instance to WelcomeView
        self.stop()

class TrackingSheetSelectionView(View):
    def __init__(self, ctx):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.value = None

    @discord.ui.button(label="Recent Sheets", style=discord.ButtonStyle.primary)
    async def recent_sheets(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "recent"
        await interaction.response.send_message("✅ Will search in recent sheets")
        self.stop()

    @discord.ui.button(label="Custom Sheet", style=discord.ButtonStyle.secondary)
    async def custom_sheet(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Please enter your custom sheet name:", ephemeral=True)
        
        def check(m):
            return m.author == self.ctx.author and m.channel == self.ctx.channel
        
        try:
            msg = await self.ctx.bot.wait_for('message', check=check, timeout=60.0)
            self.value = msg.content.strip()
            await interaction.followup.send(f"✅ Will search in sheet: {msg.content.strip()}", ephemeral=True)
            self.stop()
        except asyncio.TimeoutError:
            await interaction.followup.send("❌ No sheet name provided. Operation cancelled.", ephemeral=True)
            self.value = None
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = None
        await interaction.response.send_message("❌ Operation cancelled")
        self.stop()

class ProgressView(View):
    def __init__(self, total_steps: int):
        super().__init__(timeout=None)
        self.total_steps = total_steps
        self.current_step = 0
        self.message = None
        
    async def update_progress(self, step: int, description: str):
        self.current_step = step
        progress = int((step / self.total_steps) * 100)
        bar_length = 20
        filled_length = int(bar_length * step // self.total_steps)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        if self.message:
            await self.message.edit(content=f"```\nProgress: [{bar}] {progress}%\n{description}\n```")

class ConfirmationView(View):
    def __init__(self, timeout: int = 180):
        super().__init__(timeout=timeout)
        self.value = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        await interaction.response.send_message("✅ Confirmed! Processing deletion...", ephemeral=True)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        await interaction.response.send_message("❌ Operation cancelled.", ephemeral=True)
        self.stop()

class UpdatedOrdersView(View):
    def __init__(self, updated_orders):
        super().__init__(timeout=180)
        self.updated_orders = updated_orders

    @discord.ui.button(label="View All Updated Orders", style=discord.ButtonStyle.primary)
    async def view_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Chunk the orders if too many
        chunk_size = 20
        chunks = [self.updated_orders[i:i+chunk_size] for i in range(0, len(self.updated_orders), chunk_size)]
        for chunk in chunks:
            msg = "\n".join(f"• {order}" for order in chunk)
            await interaction.followup.send(f"**Updated Orders:**\n{msg}", ephemeral=True)
        await interaction.response.defer()
        self.stop()

class CopyTrackingView(View):
    def __init__(self, tracking_numbers):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.tracking_numbers = tracking_numbers

    @discord.ui.button(label="📋 Copy All Trackings", style=discord.ButtonStyle.green, emoji="📋")
    async def copy_trackings(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Discord message limit is 2000 characters
        max_length = 2000
        
        # Calculate the overhead for the message format
        # Format: "📋 **Copy these tracking numbers (part X/Y):**\n```\n{tracking_text}\n```\nClick the text above to select all, then copy (Ctrl+C / Cmd+C)"
        base_overhead = len("📋 **Copy these tracking numbers (part 1/1):**\n```\n\n```\nClick the text above to select all, then copy (Ctrl+C / Cmd+C)")
        
        # Available space for tracking numbers
        available_space = max_length - base_overhead
        
        # Split tracking numbers into chunks
        chunks = []
        current_chunk = []
        current_chunk_length = 0
        
        for tracking in self.tracking_numbers:
            # Each tracking number adds its length + 1 for newline
            tracking_length = len(tracking) + 1
            
            # If adding this tracking would exceed the limit, start a new chunk
            if current_chunk_length + tracking_length > available_space:
                if current_chunk:  # Only add non-empty chunks
                    chunks.append(current_chunk)
                current_chunk = [tracking]
                current_chunk_length = tracking_length
            else:
                current_chunk.append(tracking)
                current_chunk_length += tracking_length
        
        # Add the last chunk if it has content
        if current_chunk:
            chunks.append(current_chunk)
        
        # If no chunks were created, create a single empty chunk
        if not chunks:
            chunks = [[]]
        
        # Send each chunk as a separate message
        for i, chunk in enumerate(chunks):
            tracking_text = "\n".join(chunk) if chunk else "No tracking numbers available"
            msg = f"📋 **Copy these tracking numbers (part {i+1}/{len(chunks)}):**\n```\n{tracking_text}\n```\nClick the text above to select all, then copy (Ctrl+C / Cmd+C)"
            
            try:
                if i == 0:
                    await interaction.response.send_message(msg, ephemeral=True)
                else:
                    await interaction.followup.send(msg, ephemeral=True)
            except discord.errors.HTTPException as e:
                if "Must be 2000 or fewer in length" in str(e):
                    # If still too long, send a simplified message
                    simple_msg = f"📋 **Tracking numbers (part {i+1}/{len(chunks)}):**\n```\n{tracking_text[:1800]}{'...' if len(tracking_text) > 1800 else ''}\n```"
                    if i == 0:
                        await interaction.response.send_message(simple_msg, ephemeral=True)
                    else:
                        await interaction.followup.send(simple_msg, ephemeral=True)
                else:
                    raise e
        
        self.stop()

    @discord.ui.button(label="❌ Close", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("✅ Tracking copy dialog closed.", ephemeral=True)
        self.stop()

@bot.command(name='summary')
@is_admin()
async def show_summary(ctx):
    """Show order summary with interactive buttons"""
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
    if not sheets_available():
        await ctx.send("❌ Google Sheets is currently unavailable. Please try again later or contact the admin.")
        return

    view = SummaryView(ctx)
    await ctx.send("📊 Select time period for summary:", view=view)
    
    # Wait for button interaction
    await view.wait()
    
    if view.value is None:
        await ctx.send("❌ Operation timed out")
        return
        
    # Get the period from button selection
    period = view.value
    
    try:
        # Get all orders from all sheets
        all_values = get_all_orders()
        
        if not all_values:
            await ctx.send("❌ No data found in any sheet")
            return
            
        now = datetime.now()
        
        # Determine date range based on selected period
        if period == "all":
            start_date = None
            period_name = "All Time"
        elif period == "today":
            start_date = now.strftime('%Y-%m-%d')
            period_name = "Today"
        elif period == "week":
            start_date = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
            period_name = "This Week"
        elif period == "month":
            start_date = now.replace(day=1).strftime('%Y-%m-%d')
            period_name = "This Month"
            
        # Process orders and create summary
        matching_orders = []
        canceled_orders = 0
        
        for row in all_values:
            try:
                if start_date is None or row[0] >= start_date:
                    # Check if order is canceled
                    if len(row) > 8 and row[8].lower() == 'canceled':
                        canceled_orders += 1
                        continue
                    matching_orders.append(row)
            except (ValueError, IndexError) as e:
                continue
                
        if matching_orders:
            # Calculate statistics
            total_revenue = 0
            product_stats = {}
            tracking_uploaded = 0
            
            for order in matching_orders:
                try:
                    price = float(order[3].replace('$', '').strip())
                    quantity = int(order[4])
                    order_revenue = price * quantity
                    total_revenue += order_revenue
                    
                    # Product stats
                    product = order[2]
                    if product not in product_stats:
                        product_stats[product] = 0
                    product_stats[product] += quantity
                    
                    # Check if tracking was uploaded
                    if len(order) > 8 and order[8].strip():  # Assuming tracking is in column 9
                        tracking_uploaded += 1
                    
                except (ValueError, IndexError) as e:
                    continue
            
            # Create clean summary message
            summary = f"📊 **{period_name}'s Summary**\n\n"
            
            # Products Ordered
            summary += f"📦 **Products Ordered:**\n"
            if product_stats:
                for product, qty in product_stats.items():
                    summary += f"• {product}: {qty} units\n"
            else:
                summary += "• No products ordered\n"
            
            # Trackings Uploaded
            summary += f"\n📋 **Trackings Uploaded:** {tracking_uploaded}\n"
            
            # Order Totals
            summary += f"💰 **Order Totals:** {format_currency(total_revenue)}\n"
            
            # Orders Canceled
            summary += f"❌ **Orders Canceled:** {canceled_orders}\n"
            
            # Total Orders
            summary += f"📈 **Total Orders:** {len(matching_orders)}"
            
            await ctx.send(summary)
        else:
            await ctx.send(f"No orders found for {period_name.lower()}")
            
    except Exception as e:
        error_msg = f"Error in summary command: {str(e)}"
        logging.error(error_msg)
        await ctx.send(f"❌ {error_msg}")

@bot.command(name='file')
@is_admin()
async def process_file(ctx):
    """Process messages from a text file with interactive buttons"""
    # Use the global datetime import
    global last_created_sheets
    if not sheets_available():
        await ctx.send("❌ Google Sheets is currently unavailable. Please try again later or contact the admin.")
        return
    
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
        
    if not ctx.message.attachments:
        await ctx.send("❌ Please attach a text file")
        return
        
    attachment = ctx.message.attachments[0]
    if not attachment.filename.endswith('.txt'):
        await ctx.send("❌ Please attach a .txt file")
        return
        
    try:
        # Read file content
        content = await attachment.read()
        content = content.decode('utf-8')
        
        # Split messages by "Successful Checkout" marker
        messages = content.split("Successful Checkout")
        messages = [msg.strip() for msg in messages if msg.strip()]
        
        if not messages:
            await ctx.send("❌ No messages found in file")
            return
        
        # Send initial progress message
        progress_msg = await ctx.send(f"📦 Processing {len(messages)} orders... Please wait.")
        
        # Process messages
        rows_to_add = []
        successful = 0
        failed = []
        
        for i, message in enumerate(messages, 1):
            try:
                # Add "Successful Checkout" back to the message for parsing
                message = "Successful Checkout" + message
                order_data = parse_message(message)
                if not order_data:
                    failed.append(f"Order {i}: Invalid format")
                    continue
                now = datetime.now()
                row = [
                    now.strftime('%Y-%m-%d'),
                    now.strftime('%I:%M:%S %p'),
                    order_data['Product'],
                    order_data['Price'],
                    order_data['Quantity'],
                    order_data['Profile'],
                    order_data['Proxy List'],
                    order_data['Order Number'],
                    order_data['Email']
                ]
                rows_to_add.append(row)
                successful += 1
                # Update progress every 10 orders or at the end
                if i % 10 == 0 or i == len(messages):
                    progress = int((i / len(messages)) * 100)
                    bar_length = 20
                    filled_length = int(bar_length * i // len(messages))
                    bar = '█' * filled_length + '░' * (bar_length - filled_length)
                    await progress_msg.edit(content=f"```\nProgress: [{bar}] {progress}%\nProcessed {i}/{len(messages)} orders...\n" + (f"{successful} valid, {len(failed)} failed" if failed else f"{successful} valid") + "\n```")
            except Exception as e:
                failed.append(f"Order {i}: {str(e)}")
                continue
        
        if rows_to_add:
            try:
                await progress_msg.edit(content=f"```\nAdding {successful} orders to spreadsheet...\nPlease wait.\n```")
                # Create file upload view
                view = FileUploadView(ctx)
                await ctx.send("Choose where to upload the orders:", view=view)
                await view.wait()
                if view.value is None:
                    await ctx.send("❌ Operation cancelled")
                    return
                if view.value == "sheet1":
                    worksheet.append_rows(rows_to_add)
                    sheet_name = "Sheet1"
                elif view.value.startswith("existing:"):
                    sheet_name = view.value.split(":", 1)[1]
                    try:
                        target_sheet = spreadsheet.worksheet(sheet_name)
                        target_sheet.append_rows(rows_to_add)
                    except Exception as e:
                        await ctx.send(f"❌ Error uploading to existing sheet '{sheet_name}': {str(e)}")
                        return
                else:
                    if view.value.startswith("custom:"):
                        sheet_name = view.value.split(":", 1)[1]
                    else:
                        now = datetime.now()
                        date_str = now.strftime('%A %B %d')
                        sheet_name = f"Orders_{date_str}"
                    new_sheet = spreadsheet.add_worksheet(sheet_name, 1000, 9)
                    headers = [
                        'Date', 'Time', 'Product', 
                        'Price', 'Quantity', 'Profile', 'Proxy List', 
                        'Order Number', 'Email'
                    ]
                    new_sheet.append_row(headers)
                    new_sheet.format('A1:I1', {
                        "textFormat": {"bold": True}
                    })
                    new_sheet.append_rows(rows_to_add)
                    last_created_sheet = new_sheet
                    last_created_sheets.insert(0, new_sheet)
                    last_created_sheets = last_created_sheets[:3]
                last_upload['rows'] = rows_to_add
                last_upload['timestamp'] = datetime.now().strftime('%I:%M:%S %p')
                await progress_msg.edit(content=f"✅ Successfully added {successful} orders to {sheet_name}!\n" + (f"\n❌ Failed to process {len(failed)} messages:\n" + "\n".join(failed) if failed else ""))
                response = f"✅ Successfully added {successful} orders to {sheet_name}"
                if failed:
                    response += f"\n❌ Failed to process {len(failed)} messages:\n" + "\n".join(failed)
                response += "\n\nℹ️ You can use !undo to reverse this upload if needed"
                await ctx.send(response)
            except Exception as e:
                await progress_msg.edit(content=f"❌ Error adding to spreadsheet: {str(e)}")
        else:
            await progress_msg.edit(content="❌ No valid orders found in the file")
            await ctx.send("❌ No valid orders found in the file")
    except Exception as e:
        await ctx.send(f"❌ Error processing file: {str(e)}")

@bot.command(name='undo')
@is_admin()
@safe_sheets_operation
async def undo_last_upload(ctx):
    """Undo the last file upload"""
    global last_upload, worksheet
    if not sheets_available():
        await ctx.send("❌ Google Sheets is currently unavailable. Please try again later or contact the admin.")
        return
    
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
    
    if not last_upload['rows'] or not last_upload['timestamp']:
        await ctx.send("❌ No recent uploads to undo")
        return
    
    # Create confirmation view
    view = ConfirmationView()
    await ctx.send(
        f"⚠️ Are you sure you want to undo the last upload from {last_upload['timestamp']}?\n"
        f"This will remove {len(last_upload['rows'])} entries.",
        view=view
    )
    
    # Wait for the user to confirm or cancel
    await view.wait()
    
    if view.value is None:
        await ctx.send("❌ Operation timed out")
    elif view.value:
        try:
            # Find the rows to remove
            all_values = worksheet.get_all_values()
            rows_to_remove = len(last_upload['rows'])
            
            if rows_to_remove > 0:
                # Keep all rows except the last batch
                new_values = all_values[:-rows_to_remove]
                
                # Clear the sheet and rewrite without the last batch
                worksheet.clear()
                if new_values:
                    worksheet.append_rows(new_values)
                
                await ctx.send(f"✅ Successfully removed last {rows_to_remove} entries from {last_upload['timestamp']}")
                
                # Clear the last upload record
                last_upload['rows'] = []
                last_upload['timestamp'] = None
            else:
                await ctx.send("❌ No rows to remove")
                
        except Exception as e:
            await ctx.send(f"❌ Error undoing last upload: {str(e)}")
    else:
        await ctx.send("✅ Operation cancelled")

@bot.command(name='today')
@is_admin()
@safe_sheets_operation
async def get_todays_orders(ctx):
    """Show clean summary of today's orders"""
    if not sheets_available():
        await ctx.send("❌ Google Sheets is currently unavailable. Please try again later or contact the admin.")
        return
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
    try:
        from sheets_utils import get_worksheets
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Statistics
        total_revenue = 0
        total_orders = 0
        canceled_orders = 0
        tracking_uploaded = 0
        
        # Product and quantity tracking
        product_stats = {}
        
        for sheet in get_worksheets():
            values = await safe_get_sheet_values(sheet)
            if not values or len(values) < 2:
                continue
            headers = values[0]
            try:
                date_idx = headers.index('Date')
                product_idx = headers.index('Product')
                price_idx = headers.index('Price')
                quantity_idx = headers.index('Quantity') if 'Quantity' in headers else None
                tracking_idx = None
                if 'Tracking Number' in headers:
                    tracking_idx = headers.index('Tracking Number')
                elif 'Tracking' in headers:
                    tracking_idx = headers.index('Tracking')
            except ValueError:
                continue
                
            for row in values[1:]:
                if len(row) <= max(date_idx, price_idx, product_idx):
                    continue
                if row[date_idx] == today:
                    try:
                        # Check if order is canceled
                        if len(row) > 8 and row[8].lower() == 'canceled':
                            canceled_orders += 1
                            continue
                            
                        price = float(row[price_idx].replace('$', '').strip())
                        quantity = int(row[quantity_idx]) if quantity_idx is not None and len(row) > quantity_idx and row[quantity_idx] else 1
                        product = row[product_idx]
                        
                        total_revenue += price * quantity
                        total_orders += 1
                        
                        # Track product quantities
                        if product not in product_stats:
                            product_stats[product] = 0
                        product_stats[product] += quantity
                        
                        # Check if tracking was uploaded
                        if tracking_idx is not None and len(row) > tracking_idx and row[tracking_idx].strip():
                            tracking_uploaded += 1
                            
                    except Exception:
                        continue
                        
        # Create clean summary
        summary = f"📊 **Today's Summary** ({today})\n\n"
        summary += f"📦 **Products Ordered:**\n"
        if product_stats:
            for product, qty in product_stats.items():
                summary += f"• {product}: {qty} units\n"
        else:
            summary += "• No products ordered\n"
            
        summary += f"\n📋 **Trackings Uploaded:** {tracking_uploaded}\n"
        summary += f"💰 **Order Totals:** ${total_revenue:,.2f}\n"
        summary += f"❌ **Orders Canceled:** {canceled_orders}\n"
        summary += f"📈 **Total Orders:** {total_orders}"
        
        if total_orders == 0:
            await ctx.send("No orders found for today")
        else:
            await ctx.send(summary)
            
    except Exception as e:
        await ctx.send(f"❌ Error getting today's orders: {str(e)}")

@bot.command(name='commands')
@is_authorized_user()
async def show_commands(ctx):
    """Show available commands"""
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
    
    user = ctx.author
    is_owner = user.id == bot.owner_id
    is_admin_user = check_admin_status(user.id)
    
    if is_owner or is_admin_user:
        # Admin/Owner help text
        help_texts = [
            """📋 **Available Commands (Admin/Owner):**

**User Commands:**
`!menu` - Show the main menu with buttons for all operations
`!commands` - Show this help message
`!batch` - Process multiple orders from pasted text

**Available Operations (via Menu Buttons):**
• **Upload Orders** - Upload orders to your Google Sheet
• **Cancel Orders** - Cancel orders using CSV/TXT files
• **Track Orders** - Update tracking numbers using CSV files
• **Mark Received** - Mark orders as received using CSV files
• **Reconcile Charges** - Reconcile credit card charges""",

            """**Admin Commands:**
`!adduser <user_id> <role>` - Add a user with specified role
`!removeuser <user_id>` - Remove a user from the bot
`!listusers` - List all authorized users and their roles
`!summary` - Show period summary with interactive buttons
`!file` - Upload a text file with orders (interactive sheet selection)
`!undo` - Undo the last upload operation
`!today` - Show all orders from today
`!delete [--sheet "Sheet Name"] <order_numbers>` - Delete orders by order number
`!tracking [--sheet "Sheet Name"]` - Update tracking numbers from CSV file""",

            """**More Admin Commands:**
`!export [date] [--columns col1,col2]` - Download orders as CSV file
`!clear` - Clear all orders (requires confirmation)
`!backup` - Create a backup of the current spreadsheet
`!restore` - Restore from a backup CSV file
`!search <query>` - Search for specific orders across all sheets
`!range <start_date> <end_date>` - Show orders between dates (YYYY-MM-DD)
`!profile <profile_name>` - Show detailed analysis for a specific profile
`!refreshsheets` - Refresh the list of available sheets""",

            """**System Commands:**
`!diagnose` - Basic connection diagnostics
`!reconnect` - Reinitialize Google Sheets connection
`!inspect <sheet_name>` - Inspect a sheet's structure
`!reload` - Hot reload the bot without restarting
`!testconnection` - Test Google Sheets connection and provide detailed diagnostics
`!fixconnection` - Attempt to fix connection issues
`!latency` - Check bot performance and websocket status
`!activity [limit]` - View recent user activity (Owner only)

**Performance Monitoring:**
• The bot now includes automatic performance monitoring
• Performance alerts are sent to the owner when issues are detected
• Use `!latency` to check current performance metrics

**Notes:**
• All commands must be used in DM with the bot
• Regular users should use the menu buttons for most operations
• Admin commands require admin or owner permissions
• Sheet names with spaces should be quoted: `"Sheet Name"`"""
        ]
    else:
        # Regular user help text
        help_texts = [
            """📋 **Available Commands (User):**

**Text Commands:**
`!menu` - Show the main menu with buttons for all operations
`!commands` - Show this help message
`!batch` - Process multiple orders from pasted text

**Available Operations (via Menu Buttons):**
• **Upload Orders** - Upload orders to your Google Sheet
• **Cancel Orders** - Cancel orders using CSV/TXT files
• **Track Orders** - Update tracking numbers using CSV files
• **Mark Received** - Mark orders as received using CSV files
• **Reconcile Charges** - Reconcile credit card charges""",

            """**How to Use:**
1. **Use `!menu`** to open the main menu with buttons
2. **Click any button** to start that operation
3. **Follow the prompts** and attach files when requested
4. **Use `!batch`** to process multiple orders from pasted text

**File Formats:**
• **Orders**: Text files with "Successful Checkout" messages
• **Cancellations**: CSV files with order numbers
• **Trackings**: CSV files with Order and Tracking columns

**Notes:**
• All commands must be used in DM with the bot
• Use the menu buttons for most operations (easier than text commands)
• Contact an admin if you need access to additional features"""
        ]
    
    for help_text in help_texts:
        await ctx.send(help_text)

@bot.command(name='bothelp')
@is_authorized_user()
async def show_bot_help(ctx):
    """Show help - same as !commands"""
    await show_commands(ctx)

# Remove the built-in help command and replace it with our role-based version
bot.remove_command('help')

@bot.command(name='mystatus')
async def check_my_status(ctx):
    """Check your own authorization status"""
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
    
    user_id = ctx.author.id
    is_owner = user_id == bot.owner_id
    is_admin_user = check_admin_status(user_id)
    is_authorized_user = is_authorized(user_id)
    profile = get_user_profile(user_id)
    
    status_msg = f"🔍 **Your Authorization Status**\n\n"
    status_msg += f"**User ID:** {user_id}\n"
    status_msg += f"**Bot Owner:** {'✅ Yes' if is_owner else '❌ No'}\n"
    status_msg += f"**Admin:** {'✅ Yes' if is_admin_user else '❌ No'}\n"
    status_msg += f"**Authorized User:** {'✅ Yes' if is_authorized_user else '❌ No'}\n"
    
    if profile:
        status_msg += f"**Role:** {profile.get('role', 'unknown')}\n"
        if profile.get('spreadsheet_id'):
            status_msg += f"**Spreadsheet:** {profile.get('spreadsheet_name', 'Unknown')}\n"
        else:
            status_msg += "**Spreadsheet:** ❌ Not configured\n"
    else:
        status_msg += "**Profile:** ❌ Not registered\n"
    
    status_msg += f"\n**Can use !menu:** {'✅ Yes' if (is_owner or is_admin_user or is_authorized_user) else '❌ No'}"
    
    if not (is_owner or is_admin_user or is_authorized_user):
        status_msg += "\n\n**To get access:** Contact a bot admin to add you as a user."
    
    await ctx.send(status_msg)

@bot.command(name='help')
@is_authorized_user()
async def show_help(ctx):
    """Show role-based help"""
    await show_commands(ctx)

@bot.command(name='menu')
@is_authorized_user()
async def show_menu(ctx):
    """Show the main menu with Upload Orders and other buttons"""
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
    
    # Check if user is authorized
    user = ctx.author
    if not (user.id == bot.owner_id or is_authorized(user.id)):
        await ctx.send("🤖 You are not authorized to use this bot. Please contact the bot owner for access.")
        return
    
    # Check if user needs setup
    if needs_setup(ctx.author.id):
        await ctx.send("🔄 **First-time setup required.** Please wait while I guide you through the process...")
        # Trigger the setup process
        await prompt_for_spreadsheet_setup(ctx)
        return
    
    log_activity(ctx.author.id, "Menu Access", "Accessed main menu")
    welcome_msg = (
        "🤖 **Discord Order Bot**\n\n"
        "Welcome! Use the buttons below to upload orders, cancel, track, or view summaries."
    )
    await ctx.send(welcome_msg, view=WelcomeView(ctx.bot))

async def prompt_for_spreadsheet_setup(ctx):
    """Guides a new user through setting up their Google Sheet."""
    user = ctx.author
    
    # Read the service account email from credentials.json
    try:
        with open('credentials.json', 'r') as f:
            creds_data = json.load(f)
            service_email = creds_data.get('client_email')
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        await ctx.send("❌ **Bot Error:** Could not read service account email from `credentials.json`. Please contact the bot owner.")
        return
        
    setup_message = (
        f"👋 **Welcome, {user.mention}!** To get started, I need access to your Google Sheet.\n\n"
        "**Please follow these steps:**\n"
        "1. **Create a Google Sheet** where you want me to store order data.\n"
        "2. **Click the 'Share' button** in your Google Sheet (top right).\n"
        f"3. **Invite this email address as an `Editor`**: ```{service_email}```\n"
        "4. **Copy the full URL** of your Google Sheet from your browser's address bar.\n"
        "5. **Paste the URL here in this DM and press Enter.**"
    )
    
    await ctx.send(setup_message)

    def check(m):
        # Check if the message is from the user in the same DM channel
        return m.author == user and isinstance(m.channel, discord.DMChannel)

    try:
        # Wait for the user to reply with the URL
        msg = await ctx.bot.wait_for('message', check=check, timeout=300.0)
        url = msg.content.strip()
        
        # Extract spreadsheet ID from URL
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
        if not match:
            await msg.reply("❌ That doesn't look like a valid Google Sheet URL. Please try again.")
            return
        
        spreadsheet_id = match.group(1)
        
        # Test the connection to the sheet
        await msg.reply("⏳ Validating your sheet, please wait...")
        try:
            # Use a temporary gspread client to test this specific sheet
            from google.oauth2.service_account import Credentials
            creds = Credentials.from_service_account_file('credentials.json', scopes=['https://www.googleapis.com/auth/spreadsheets'])
            temp_gc = gspread.authorize(creds)
            
            new_sheet = await asyncio.to_thread(temp_gc.open_by_key, spreadsheet_id)
            spreadsheet_name = new_sheet.title

            # Save the user's spreadsheet info
            set_user_spreadsheet(user.id, spreadsheet_id, spreadsheet_name)
            # Also set it in the sheet_utils cache for immediate use
            set_user_spreadsheet(user.id, new_sheet.id, new_sheet.title)

            await msg.reply(f"✅ **Success!** I've connected to your sheet: **`{spreadsheet_name}`**. You can now use the bot commands.")

        except gspread.exceptions.SpreadsheetNotFound:
            await msg.reply(f"❌ **Failed!** I couldn't find a spreadsheet with that URL. Make sure it was shared correctly with my email address (`{service_email}`).")
        except Exception as e:
            logging.error(f"Error during user sheet setup for {user.id}: {e}")
            await msg.reply("❌ An unexpected error occurred. Please try again or contact the owner.")

    except asyncio.TimeoutError:
        await ctx.send("⏰ Your setup request timed out. Please try `!menu` again to restart.")

# Add this helper to check Sheets availability

def sheets_available():
    return gc is not None and spreadsheet is not None and worksheet is not None and worksheets is not None and len(worksheets) > 0

# In every command or event that requires Sheets, add a check like this at the top:
# if not sheets_available():
#     await ctx.send("❌ Google Sheets is currently unavailable. Please try again later or contact the admin.")
#     return
# For on_message, you can add a similar check before processing uploads/cancels/trackings.

@bot.command(name='delete')
@is_admin()
@safe_sheets_operation
async def delete_orders(ctx, *, args: str = None):
    if not sheets_available():
        await ctx.send("❌ Google Sheets is currently unavailable. Please try again later or contact the admin.")
        return
    # ... existing code ...

@bot.command(name='tracking')
@is_admin()
@safe_sheets_operation
async def update_tracking(ctx):
    if not sheets_available():
        await ctx.send("❌ Google Sheets is currently unavailable. Please try again later or contact the admin.")
        return
    # ... existing code ...

@bot.command(name='export')
@is_admin()
@safe_sheets_operation
async def export_orders(ctx, start_date: str = None, end_date: str = None, *, columns: str = None):
    if not sheets_available():
        await ctx.send("❌ Google Sheets is currently unavailable. Please try again later or contact the admin.")
        return
    # ... existing code ...

@bot.command(name='clear')
@is_admin()
@safe_sheets_operation
async def clear_orders(ctx):
    if not sheets_available():
        await ctx.send("❌ Google Sheets is currently unavailable. Please try again later or contact the admin.")
        return
    # ... existing code ...

@bot.command(name='backup')
@is_admin()
@safe_sheets_operation
async def backup_spreadsheet(ctx, sheet_name: Optional[str] = None):
    if not sheets_available():
        await ctx.send("❌ Google Sheets is currently unavailable. Please try again later or contact the admin.")
        return
    # ... existing code ...

@bot.command(name='restore')
@is_admin()
@safe_sheets_operation
async def restore_spreadsheet(ctx):
    if not sheets_available():
        await ctx.send("❌ Google Sheets is currently unavailable. Please try again later or contact the admin.")
        return
    # ... existing code ...

@bot.command(name='profile')
@is_admin()
@safe_sheets_operation
async def analyze_profile(ctx, *, profile_name: str):
    if not sheets_available():
        await ctx.send("❌ Google Sheets is currently unavailable. Please try again later or contact the admin.")
        return
    # ... existing code ...

@bot.command(name='range')
@is_admin()
@safe_sheets_operation
async def get_order_range(ctx, start_date: str, end_date: str):
    if not sheets_available():
        await ctx.send("❌ Google Sheets is currently unavailable. Please try again later or contact the admin.")
        return
    # ... existing code ...

@bot.command(name='refreshsheets')
@is_admin()
@safe_sheets_operation
async def refresh_sheets_list(ctx):
    """Refresh the list of available Google Sheets worksheets"""
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
    if not sheets_available():
        await ctx.send("❌ Google Sheets is currently unavailable. Please try again later or contact the admin.")
        return
    try:
        from sheets_utils import get_worksheets
        refreshed = get_worksheets()
        if refreshed:
            await ctx.send(f"✅ Refreshed the list of available sheets. Now {len(refreshed)} sheets loaded.")
        else:
            await ctx.send("❌ Failed to refresh sheets or no sheets found.")
    except Exception as e:
        await ctx.send(f"❌ Error refreshing sheets: {str(e)}")

@bot.command(name='diagnose')
@is_admin()
async def diagnose_sheets(ctx):
    """Diagnose Google Sheets connection issues"""
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
    
    await ctx.send("🔍 **Diagnosing Google Sheets Connection...**")
    
    # Check 1: Credentials file
    try:
        import os
        if os.path.exists('credentials.json'):
            await ctx.send("✅ `credentials.json` file found")
        else:
            await ctx.send("❌ `credentials.json` file not found")
            return
    except Exception as e:
        await ctx.send(f"❌ Error checking credentials file: {str(e)}")
        return
    
    # Check 2: Google Sheets connection
    try:
        from google.oauth2.service_account import Credentials
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        await ctx.send("✅ Credentials loaded successfully")
    except Exception as e:
        await ctx.send(f"❌ Error loading credentials: {str(e)}")
        return
    
    # Check 3: Gspread authorization
    try:
        test_gc = gspread.authorize(creds)
        await ctx.send("✅ Gspread authorization successful")
    except Exception as e:
        await ctx.send(f"❌ Error authorizing gspread: {str(e)}")
        return
    
    # Check 4: Spreadsheet access
    try:
        test_spreadsheet = test_gc.open('Successful-Orders')
        await ctx.send("✅ Spreadsheet 'Successful-Orders' found")
    except Exception as e:
        await ctx.send(f"❌ Error accessing spreadsheet 'Successful-Orders': {str(e)}")
        return
    
    # Check 5: Worksheets access
    try:
        test_worksheets = test_spreadsheet.worksheets()
        await ctx.send(f"✅ Found {len(test_worksheets)} worksheets")
    except Exception as e:
        await ctx.send(f"❌ Error accessing worksheets: {str(e)}")
        return
    
    # Check 6: Current connection status
    await ctx.send(f"📊 **Current Connection Status:**")
    await ctx.send(f"• gc: {'✅ Connected' if gc is not None else '❌ None'}")
    await ctx.send(f"• spreadsheet: {'✅ Connected' if spreadsheet is not None else '❌ None'}")
    await ctx.send(f"• worksheet: {'✅ Connected' if worksheet is not None else '❌ None'}")
    await ctx.send(f"• worksheets: {'✅ Connected' if worksheets is not None and len(worksheets) > 0 else '❌ None/Empty'}")
    
    # Check 7: sheets_available() function
    available = sheets_available()
    await ctx.send(f"• sheets_available(): {'✅ True' if available else '❌ False'}")
    
    if not available:
        await ctx.send("\n🔧 **Troubleshooting Steps:**")
        await ctx.send("1. Check if `credentials.json` is valid and has proper permissions")
        await ctx.send("2. Verify the spreadsheet 'Successful-Orders' exists and is shared with the service account")
        await ctx.send("3. Try restarting the bot")
        await ctx.send("4. Check the bot logs for detailed error messages")
    else:
        await ctx.send("\n✅ **Google Sheets connection is working properly!**")

@bot.command(name='reconnect')
@is_admin()
async def reconnect_sheets(ctx):
    """Reinitialize connection to Google Sheets."""
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
    
    global gc, spreadsheet, worksheet, worksheets
    
    await ctx.send("🔄 **Reinitializing Google Sheets Connection...**")
    
    try:
        # Step 1: Load credentials
        from google.oauth2.service_account import Credentials
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        await ctx.send("✅ Credentials loaded")
        
        # Step 2: Authorize
        gc = gspread.authorize(creds)
        await ctx.send("✅ Gspread authorized")
        
        # Step 3: Open spreadsheet and get worksheets
        spreadsheet = gc.open('Successful-Orders')
        worksheet = spreadsheet.sheet1
        worksheets = spreadsheet.worksheets()
        await ctx.send(f"✅ Connected to spreadsheet with {len(worksheets)} worksheets")
        
        # Check headers in each sheet
        headers = [
            'Date', 'Time', 'Product', 'Price', 'Quantity', 
            'Profile', 'Proxy List', 'Order Number', 'Email'
        ]
        
        for sheet in worksheets:
            try:
                existing_headers = sheet.row_values(1)
                if not existing_headers:
                    sheet.append_row(headers)
            except Exception as e:
                await ctx.send(f"⚠️ Warning: Could not check headers for sheet {sheet.title}: {str(e)}")
        
        await ctx.send("✅ **Google Sheets connection reinitialized successfully!**")
        
        # Test the connection
        if sheets_available():
            await ctx.send("✅ Connection test passed - bot is ready to use!")
        else:
            await ctx.send("❌ Connection test failed - please check the logs")
            
    except Exception as e:
        await ctx.send(f"❌ **Error reinitializing connection:** {str(e)}")
        # Reset variables on error
        gc = None
        spreadsheet = None
        worksheet = None
        worksheets = []

@bot.command(name='inspect')
@is_admin()
async def inspect_sheet(ctx, sheet_name: str = "Sheet1"):
    """Inspect a sheet's structure and show sample order numbers"""
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
    
    if not sheets_available():
        await ctx.send("❌ Google Sheets is currently unavailable. Please try again later or contact the admin.")
        return
    
    try:
        # Get the target sheet
        if sheet_name.lower() == "sheet1":
            target_sheet = worksheet
        else:
            target_sheet = spreadsheet.worksheet(sheet_name)
        
        # Get sheet data
        sheet_values = target_sheet.get_all_values()
        if not sheet_values:
            await ctx.send(f"❌ No data found in {sheet_name}")
            return
        
        # Show headers
        headers = sheet_values[0]
        await ctx.send(f"📋 **Sheet: {sheet_name}**\n\n**Headers:** {', '.join(headers)}")
        
        # Find Order Number column
        order_number_idx = None
        for idx, header in enumerate(headers):
            if header.lower() == 'order number':
                order_number_idx = idx
                break
        
        if order_number_idx is None:
            await ctx.send(f"❌ 'Order Number' column not found in {sheet_name}")
            return
        
        await ctx.send(f"✅ Found 'Order Number' column at position {order_number_idx + 1}")
        
        # Show sample order numbers
        sample_orders = []
        for idx, row in enumerate(sheet_values[1:21], start=2):  # First 20 rows
            if len(row) > order_number_idx and row[order_number_idx].strip():
                sample_orders.append(row[order_number_idx].strip())
        
        if sample_orders:
            await ctx.send(f"📝 **Sample Order Numbers (first 20):**\n{', '.join(sample_orders)}")
        else:
            await ctx.send("⚠️ No order numbers found in the first 20 rows")
        
        # Show total count
        total_orders = 0
        for row in sheet_values[1:]:
            if len(row) > order_number_idx and row[order_number_idx].strip():
                total_orders += 1
        
        await ctx.send(f"📊 **Total rows with order numbers:** {total_orders}")
        
    except Exception as e:
        await ctx.send(f"❌ Error inspecting sheet {sheet_name}: {str(e)}")

@bot.command(name='search')
@is_admin()
@safe_sheets_operation
async def search_orders(ctx, *, query: str):
    """Search for specific order numbers in a sheet"""
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
    
    if not sheets_available():
        await ctx.send("❌ Google Sheets is currently unavailable. Please try again later or contact the admin.")
        return
    
    try:
        # Parse order numbers from input
        search_items = [item.strip() for item in query.split(',') if item.strip()]
        if not search_items:
            await ctx.send("❌ No order numbers provided")
            return
        
        # Convert to lowercase for searching
        search_set = set(item.lower() for item in search_items)
        
        await ctx.send(f"🔍 **Searching for {len(search_set)} order numbers:**\n{', '.join(search_items[:10])}{'...' if len(search_items) > 10 else ''}")
        
        # Search in all sheets
        found_orders = []
        not_found_orders = []
        
        for sheet in worksheets:
            try:
                sheet_values = sheet.get_all_values()
                if not sheet_values or len(sheet_values) < 2:
                    continue
                
                headers = sheet_values[0]
                order_number_idx = None
                for idx, header in enumerate(headers):
                    if header.lower() == 'order number':
                        order_number_idx = idx
                        break
                
                if order_number_idx is None:
                    continue
                
                # Search in this sheet
                for row in sheet_values[1:]:
                    if len(row) <= order_number_idx:
                        continue
                    order_number = row[order_number_idx].strip().lower()
                    original_order = row[order_number_idx].strip()
                    
                    if order_number in search_set:
                        found_orders.append({
                            'order': original_order,
                            'sheet': sheet.title,
                            'row': sheet_values.index(row) + 1
                        })
                
            except Exception as e:
                await ctx.send(f"⚠️ Error searching sheet {sheet.title}: {str(e)}")
                continue
        
        # Check which orders were not found
        found_order_numbers = set(item['order'].lower() for item in found_orders)
        not_found_orders = [item for item in search_items if item.lower() not in found_order_numbers]
        
        # Show results
        if found_orders:
            await ctx.send(f"✅ **Found {len(found_orders)} orders:**")
            for item in found_orders[:10]:  # Show first 10
                await ctx.send(f"• {item['order']} in {item['sheet']} (row {item['row']})")
            if len(found_orders) > 10:
                await ctx.send(f"... and {len(found_orders) - 10} more")
        else:
            await ctx.send("❌ **No orders found in any sheet**")
        
        if not_found_orders:
            await ctx.send(f"❌ **Not found ({len(not_found_orders)} orders):**\n{', '.join(not_found_orders[:10])}{'...' if len(not_found_orders) > 10 else ''}")
        
        # Show summary
        await ctx.send(f"📊 **Summary:**\n• Total searched: {len(search_items)}\n• Found: {len(found_orders)}\n• Not found: {len(not_found_orders)}")
        
    except Exception as e:
        await ctx.send(f"❌ Error searching orders: {str(e)}")

@bot.command(name='reload')
@is_admin()
@safe_sheets_operation
async def reload_bot(ctx):
    """Hot reload the bot without restarting the process"""
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
    
    await ctx.send("🔄 **Reloading bot modules...**")
    
    try:
        # Reload key modules
        import importlib
        import sys
        
        # Reload main modules
        modules_to_reload = [
            'sheets_utils',
            'notifications', 
            'dashboard'
        ]
        
        reloaded_count = 0
        for module_name in modules_to_reload:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
                reloaded_count += 1
        
        # Only reinitialize sheets if there are connection issues
        try:
            # Quick test of existing connection
            if gc and spreadsheet:
                # Test with a simple operation
                test_sheet = spreadsheet.sheet1
                test_sheet.title  # This will fail if connection is broken
                sheets_status = "✅ Using existing connection"
            else:
                raise Exception("No existing connection")
        except Exception as e:
            # Only reinitialize if connection is broken
            await ctx.send("⚠️ **Google Sheets connection issue detected, reinitializing...**")
            # Already imported at top
            initialize_sheets()
            sheets_status = "🔄 Reinitialized connection"
        
        # Test basic functionality
        test_msg = "✅ **Reload successful!**\n"
        test_msg += f"• Reloaded {reloaded_count} modules\n"
        test_msg += f"• {sheets_status}\n"
        test_msg += "• Discord connection maintained\n\n"
        test_msg += "**✅ These changes work without restart:**\n"
        test_msg += "• Function logic improvements\n"
        test_msg += "• Error handling updates\n"
        test_msg += "• UI text changes\n"
        test_msg += "• Variable calculations\n"
        test_msg += "• Rate limiting adjustments\n\n"
        test_msg += "**❌ These require full restart:**\n"
        test_msg += "• New commands (@bot.command)\n"
        test_msg += "• New event handlers (@bot.event)\n"
        test_msg += "• New imports at top level\n"
        test_msg += "• Bot configuration changes"
        
        await ctx.send(test_msg)
        
    except Exception as e:
        await ctx.send(f"❌ **Reload failed:** {str(e)}\n\nA full restart may be required for this change.")

class ViewAllOrdersView(View):
    def __init__(self, label, order_numbers, title):
        super().__init__(timeout=600) # Increased timeout to 10 minutes
        self.order_numbers = order_numbers
        self.title = title
        
        button = discord.ui.Button(label=label, style=discord.ButtonStyle.primary)
        button.callback = self.view_all_callback
        self.add_item(button)

    async def view_all_callback(self, interaction: discord.Interaction):
        # Create the text with one order per line
        text = '\n'.join(self.order_numbers)
        
        # Discord message limit is 2000 characters
        max_length = 1900  # Leave some buffer for formatting
        
        if len(text) <= max_length:
            # If it fits in one message, send it
            await interaction.response.send_message(f"**{self.title}:**\n```\n{text}\n```", ephemeral=True)
        else:
            # If it's too long, split into multiple messages
            await interaction.response.send_message(f"**{self.title}** (Part 1):\n```\n{text[:max_length]}\n```", ephemeral=True)
            
            # Send remaining parts
            remaining_text = text[max_length:]
            part_num = 2
            while remaining_text:
                chunk = remaining_text[:max_length]
                await interaction.followup.send(f"**{self.title}** (Part {part_num}):\n```\n{chunk}\n```", ephemeral=True)
                remaining_text = remaining_text[max_length:]
                part_num += 1
        
        self.stop()

@bot.command(name='testconnection')
@is_admin()
async def test_connection(ctx):
    """Test Google Sheets connection and provide detailed diagnostics"""
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
    
    await ctx.send("🔍 **Testing Google Sheets Connection...**")
    
    # Test 1: Check credentials file
    try:
        import os
        if os.path.exists('credentials.json'):
            await ctx.send("✅ `credentials.json` file found")
            
            # Check file size
            file_size = os.path.getsize('credentials.json')
            if file_size < 100:
                await ctx.send("⚠️ `credentials.json` file seems too small. It might be corrupted.")
            else:
                await ctx.send(f"✅ `credentials.json` file size: {file_size} bytes")
        else:
            await ctx.send("❌ `credentials.json` file not found")
            await ctx.send("**Solution:** Download your service account key from Google Cloud Console and save it as `credentials.json`")
            return
    except Exception as e:
        await ctx.send(f"❌ Error checking credentials file: {str(e)}")
        return
    
    # Test 2: Load credentials
    try:
        from google.oauth2.service_account import Credentials
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        await ctx.send("✅ Credentials loaded successfully")
        
        # Check service account email
        service_email = creds.service_account_email
        await ctx.send(f"📧 Service Account Email: `{service_email}`")
        
    except Exception as e:
        await ctx.send(f"❌ Error loading credentials: {str(e)}")
        await ctx.send("**Solution:** Check if your `credentials.json` file is valid and not corrupted")
        return
    
    # Test 3: Test authorization with timeout
    await ctx.send("🔄 Testing authorization (this may take up to 30 seconds)...")
    try:
        import threading
        import queue
        import time
        
        def test_authorization():
            try:
                test_gc = gspread.authorize(creds)
                return test_gc
            except Exception as e:
                return e
        
        result_queue = queue.Queue()
        thread = threading.Thread(target=lambda: result_queue.put(test_authorization()))
        thread.daemon = True
        thread.start()
        
        # Wait up to 30 seconds
        start_time = time.time()
        while thread.is_alive() and (time.time() - start_time) < 30:
            await asyncio.sleep(1)
            await ctx.send(f"⏳ Still authorizing... ({int(time.time() - start_time)}s)")
        
        if thread.is_alive():
            await ctx.send("❌ **Authorization timed out after 30 seconds**")
            await ctx.send("**Possible causes:**")
            await ctx.send("• Slow internet connection")
            await ctx.send("• Google API rate limiting")
            await ctx.send("• Firewall blocking the connection")
            await ctx.send("• DNS resolution issues")
            return
        
        result = result_queue.get()
        if isinstance(result, Exception):
            await ctx.send(f"❌ **Authorization failed:** {str(result)}")
            await ctx.send("**Solutions:**")
            await ctx.send("• Check your internet connection")
            await ctx.send("• Verify the service account has proper permissions")
            await ctx.send("• Try again in a few minutes (rate limiting)")
            return
        else:
            await ctx.send("✅ **Authorization successful!**")
            test_gc = result
    
    except Exception as e:
        await ctx.send(f"❌ **Authorization test failed:** {str(e)}")
        return
    
    # Test 4: Test spreadsheet access
    await ctx.send("🔄 Testing spreadsheet access...")
    try:
        test_spreadsheet = test_gc.open('Successful-Orders')
        await ctx.send("✅ Spreadsheet 'Successful-Orders' found")
        
        # Test worksheet access
        test_worksheets = test_spreadsheet.worksheets()
        await ctx.send(f"✅ Found {len(test_worksheets)} worksheets")
        
        # List worksheet names
        sheet_names = [sheet.title for sheet in test_worksheets]
        await ctx.send(f"📋 Worksheets: {', '.join(sheet_names)}")
        
    except gspread.exceptions.SpreadsheetNotFound:
        await ctx.send("❌ **Spreadsheet 'Successful-Orders' not found**")
        await ctx.send("**Solutions:**")
        await ctx.send("• Create a spreadsheet named 'Successful-Orders'")
        await ctx.send(f"• Share it with the service account: `{service_email}`")
        await ctx.send("• Make sure the service account has 'Editor' permissions")
        return
    except Exception as e:
        await ctx.send(f"❌ **Error accessing spreadsheet:** {str(e)}")
        return
    
    # Test 5: Test current connection status
    await ctx.send("📊 **Current Connection Status:**")
    await ctx.send(f"• gc: {'✅ Connected' if gc is not None else '❌ None'}")
    await ctx.send(f"• spreadsheet: {'✅ Connected' if spreadsheet is not None else '❌ None'}")
    await ctx.send(f"• worksheet: {'✅ Connected' if worksheet is not None else '❌ None'}")
    await ctx.send(f"• worksheets: {'✅ Connected' if worksheets is not None and len(worksheets) > 0 else '❌ None/Empty'}")
    
    # Test 6: sheets_available() function
    available = sheets_available()
    await ctx.send(f"• sheets_available(): {'✅ True' if available else '❌ False'}")
    
    if available:
        await ctx.send("🎉 **All tests passed! Google Sheets connection is working properly.**")
    else:
        await ctx.send("⚠️ **Connection test passed but current connection is not available.**")
        await ctx.send("**Try:** `!reconnect` to reinitialize the connection")
    
    # Test 7: Network connectivity
    await ctx.send("🌐 **Testing network connectivity...**")
    try:
        import urllib.request
        urllib.request.urlopen('https://sheets.googleapis.com', timeout=10)
        await ctx.send("✅ Can reach Google Sheets API")
    except Exception as e:
        await ctx.send(f"❌ **Network connectivity issue:** {str(e)}")
        await ctx.send("**Solutions:**")
        await ctx.send("• Check your internet connection")
        await ctx.send("• Check if you're behind a firewall")
        await ctx.send("• Try using a different network")

@bot.command(name='activity')
@is_owner()
async def view_activity(ctx, limit: int = 20, detailed: str = "false"):
    """View detailed user activity with button interactions (Owner only)"""
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
    
    try:
        # Read activity log file
        activities = []
        try:
            with open('activity_log.json', 'r') as f:
                for line in f:
                    if line.strip():
                        activities.append(json.loads(line))
        except FileNotFoundError:
            await ctx.send("📊 **No activity log found.**\n\nActivity logging will start when users perform actions.")
            return
        
        if not activities:
            await ctx.send("📊 **No activity recorded yet.**\n\nActivity will be logged when users perform actions.")
            return
        
        # Sort by timestamp (newest first)
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Get recent activities
        recent_activities = activities[:limit]
        
        # Check if user wants detailed view
        show_detailed = detailed.lower() in ['true', 'yes', 'detailed', 'full']
        
        if show_detailed:
            # Detailed view with all interaction information
            report = f"🔍 **Detailed Activity Report** (Last {len(recent_activities)} actions)\n\n"
            
            for i, act in enumerate(recent_activities, 1):
                try:
                    user = await safe_discord_call(bot.fetch_user, int(act['user_id']), call_type='user_fetch')
                    user_name = user.display_name if user else f"Unknown User ({act['user_id']})"
                except:
                    user_name = f"Unknown User ({act['user_id']})"
                
                timestamp = datetime.fromisoformat(act['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                
                report += f"**{i}. {user_name}** ({timestamp})\n"
                report += f"   📋 Action: {act['action']}\n"
                
                # Show interaction type and button details
                interaction_type = act.get('interaction_type', 'command')
                if interaction_type == 'button':
                    button_label = act.get('button_label', 'Unknown Button')
                    report += f"   🔘 Button: {button_label}\n"
                elif interaction_type == 'modal':
                    report += f"   📝 Modal: {act.get('details', 'Form submitted')}\n"
                elif interaction_type == 'select':
                    report += f"   📋 Select: {act.get('details', 'Option selected')}\n"
                else:
                    report += f"   💬 Command: {act.get('details', 'Command executed')}\n"
                
                # Show sheet information
                if act.get('sheet_name'):
                    report += f"   📊 Sheet: {act['sheet_name']}\n"
                
                # Show file information
                if act.get('file_name'):
                    report += f"   📁 File: {act['file_name']}\n"
                
                # Show order count
                if act.get('order_count', 0) > 0:
                    report += f"   📦 Orders: {act['order_count']} processed\n"
                
                # Show additional details
                if act.get('details') and not any(key in act.get('details', '') for key in ['Sheet:', 'File:', 'Orders:']):
                    report += f"   ℹ️ Details: {act['details']}\n"
                
                report += "\n"
        else:
            # Standard view (grouped by user)
            user_activities = {}
            for activity in recent_activities:
                user_id = activity['user_id']
                if user_id not in user_activities:
                    user_activities[user_id] = []
                user_activities[user_id].append(activity)
            
            report = f"📊 **Activity Report** (Last {len(recent_activities)} actions)\n\n"
            
            for user_id, user_acts in user_activities.items():
                try:
                    user = await safe_discord_call(bot.fetch_user, int(user_id), call_type='user_fetch')
                    user_name = user.display_name if user else f"Unknown User ({user_id})"
                except:
                    user_name = f"Unknown User ({user_id})"
                
                report += f"👤 **{user_name}**\n"
                for act in user_acts:
                    timestamp = datetime.fromisoformat(act['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                    interaction_type = act.get('interaction_type', 'command')
                    
                    if interaction_type == 'button':
                        button_label = act.get('button_label', 'Unknown Button')
                        report += f"• {timestamp}: 🔘 {button_label} - {act['action']}"
                    else:
                        report += f"• {timestamp}: {act['action']}"
                    
                    if act.get('details'):
                        report += f" - {act['details']}"
                    report += "\n"
                report += "\n"
        
        # Split long reports
        if len(report) > 1900:
            parts = [report[i:i+1900] for i in range(0, len(report), 1900)]
            for i, part in enumerate(parts):
                await ctx.send(f"{part}\n\n*Part {i+1}/{len(parts)}*")
        else:
            await ctx.send(report)
            
        # Add usage hint for detailed view
        if not show_detailed:
            await ctx.send("💡 **Tip:** Use `!activity <limit> detailed` to see detailed button interactions and user actions.")
            
    except Exception as e:
        await ctx.send(f"❌ Error reading activity log: {str(e)}")

@bot.command(name='debugauth')
@is_admin()
async def debug_auth(ctx, user_mention: str = None):
    """Debug authorization issues for a user"""
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
    
    if user_mention:
        # Extract user ID from mention
        user_id = int(user_mention.strip('<@!>'))
    else:
        user_id = ctx.author.id
    
    try:
        user = await safe_discord_call(bot.fetch_user, user_id, call_type='user_fetch')
        user_name = user.display_name
    except:
        user_name = f"Unknown User ({user_id})"
    
    # Check authorization status
    is_owner = user_id == bot.owner_id
    is_admin_user = check_admin_status(user_id)
    is_authorized_user = is_authorized(user_id)
    profile = get_user_profile(user_id)
    
    debug_msg = f"🔍 **Authorization Debug for {user_name}**\n\n"
    debug_msg += f"**User ID:** {user_id}\n"
    debug_msg += f"**Bot Owner:** {'✅ Yes' if is_owner else '❌ No'}\n"
    debug_msg += f"**Admin:** {'✅ Yes' if is_admin_user else '❌ No'}\n"
    debug_msg += f"**Authorized User:** {'✅ Yes' if is_authorized_user else '❌ No'}\n"
    
    if profile:
        debug_msg += f"**Role:** {profile.get('role', 'unknown')}\n"
        debug_msg += f"**Has Spreadsheet:** {'✅ Yes' if profile.get('spreadsheet_id') else '❌ No'}\n"
    else:
        debug_msg += "**Profile:** ❌ Not found\n"
    
    debug_msg += f"\n**Can use !menu:** {'✅ Yes' if (is_owner or is_admin_user or is_authorized_user) else '❌ No'}"
    
    await ctx.send(debug_msg)

@bot.command(name='debugusers')
@is_admin()
async def debug_users_system(ctx):
    """Debug the entire user management system"""
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
    
    # Check file status
    import os
    file_exists = os.path.exists('users.json')
    file_size = os.path.getsize('users.json') if file_exists else 0
    
    # Reload user data from file
    load_user_data()
    all_users = get_all_users_with_details()
    
    debug_msg = "🔍 **User Management System Debug**\n\n"
    debug_msg += f"**File Status:**\n"
    debug_msg += f"• File exists: {'✅ Yes' if file_exists else '❌ No'}\n"
    debug_msg += f"• File size: {file_size} bytes\n"
    debug_msg += f"• Last modified: {time.ctime(os.path.getmtime('users.json')) if file_exists else 'N/A'}\n\n"
    
    debug_msg += f"**Memory Status:**\n"
    debug_msg += f"• Users in memory: {len(all_users)}\n"
    debug_msg += f"• Memory data: {all_users}\n\n"
    
    # Test file operations
    try:
        with open('users.json', 'r') as f:
            file_content = f.read()
            debug_msg += f"**File Content:**\n```json\n{file_content}\n```\n"
    except Exception as e:
        debug_msg += f"**File Read Error:** {str(e)}\n"
    
    await ctx.send(debug_msg)

@bot.command(name='readfile')
@is_owner()
async def read_uploaded_file(ctx, filename: str):
    """Read the contents of an uploaded file (Owner only)"""
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
    
    try:
        # Check if file exists
        if not os.path.exists(filename):
            await ctx.send(f"❌ **File not found:** `{filename}`\n\nAvailable files:\n" + 
                          "\n".join([f"• `{f}`" for f in os.listdir('.') if f.endswith(('.txt', '.csv', '.json'))]))
            return
        
        # Read file contents
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check file size
        file_size = len(content)
        if file_size > 2000:  # Discord message limit is 2000 chars
            # Show first 1000 chars and last 1000 chars
            preview = content[:1000] + "\n\n... [TRUNCATED] ...\n\n" + content[-1000:]
            await ctx.send(f"📄 **File Preview:** `{filename}` ({file_size} characters)\n\n```\n{preview}\n```")
        else:
            await ctx.send(f"📄 **File Contents:** `{filename}` ({file_size} characters)\n\n```\n{content}\n```")
            
    except Exception as e:
        await ctx.send(f"❌ **Error reading file:** {str(e)}")

@bot.command(name='listfiles')
@is_owner()
async def list_uploaded_files(ctx):
    """List all uploaded files (Owner only)"""
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
    
    try:
        # Get all relevant files
        files = []
        for f in os.listdir('.'):
            if f.endswith(('.txt', '.csv', '.json', '.log')):
                size = os.path.getsize(f)
                modified = time.ctime(os.path.getmtime(f))
                files.append((f, size, modified))
        
        if not files:
            await ctx.send("📁 **No uploaded files found**")
            return
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: os.path.getmtime(x[0]), reverse=True)
        
        file_list = "📁 **Uploaded Files:**\n\n"
        for filename, size, modified in files[:20]:  # Show last 20 files
            file_list += f"• `{filename}` ({size} bytes) - {modified}\n"
        
        if len(files) > 20:
            file_list += f"\n... and {len(files) - 20} more files"
        
        await ctx.send(file_list)
        
    except Exception as e:
        await ctx.send(f"❌ **Error listing files:** {str(e)}")

@bot.command(name='testactivity')
@is_admin()
async def test_activity_logging(ctx):
    """Test activity logging by creating sample entries"""
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
    
    # Create some test activity entries with enhanced logging
    test_actions = [
        ("Test Action 1", "Testing enhanced activity logging system", "command", "", "", "", 0),
        ("Test Button Click", "Testing button interaction logging", "button", "Test Button", "Test Sheet", "test.txt", 5),
        ("Test File Upload", "Testing file upload logging", "file_upload", "", "Test Sheet", "orders.txt", 10),
        ("Test Sheet Selection", "Testing sheet selection logging", "select", "Sheet1", "Sheet1", "", 0),
        ("Test Modal Submission", "Testing modal submission logging", "modal", "", "Custom Sheet", "custom.txt", 3)
    ]
    
    for action, details, interaction_type, button_label, sheet_name, file_name, order_count in test_actions:
        log_activity(
            user_id=ctx.author.id,
            action=action,
            details=details,
            interaction_type=interaction_type,
            button_label=button_label,
            sheet_name=sheet_name,
            file_name=file_name,
            order_count=order_count
        )
    
    await ctx.send("✅ **Test activity entries created!**\n\n"
                  f"Created {len(test_actions)} test activity entries.\n"
                  "Now try running `!activity` to see them.")

@bot.command(name='fixusers')
@is_admin()
async def fix_users_file(ctx):
    """Attempt to fix corrupted user data"""
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
    
    try:
        # Backup current file
        import shutil
        shutil.copy('users.json', 'users.json.backup')
        
        # Reload user data
        load_user_data()
        all_users = get_all_users_with_details()
        
        # Save fresh copy
        save_user_data()
        
        await ctx.send(f"✅ **User data fixed!**\n\n"
                      f"• Backup created: `users.json.backup`\n"
                      f"• Users in system: {len(all_users)}\n"
                      f"• Fresh data saved to `users.json`")
        
    except Exception as e:
        await ctx.send(f"❌ **Error fixing user data:** {str(e)}")

@bot.command(name='latency')
@is_admin()
async def check_latency(ctx):
    """Check bot latency and connection status"""
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
    
    try:
        # Get bot latency
        latency = round(bot.latency * 1000, 2)  # Convert to milliseconds
        
        # Get connection status
        status = "🟢 Connected" if bot.is_ready() else "🔴 Disconnected"
        
        # Get shard info
        shard_info = f"Shard {bot.shard_id}/{bot.shard_count}" if bot.shard_id is not None else "No Shard Info"
        
        # Get memory usage
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        # Get CPU usage
        cpu_percent = process.cpu_percent()
        
        # Get rate limiter status
        discord_queue = len(discord_rate_limiter.calls.get('send_message', []))
        sheets_queue = len(sheets_rate_limiter.calls.get('batch_update', []))
        
        # Check websocket status
        ws_status = "🟢 Normal" if not bot.is_ws_ratelimited() else "🔴 Rate Limited"
        
        latency_msg = f"📊 **Bot Performance Status**\n\n"
        latency_msg += f"**Connection:** {status}\n"
        latency_msg += f"**Latency:** {latency}ms\n"
        latency_msg += f"**Shard:** {shard_info}\n"
        latency_msg += f"**Memory:** {memory_mb:.1f} MB\n"
        latency_msg += f"**CPU:** {cpu_percent:.1f}%\n"
        latency_msg += f"**Websocket:** {ws_status}\n"
        latency_msg += f"**Discord Queue:** {discord_queue} pending\n"
        latency_msg += f"**Sheets Queue:** {sheets_queue} pending\n"
        
        # Add warnings for high values
        warnings = []
        if latency > 1000:
            warnings.append(f"⚠️ **HIGH LATENCY WARNING:** {latency}ms (should be < 1000ms)")
        if memory_mb > 500:
            warnings.append(f"⚠️ **HIGH MEMORY USAGE:** {memory_mb:.1f}MB")
        if cpu_percent > 50:
            warnings.append(f"⚠️ **HIGH CPU USAGE:** {cpu_percent:.1f}%")
        if discord_queue > 10:
            warnings.append(f"⚠️ **HIGH DISCORD QUEUE:** {discord_queue} pending")
        if sheets_queue > 5:
            warnings.append(f"⚠️ **HIGH SHEETS QUEUE:** {sheets_queue} pending")
        if bot.is_ws_ratelimited():
            warnings.append("⚠️ **WEBSOCKET RATE LIMITED**")
            
        if warnings:
            latency_msg += f"\n**Warnings:**\n" + "\n".join(warnings)
        else:
            latency_msg += f"\n✅ **All systems operating normally**"
        
        await ctx.send(latency_msg)
        
    except Exception as e:
        await ctx.send(f"❌ **Error checking latency:** {str(e)}")

@bot.command(name='fixconnection')
@is_admin()
async def fix_connection(ctx):
    """Attempt to fix Google Sheets connection issues"""
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please use this command in DM")
        return
    
    await ctx.send("🔧 **Attempting to fix Google Sheets connection...**")
    
    global gc, spreadsheet, worksheet, worksheets
    
    try:
        # Step 1: Clear existing connections
        gc = None
        spreadsheet = None
        worksheet = None
        worksheets = []
        await ctx.send("✅ Cleared existing connections")
        
        # Step 2: Reinitialize with better error handling
        await ctx.send("🔄 Reinitializing connection...")
        
        from google.oauth2.service_account import Credentials
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Load credentials with timeout
        creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        await ctx.send("✅ Credentials loaded")
        
        # Authorize with timeout
        import threading
        import queue
        
        def authorize_with_timeout():
            try:
                return gspread.authorize(creds)
            except Exception as e:
                return e
        
        result_queue = queue.Queue()
        thread = threading.Thread(target=lambda: result_queue.put(authorize_with_timeout()))
        thread.daemon = True
        thread.start()
        thread.join(timeout=30)
        
        if thread.is_alive():
            await ctx.send("❌ **Authorization timed out**")
            await ctx.send("**Try these steps:**")
            await ctx.send("1. Check your internet connection")
            await ctx.send("2. Wait a few minutes and try again")
            await ctx.send("3. Restart the bot")
            return
        
        result = result_queue.get()
        if isinstance(result, Exception):
            await ctx.send(f"❌ **Authorization failed:** {str(result)}")
            return
        
        gc = result
        await ctx.send("✅ Authorization successful")
        
        # Open spreadsheet
        spreadsheet = gc.open('Successful-Orders')
        worksheet = spreadsheet.sheet1
        worksheets = spreadsheet.worksheets()
        await ctx.send(f"✅ Connected to spreadsheet with {len(worksheets)} worksheets")
        
        # Test the connection
        if sheets_available():
            await ctx.send("🎉 **Connection fixed successfully!**")
            await ctx.send("The bot should now be able to use Google Sheets.")
        else:
            await ctx.send("⚠️ **Connection reinitialized but still not available**")
            await ctx.send("Try restarting the bot completely.")
            
    except Exception as e:
        await ctx.send(f"❌ **Failed to fix connection:** {str(e)}")
        await ctx.send("**Manual steps to try:**")
        await ctx.send("1. Restart the bot")
        await ctx.send("2. Check your `credentials.json` file")
        await ctx.send("3. Verify the spreadsheet exists and is shared")
        await ctx.send("4. Check your internet connection")

def clean_tracking(raw):
    """Clean tracking number by removing quotes and other formatting."""
    import re
    # Log the raw tracking before cleaning
    logging.info(f"Cleaning tracking number: '{raw}'")
    match = re.search(r'="?([A-Za-z0-9]+)"?', raw)
    result = match.group(1) if match else raw.replace('="', '').replace('"', '').replace('=', '').strip()
    logging.info(f"Cleaned tracking number: '{result}'")
    return result

if __name__ == "__main__":
    import os
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN not found in environment variables or .env file.")
    else:
        bot.run(token)
