import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
import asyncio
import time
from datetime import datetime
import logging
from cache_manager import data_cache, rate_limiter

logger = logging.getLogger(__name__)

class GoogleSheetsManager:
    def __init__(self):
        self.client = None
        self.cached_sheets: Dict[str, Any] = {}
        self.initialize_client()
    
    def initialize_client(self):
        """Initialize Google Sheets client with service account"""
        try:
            import os
            creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
            if os.path.exists(creds_path):
                SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
                creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
                self.client = gspread.authorize(creds)
                self.service_account_email = creds.service_account_email
                logger.info("✅ Google Sheets client initialized successfully")
            else:
                logger.warning("⚠️ credentials.json not found")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Sheets client: {e}")
    
    def get_account_info(self) -> str:
        """Get service account email for display"""
        try:
            if hasattr(self, 'service_account_email') and self.service_account_email:
                # Extract a friendly name from service account email
                email = self.service_account_email
                if '@' in email:
                    name_part = email.split('@')[0]
                    # Convert service account name to friendly format
                    friendly_name = name_part.replace('-', ' ').title()
                    # Make it more friendly
                    if 'discord' in friendly_name.lower():
                        return "Ariel"
                    return friendly_name
                return email
            
            # Try to get it from credentials file directly
            import json
            import os
            creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
            if os.path.exists(creds_path):
                with open(creds_path, 'r') as f:
                    creds_data = json.load(f)
                    email = creds_data.get('client_email', '')
                    if 'discord' in email.lower():
                        return "Ariel"
                    return email.split('@')[0].replace('-', ' ').title()
        except Exception as e:
            logger.warning(f"Could not get account info: {e}")
        
        return "Ariel"  # Default to your name
    
    def get_worksheet(self, sheet_url: str, worksheet_name: str = None):
        """Get worksheet object from URL"""
        if not self.client:
            raise Exception("Google Sheets client not initialized")
        
        try:
            sheet = self.client.open_by_url(sheet_url)
            if worksheet_name:
                worksheet = sheet.worksheet(worksheet_name)
            else:
                worksheet = sheet.get_worksheet(0)
            return worksheet
        except Exception as e:
            logger.error(f"Failed to get worksheet: {e}")
            raise
    
    async def get_all_data(self, sheet_url: str, worksheet_name: str = None) -> pd.DataFrame:
        """Get all data from sheet asynchronously with caching and rate limiting"""
        
        # Check cache first
        cached_data = data_cache.get_cached_data(sheet_url, worksheet_name)
        if cached_data is not None:
            return cached_data
        
        # REMOVED: Rate limiting for instant performance
        
        def _get_data():
            worksheet = self.get_worksheet(sheet_url, worksheet_name)
            
            # Get all values to handle empty headers manually
            try:
                # Try the normal way first
                data = worksheet.get_all_records()
                df = pd.DataFrame(data)
            except Exception as e:
                # If it fails due to empty headers, get raw values and clean them
                logger.warning(f"Failed to get records normally (likely empty headers): {e}")
                all_values = worksheet.get_all_values()
                if not all_values or len(all_values) < 2:
                    return pd.DataFrame()
                
                # Get header row and clean it
                headers = all_values[0]
                # Remove empty headers and their corresponding columns
                valid_indices = [i for i, h in enumerate(headers) if h and h.strip()]
                clean_headers = [headers[i] for i in valid_indices]
                
                # Get data rows with only valid columns
                data_rows = []
                for row in all_values[1:]:
                    clean_row = [row[i] if i < len(row) else '' for i in valid_indices]
                    data_rows.append(clean_row)
                
                # Create DataFrame from cleaned data
                df = pd.DataFrame(data_rows, columns=clean_headers)
            
            if not df.empty:
                df = self.format_dataframe(df)
                # Add worksheet name as a column for multi-sheet support
                df['Worksheet'] = worksheet_name or worksheet.title
            return df
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, _get_data)
        
        # Cache the result
        data_cache.set_cached_data(sheet_url, df, worksheet_name)
        
        return df
    
    async def get_all_worksheets_data(self, sheet_url: str) -> pd.DataFrame:
        """Get data from all worksheets and combine them with caching and parallel processing"""
        
        # Check cache first for combined data
        cached_data = data_cache.get_cached_data(sheet_url, None)
        if cached_data is not None:
            logger.info("🚀 SUPER FAST: Returning cached combined data")
            return cached_data
        
        logger.info("🔄 Cache miss - fetching fresh data with parallel processing...")
        start_time = time.time()
        
        # REMOVED: Rate limiting for instant performance
        
        def _get_worksheet_list():
            if not self.client:
                raise Exception("Google Sheets client not initialized")
            sheet = self.client.open_by_url(sheet_url)
            return sheet.worksheets()
        
        # Get worksheet list
        loop = asyncio.get_event_loop()
        worksheets = await loop.run_in_executor(None, _get_worksheet_list)
        
        # Filter out summary/totals sheets that contain aggregate data, not individual orders
        # These sheets have different structures and shouldn't be included in order queries
        def should_skip_worksheet(ws_title: str) -> bool:
            """Check if worksheet should be skipped based on name patterns"""
            title_lower = ws_title.lower().strip()
            
            # Skip exact matches (case-insensitive) - only skip if the ENTIRE name matches
            skip_exact = ['totals', 'total', 'summary', 'summaries', 'aggregates', 'template', 'archive', 'overview']
            if title_lower in skip_exact:
                return True
            
            # Skip sheets ending with these keywords (e.g., "Oct-Totals", "Month-Summary")
            skip_endings = ['-totals', '-total', '-summary', ' totals', ' total', ' summary', '(totals)', '(total)', '(summary)']
            if any(title_lower.endswith(ending) for ending in skip_endings):
                return True
            
            return False
        
        all_worksheet_names = [ws.title for ws in worksheets]
        worksheets = [ws for ws in worksheets if not should_skip_worksheet(ws.title)]
        skipped = [ws for ws in all_worksheet_names if should_skip_worksheet(ws)]
        
        if skipped:
            logger.info(f"⏩ Skipped {len(skipped)} summary sheets: {', '.join(skipped)}")
        logger.info(f"📋 Processing {len(worksheets)} data worksheets: {', '.join([ws.title for ws in worksheets[:5]])}{'...' if len(worksheets) > 5 else ''}")
        
        # REMOVED: Rate limiting and semaphore for instant performance
        # With 0.4% quota usage, these are unnecessary and just slow things down
        
        async def _process_worksheet_parallel(worksheet):
            """Process a single worksheet without rate limiting for instant performance"""
            try:
                # Check individual worksheet cache first
                worksheet_data = data_cache.get_cached_data(sheet_url, worksheet.title)
                
                if worksheet_data is not None:
                    logger.info(f"✅ Cache hit for worksheet: {worksheet.title}")
                    return worksheet_data
                
                def _get_worksheet_data():
                    try:
                        logger.info(f"📡 Fetching data for worksheet: {worksheet.title}")
                        
                        # Try the normal way first
                        try:
                            data = worksheet.get_all_records()
                            if data:  # Only process non-empty worksheets
                                df = pd.DataFrame(data)
                        except Exception as header_error:
                            # If it fails due to empty headers, get raw values and clean them
                            logger.warning(f"Failed to get records normally for {worksheet.title} (likely empty headers): {header_error}")
                            all_values = worksheet.get_all_values()
                            if not all_values or len(all_values) < 2:
                                return pd.DataFrame()
                            
                            # Get header row and clean it
                            headers = all_values[0]
                            # Remove empty headers and their corresponding columns
                            valid_indices = [i for i, h in enumerate(headers) if h and h.strip()]
                            clean_headers = [headers[i] for i in valid_indices]
                            
                            # Get data rows with only valid columns
                            data_rows = []
                            for row in all_values[1:]:
                                clean_row = [row[i] if i < len(row) else '' for i in valid_indices]
                                data_rows.append(clean_row)
                            
                            # Create DataFrame from cleaned data
                            df = pd.DataFrame(data_rows, columns=clean_headers)
                        
                        if not df.empty:
                            df = self.format_dataframe(df)
                            # Add worksheet info
                            df['Worksheet'] = worksheet.title
                            df['Product_Run'] = worksheet.title
                            logger.info(f"✅ Processed {len(df)} rows from {worksheet.title}")
                            return df
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to load worksheet {worksheet.title}: {e}")
                    return pd.DataFrame()
                
                worksheet_data = await loop.run_in_executor(None, _get_worksheet_data)
                
                # Cache individual worksheet data
                if not worksheet_data.empty:
                    data_cache.set_cached_data(sheet_url, worksheet_data, worksheet.title)
                
                return worksheet_data
                
            except Exception as e:
                logger.warning(f"❌ Failed to process worksheet {worksheet.title}: {e}")
                return pd.DataFrame()
        
        # PARALLEL PROCESSING: Process all worksheets concurrently
        logger.info("🚀 Starting parallel worksheet processing...")
        parallel_start = time.time()
        
        worksheet_tasks = [_process_worksheet_parallel(ws) for ws in worksheets]
        worksheet_results = await asyncio.gather(*worksheet_tasks, return_exceptions=True)
        
        parallel_time = time.time() - parallel_start
        logger.info(f"⚡ Parallel processing completed in {parallel_time:.2f}s")
        
        # Collect valid data
        all_data = []
        for i, result in enumerate(worksheet_results):
            if isinstance(result, Exception):
                logger.warning(f"⚠️ Worksheet {worksheets[i].title} failed: {result}")
                continue
            if not result.empty:
                all_data.append(result)
        
        if all_data:
            # Combine all worksheets
            combine_start = time.time()
            combined_df = pd.concat(all_data, ignore_index=True, sort=False)
            combine_time = time.time() - combine_start
            
            total_time = time.time() - start_time
            logger.info(f"📊 Combined {len(all_data)} worksheets with {len(combined_df)} total rows")
            logger.info(f"⏱️ Total processing time: {total_time:.2f}s (fetch: {parallel_time:.2f}s, combine: {combine_time:.2f}s)")
            
            # Cache the combined result
            data_cache.set_cached_data(sheet_url, combined_df, None)
            
            return combined_df
        else:
            total_time = time.time() - start_time
            logger.warning(f"❌ No data found in any worksheet (took {total_time:.2f}s)")
            empty_df = pd.DataFrame()
            # Cache empty result too (but for shorter time)
            data_cache.set_cached_data(sheet_url, empty_df, None)
            return empty_df
    
    def get_worksheet_list(self, sheet_url: str) -> List[str]:
        """Get list of all worksheet names"""
        try:
            if not self.client:
                raise Exception("Google Sheets client not initialized")
            
            sheet = self.client.open_by_url(sheet_url)
            worksheets = sheet.worksheets()
            return [ws.title for ws in worksheets]
        except Exception as e:
            logger.error(f"Failed to get worksheet list: {e}")
            return []
    
    async def update_cell(self, sheet_url: str, row: int, col: int, value: str, worksheet_name: str = None) -> bool:
        """Update a single cell"""
        def _update_cell():
            worksheet = self.get_worksheet(sheet_url, worksheet_name)
            
            # Format value according to column type
            formatted_value = self.format_cell_value(value, col)
            
            # Update the cell
            worksheet.update_cell(row, col, formatted_value)
            
            # Update the Modified timestamp (column 19)
            current_time = datetime.now().strftime("%m-%d-%Y, %H:%M:%S")
            worksheet.update_cell(row, 19, current_time)  # Modified column
            
            return True
        
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _update_cell)
        except Exception as e:
            logger.error(f"Failed to update cell: {e}")
            return False
    
    async def update_row(self, sheet_url: str, row: int, data: Dict[str, Any], worksheet_name: str = None) -> bool:
        """Update multiple cells in a row"""
        def _update_row():
            worksheet = self.get_worksheet(sheet_url, worksheet_name)
            
            # Get column mapping
            headers = worksheet.row_values(1)
            
            # Prepare updates
            updates = []
            for column_name, value in data.items():
                if column_name in headers:
                    col_index = headers.index(column_name) + 1
                    formatted_value = self.format_cell_value(value, col_index)
                    updates.append({
                        'range': f'{gspread.utils.rowcol_to_a1(row, col_index)}',
                        'values': [[formatted_value]]
                    })
            
            # Add Modified timestamp
            if 'Modified' in headers:
                modified_col = headers.index('Modified') + 1
                current_time = datetime.now().strftime("%m-%d-%Y, %H:%M:%S")
                updates.append({
                    'range': f'{gspread.utils.rowcol_to_a1(row, modified_col)}',
                    'values': [[current_time]]
                })
            
            # Batch update
            if updates:
                worksheet.batch_update(updates)
            
            return True
        
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _update_row)
        except Exception as e:
            logger.error(f"Failed to update row: {e}")
            return False
    
    async def append_row(self, sheet_url: str, data: Dict[str, Any], worksheet_name: str = None) -> bool:
        """Append a new row to the sheet"""
        def _append_row():
            worksheet = self.get_worksheet(sheet_url, worksheet_name)
            
            # Get headers
            headers = worksheet.row_values(1)
            
            # Prepare row data
            row_data = []
            for header in headers:
                if header in data:
                    col_index = headers.index(header) + 1
                    formatted_value = self.format_cell_value(data[header], col_index)
                    row_data.append(formatted_value)
                else:
                    row_data.append('')
            
            # Add timestamps
            current_time = datetime.now().strftime("%m-%d-%Y, %H:%M:%S")
            if 'Created' in headers:
                created_index = headers.index('Created')
                row_data[created_index] = current_time
            if 'Modified' in headers:
                modified_index = headers.index('Modified')
                row_data[modified_index] = current_time
            
            worksheet.append_row(row_data)
            return True
        
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _append_row)
        except Exception as e:
            logger.error(f"Failed to append row: {e}")
            return False
    
    async def append_rows(self, sheet_url: str, data: List[Dict[str, Any]], worksheet_name: str = None) -> (bool, str):
        """Append multiple rows to a worksheet."""
        if not self.client:
            return False, "Google Sheets client not initialized."
        try:
            sheet = self.client.open_by_url(sheet_url)
            
            # List available worksheets for debugging
            available_worksheets = [ws.title for ws in sheet.worksheets()]
            logger.info(f"Available worksheets: {available_worksheets}")
            
            if worksheet_name:
                try:
                    worksheet = sheet.worksheet(worksheet_name)
                    logger.info(f"Found worksheet: {worksheet.title}")
                except gspread.exceptions.WorksheetNotFound:
                    logger.warning(f"Worksheet '{worksheet_name}' not found. Available: {available_worksheets}")
                    # Try to create the worksheet if it doesn't exist
                    try:
                        worksheet = sheet.add_worksheet(title=worksheet_name, rows=1000, cols=26)
                        logger.info(f"Created new worksheet: {worksheet_name}")
                    except Exception as create_error:
                        logger.error(f"Failed to create worksheet '{worksheet_name}': {create_error}")
                        return False, f"Worksheet '{worksheet_name}' not found and could not be created. Available worksheets: {', '.join(available_worksheets)}"
            else:
                worksheet = sheet.get_worksheet(0) # Default to first sheet
                logger.info(f"Using default worksheet: {worksheet.title}")

            # Get header to ensure order of values is correct
            header = worksheet.row_values(1)
            logger.info(f"Worksheet header: {header}")
            
            rows_to_append = []
            for item in data:
                row = [item.get(h, '') for h in header]
                rows_to_append.append(row)

            if not rows_to_append:
                return False, "No data to append."

            worksheet.append_rows(rows_to_append, value_input_option='USER_ENTERED')
            
            logger.info(f"Appended {len(rows_to_append)} rows to worksheet '{worksheet.title}'")
            return True, f"Successfully appended {len(rows_to_append)} rows."
        except Exception as e:
            logger.error(f"Error appending rows to sheet: {e}")
            return False, f"Error appending rows: {e}"

    async def append_rows_discord_format(self, sheet_url: str, rows_to_add: List[List], worksheet_name: str = None, progress_callback = None) -> (bool, str):
        """Append rows in Discord bot format (9 columns in specific order)."""
        if not self.client:
            return False, "Google Sheets client not initialized."
        try:
            sheet = self.client.open_by_url(sheet_url)
            
            # List available worksheets for debugging
            available_worksheets = [ws.title for ws in sheet.worksheets()]
            logger.info(f"Available worksheets: {available_worksheets}")
            
            if worksheet_name:
                try:
                    worksheet = sheet.worksheet(worksheet_name)
                    logger.info(f"Found worksheet: {worksheet.title}")
                except gspread.exceptions.WorksheetNotFound:
                    logger.warning(f"Worksheet '{worksheet_name}' not found. Available: {available_worksheets}")
                    # Try to create the worksheet if it doesn't exist
                    try:
                        worksheet = sheet.add_worksheet(title=worksheet_name, rows=1000, cols=26)
                        logger.info(f"Created new worksheet: {worksheet_name}")
                        
                        # Add headers for new worksheet (Discord bot format)
                        headers = [
                            'Date', 'Time', 'Product', 'Price', 'Total', 'Commission', 'Quantity', 
                            'Profile', 'Proxy List', 'Order Number', 'Email', 'Reference #', 
                            'Posted Date', 'Tracking Number', 'Status', 'QTY Received', 
                            'Order ID', 'Created', 'Modified'
                        ]
                        worksheet.append_row(headers)
                        worksheet.format('A1:S1', {"textFormat": {"bold": True}})
                        logger.info(f"Added headers to new worksheet: {worksheet_name}")
                    except Exception as create_error:
                        logger.error(f"Failed to create worksheet '{worksheet_name}': {create_error}")
                        return False, f"Worksheet '{worksheet_name}' not found and could not be created. Available worksheets: {', '.join(available_worksheets)}"
            else:
                worksheet = sheet.get_worksheet(0) # Default to first sheet
                logger.info(f"Using default worksheet: {worksheet.title}")

            # Get header to check if we need to map to existing format
            header = worksheet.row_values(1)
            logger.info(f"Worksheet header: {header}")
            
            # Check if this is a new sheet with Discord bot headers or existing sheet
            if len(header) >= 19 and 'Date' in header and 'Product' in header:
                # This looks like a Discord bot format sheet, map to correct positions
                logger.info("Detected Discord bot format sheet, mapping to correct positions")
                mapped_rows = []
                
                if progress_callback:
                    await progress_callback(0, len(rows_to_add), "Mapping data to sheet format...")
                
                for i, row in enumerate(rows_to_add):
                    # Create row with 19 columns, mapping data to correct positions
                    # Original row: [Date, Time, Product, Price, Quantity, Profile, Proxy List, Order Number, Email]
                    mapped_row = [''] * 19
                    mapped_row[0] = row[0]   # Date (position 0)
                    mapped_row[1] = row[1]   # Time (position 1) 
                    mapped_row[2] = row[2]   # Product (position 2)
                    mapped_row[3] = row[3]   # Price (position 3)
                    # mapped_row[4] = Total (empty for now)
                    # mapped_row[5] = Commission (empty for now)
                    mapped_row[6] = row[4]   # Quantity (was at index 4, now at position 6)
                    mapped_row[7] = row[5]   # Profile (was at index 5, now at position 7)
                    mapped_row[8] = row[6]   # Proxy List (was at index 6, now at position 8)
                    mapped_row[9] = row[7]   # Order Number (was at index 7, now at position 9)
                    mapped_row[10] = row[8]  # Email (was at index 8, now at position 10)
                    # Other columns will remain empty until filled by other features
                    mapped_rows.append(mapped_row)
                    
                    # Update progress less frequently for speed (every 25 rows)
                    if progress_callback and (i + 1) % 25 == 0:
                        await progress_callback(i + 1, len(rows_to_add), f"Mapping row {i + 1}/{len(rows_to_add)}...")
                
                if progress_callback:
                    await progress_callback(len(rows_to_add), len(rows_to_add), "Uploading to Google Sheets...")
                
                worksheet.append_rows(mapped_rows, value_input_option='USER_ENTERED')
                logger.info(f"Appended {len(mapped_rows)} mapped rows to Discord bot format worksheet '{worksheet.title}'")
            else:
                # This is an existing sheet with different headers, append as-is
                logger.info("Detected existing sheet format, appending rows as-is")
                
                if progress_callback:
                    await progress_callback(len(rows_to_add), len(rows_to_add), "Uploading to Google Sheets...")
                
                worksheet.append_rows(rows_to_add, value_input_option='USER_ENTERED')
                logger.info(f"Appended {len(rows_to_add)} rows to existing worksheet '{worksheet.title}'")
            
            return True, f"Successfully appended {len(rows_to_add)} rows."
        except Exception as e:
            logger.error(f"Error appending rows to sheet: {e}")
            return False, f"Error appending rows: {e}"

    async def batch_update_cells(self, sheet_url: str, updates: List[Dict[str, Any]], worksheet_name: str = None) -> Tuple[bool, str]:
        """
        Batch update cells in a worksheet.
        'updates' should be a list of dicts, e.g., [{'range': 'A1', 'values': [['New Value']]}]
        """
        if not self.client:
            return False, "Google Sheets client not initialized."
        try:
            sheet = self.client.open_by_url(sheet_url)
            if worksheet_name:
                worksheet = sheet.worksheet(worksheet_name)
            else:
                worksheet = sheet.get_worksheet(0)
            
            if not updates:
                return False, "No updates to perform."

            worksheet.batch_update(updates)
            
            logger.info(f"Batch updated {len(updates)} ranges in worksheet '{worksheet.title}'")
            return True, f"Successfully updated {len(updates)} cells."
        except gspread.exceptions.WorksheetNotFound:
            return False, f"Worksheet '{worksheet_name}' not found."
        except Exception as e:
            logger.error(f"Error in batch update: {e}")
            return False, f"Error in batch update: {e}"

    def format_cell_value(self, value: str, col_index: int) -> str:
        """Format cell value according to column type (based on 19-column spec)"""
        # Column mapping from your PROJECT_CONTEXT.md
        currency_columns = [4, 5, 6]  # Price, Total, Commission (1-indexed)
        integer_columns = [7, 16]     # Quantity, QTY Received
        date_columns = [1, 13]        # Date, Posted Date
        
        try:
            if col_index in currency_columns:
                # Format as currency: $X,XXX.XX
                clean_value = str(value).replace('$', '').replace(',', '')
                if clean_value and clean_value != '':
                    num_value = float(clean_value)
                    return f"${num_value:,.2f}"
                return "$0.00"
            
            elif col_index in integer_columns:
                # Format as integer
                return str(int(float(value))) if value else "0"
            
            elif col_index in date_columns:
                # Keep date formatting as-is for now
                return str(value)
            
            else:
                # Return as string
                return str(value)
                
        except (ValueError, TypeError):
            return str(value)
    
    def format_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Format DataFrame according to user's actual sheet structure"""
        
        # Log the actual columns we receive
        logger.info(f"Original columns: {list(df.columns)}")
        
        # Don't add missing columns - work with what we have
        # Just format the columns that exist
        
        # Format currency columns based on actual column names
        currency_columns = ['Price', 'Total', 'Commission', 'Spend', 'Charged', 'Paid Out', 'PnL/BE']
        for col in currency_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).apply(self.format_currency)
        
        # Format integer columns based on actual column names  
        integer_columns = ['Quantity', 'QTY Received', 'Orders', 'Shipped', 'Scanned', 'Missing', 'QTY Ordered']
        for col in integer_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        # Format date columns with flexible parsing
        # Pandas can handle multiple formats: 'YYYY-MM-DD', 'M/D/YYYY', 'Sun, 05 Oct 2025 17:28:02 -0600', etc.
        date_columns = ['Date', 'Posted Date']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    
    def format_currency(self, value: str) -> str:
        """Format currency according to specification: $X,XXX.XX"""
        try:
            clean_value = str(value).replace('$', '').replace(',', '')
            if clean_value and clean_value != '':
                num_value = float(clean_value)
                return f"${num_value:,.2f}"
            return "$0.00"
        except:
            return "$0.00"
    
    async def get_worksheets_info(self, sheet_url: str) -> List[Dict[str, Any]]:
        """Get detailed information about all worksheets"""
        try:
            if not self.client:
                raise Exception("Google Sheets client not initialized")
            
            # REMOVED: Rate limiting for instant performance
            
            def _get_worksheets_info():
                sheet = self.client.open_by_url(sheet_url)
                worksheets = sheet.worksheets()
                
                worksheets_info = []
                for ws in worksheets:
                    try:
                        # Get basic worksheet info
                        row_count = ws.row_count
                        col_count = ws.col_count
                        
                        # Try to get data count (rows with data)
                        try:
                            data = ws.get_all_records()
                            data_rows = len([row for row in data if any(str(v).strip() for v in row.values())])
                        except:
                            data_rows = 0
                        
                        # Get last modified date if possible
                        try:
                            # Try to get the last modified date from metadata
                            updated = ws.updated
                        except:
                            updated = None
                        
                        worksheet_info = {
                            "id": ws.id,
                            "title": ws.title,
                            "index": ws.index,
                            "row_count": row_count,
                            "col_count": col_count,
                            "data_rows": data_rows,
                            "url": ws.url,
                            "updated": updated.isoformat() if updated else None,
                            "sheet_type": "orders" if any(keyword in ws.title.lower() 
                                                        for keyword in ['order', 'sale', 'purchase']) else "data"
                        }
                        
                        worksheets_info.append(worksheet_info)
                        
                    except Exception as e:
                        logger.warning(f"Error getting info for worksheet {ws.title}: {e}")
                        # Add basic info even if detailed info fails
                        worksheets_info.append({
                            "id": getattr(ws, 'id', None),
                            "title": ws.title,
                            "index": getattr(ws, 'index', 0),
                            "row_count": 0,
                            "col_count": 0,
                            "data_rows": 0,
                            "url": getattr(ws, 'url', ''),
                            "updated": None,
                            "sheet_type": "unknown",
                            "error": str(e)
                        })
                
                return worksheets_info
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            worksheets_info = await loop.run_in_executor(None, _get_worksheets_info)
            
            logger.info(f"Retrieved info for {len(worksheets_info)} worksheets")
            return worksheets_info
            
        except Exception as e:
            logger.error(f"Failed to get worksheets info: {e}")
            raise

# Global instance
sheets_manager = GoogleSheetsManager()
