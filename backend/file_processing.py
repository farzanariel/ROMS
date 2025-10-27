import re
import csv
from io import StringIO
from typing import List, Dict, Any, Tuple, Callable, Awaitable
import pandas as pd
from datetime import datetime
import logging

import gspread

from sheet_operations import sheets_manager

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int, str], Awaitable[None]]

async def process_cancel_orders(sheet_url: str, parsed_data: List[Dict[str, str]], worksheet_name: str = None, progress_callback: ProgressCallback = None) -> Tuple[bool, str]:
    """
    Finds and cancels orders in the sheet based on a list of order numbers.
    """
    try:
        df = await sheets_manager.get_all_worksheets_data(sheet_url)
        if df.empty:
            return False, "Could not retrieve any data from the Google Sheet."

        # Find order number and status columns
        order_col = next((col for col in df.columns if 'order' in col.lower()), None)
        status_col = next((col for col in df.columns if 'status' in col.lower()), None)

        if not order_col:
            return False, "Could not find 'Order Number' column in the sheet."
        if not status_col:
            return False, "Could not find 'Status' column in the sheet."

        # Extract order numbers from parsed data
        order_numbers_to_cancel = {item.get('order_number') for item in parsed_data if item.get('order_number')}
        if not order_numbers_to_cancel:
            return False, "No valid order numbers found in the uploaded file."
            
        # Find matching rows
        df['original_index'] = df.index
        to_cancel_df = df[df[order_col].astype(str).isin(order_numbers_to_cancel)]

        if to_cancel_df.empty:
            return True, "Found 0 matching orders to cancel."

        updates = []
        status_col_index = df.columns.get_loc(status_col) + 1 # Gspread is 1-indexed

        total_rows = len(to_cancel_df)
        for i, (index, row) in enumerate(to_cancel_df.iterrows()):
            sheet_row_index = row['original_index'] + 2 # +1 for header, +1 for 0-index vs 1-index
            cell_range = gspread.utils.rowcol_to_a1(sheet_row_index, status_col_index)
            updates.append({
                'range': cell_range,
                'values': [['CANCELLED']],
            })
            if progress_callback:
                await progress_callback(i + 1, total_rows, f"Processing row: {row.to_json()}")

        success, message = await sheets_manager.batch_update_cells(sheet_url, updates, worksheet_name)
        
        if success:
            return True, f"Successfully cancelled {len(updates)} orders."
        else:
            return False, message

    except Exception as e:
        return False, f"An unexpected error occurred during cancellation: {e}"

async def process_tracking_upload(sheet_url: str, parsed_data: List[Dict[str, str]], worksheet_name: str = None, progress_callback: ProgressCallback = None) -> Tuple[bool, str]:
    """
    Finds orders by order number and updates their tracking number.
    """
    try:
        df = await sheets_manager.get_all_worksheets_data(sheet_url)
        if df.empty:
            return False, "Could not retrieve any data from the Google Sheet."

        # Find order number and tracking columns
        order_col = next((col for col in df.columns if 'order' in col.lower()), None)
        tracking_col = next((col for col in df.columns if 'tracking' in col.lower()), None)

        if not order_col:
            return False, "Could not find 'Order Number' column in the sheet."
        if not tracking_col:
            return False, "Could not find 'Tracking Number' column in the sheet."

        # Create a map of order number to tracking number from the file
        tracking_map = {item.get('order_number'): item.get('tracking_number') for item in parsed_data if item.get('order_number') and item.get('tracking_number')}
        if not tracking_map:
            return False, "No valid order number/tracking number pairs found in the file."

        # Find matching rows
        df['original_index'] = df.index
        to_update_df = df[df[order_col].astype(str).isin(tracking_map.keys())]

        if to_update_df.empty:
            return True, "Found 0 matching orders to update."

        updates = []
        tracking_col_index = df.columns.get_loc(tracking_col) + 1

        total_rows = len(to_update_df)
        for i, (index, row) in enumerate(to_update_df.iterrows()):
            order_number = str(row[order_col])
            tracking_number = tracking_map[order_number]
            
            sheet_row_index = row['original_index'] + 2
            cell_range = gspread.utils.rowcol_to_a1(sheet_row_index, tracking_col_index)
            updates.append({
                'range': cell_range,
                'values': [[tracking_number]],
            })
            if progress_callback:
                await progress_callback(i + 1, total_rows, f"Processing row: {row.to_json()}")

        success, message = await sheets_manager.batch_update_cells(sheet_url, updates, worksheet_name)
        
        if success:
            return True, f"Successfully updated tracking for {len(updates)} orders."
        else:
            return False, message

    except Exception as e:
        return False, f"An unexpected error occurred during tracking upload: {e}"

async def process_mark_received(sheet_url: str, parsed_data: List[Dict[str, str]], worksheet_name: str = None, progress_callback: ProgressCallback = None) -> Tuple[bool, str]:
    """
    Finds orders by order number and updates their 'QTY Received' status.
    """
    try:
        df = await sheets_manager.get_all_worksheets_data(sheet_url)
        if df.empty:
            return False, "Could not retrieve any data from the Google Sheet."

        order_col = next((col for col in df.columns if 'order' in col.lower()), None)
        qty_received_col = next((col for col in df.columns if 'received' in col.lower()), None)
        
        if not order_col:
            return False, "Could not find 'Order Number' column in the sheet."
        if not qty_received_col:
            return False, "Could not find 'QTY Received' column in the sheet."

        # Expecting a file with 'order_number' and 'quantity'
        update_map = {item.get('order_number'): item.get('quantity', '1') for item in parsed_data if item.get('order_number')}
        if not update_map:
            return False, "No valid order numbers found in the file."

        df['original_index'] = df.index
        to_update_df = df[df[order_col].astype(str).isin(update_map.keys())]

        if to_update_df.empty:
            return True, "Found 0 matching orders to mark as received."

        updates = []
        qty_received_col_index = df.columns.get_loc(qty_received_col) + 1

        total_rows = len(to_update_df)
        for i, (index, row) in enumerate(to_update_df.iterrows()):
            order_number = str(row[order_col])
            quantity = update_map.get(order_number, '1') # Default to 1 if not specified
            
            sheet_row_index = row['original_index'] + 2
            cell_range = gspread.utils.rowcol_to_a1(sheet_row_index, qty_received_col_index)
            updates.append({
                'range': cell_range,
                'values': [[quantity]],
            })
            if progress_callback:
                await progress_callback(i + 1, total_rows, f"Processing row: {row.to_json()}")

        success, message = await sheets_manager.batch_update_cells(sheet_url, updates, worksheet_name)
        
        if success:
            return True, f"Successfully marked {len(updates)} orders as received."
        else:
            return False, message

    except Exception as e:
        return False, f"An unexpected error occurred while marking orders as received: {e}"

async def process_reconcile_charges(sheet_url: str, parsed_data: List[Dict[str, str]], worksheet_name: str = None, progress_callback: ProgressCallback = None) -> Tuple[bool, str]:
    """
    Reconciles charges by adding Reference # and Posted Date to orders.
    EXACT copy of bot.py reconcile charges logic.
    """
    try:
        # Get the worksheet directly using gspread
        spreadsheet = sheets_manager.gc.open_by_url(sheet_url)
        if worksheet_name:
            target_sheet = spreadsheet.worksheet(worksheet_name)
        else:
            target_sheet = spreadsheet.sheet1
        
        # Get all values from sheet
        values = target_sheet.get_all_values()
        if not values or len(values) < 2:
            return False, "No data found in the sheet."
        
        # Get headers from first row
        headers = values[0]
        lower_headers = [h.lower() for h in headers]
        
        # Helper function to find header column (from bot.py)
        def find_header_column(headers_list, target_key):
            target_lower = target_key.lower()
            STANDARD_HEADERS = {
                'order_number': ['order number', 'order', 'order #', 'order id', 'sku'],
                'email': ['email', 'email address', 'customer email'],
                'reference': ['reference #', 'reference', 'ref #', 'ref', 'reference number'],
                'posted_date': ['posted date', 'posted', 'fulfilled date', 'completion date'],
                'tracking_number': ['tracking number', 'tracking', 'tracking #', 'shipment id'],
            }
            
            possible_names = STANDARD_HEADERS.get(target_key, [target_key])
            for idx, header in enumerate(headers_list):
                if header.lower() in possible_names:
                    return idx
            return None
        
        # Find the Order Number column in the Google Sheet
        order_col_idx = find_header_column(headers, 'order_number')
        if order_col_idx is None:
            return False, "Order Number column not found in sheet."
        
        # Find Email column to add Reference # after it
        email_col_idx = find_header_column(headers, 'email')
        
        # Add Reference # column if it doesn't exist
        ref_col_idx = find_header_column(headers, 'reference')
        if ref_col_idx is None:
            # Add after Email column if exists, otherwise add after Order Number
            insert_idx = email_col_idx + 1 if email_col_idx is not None else order_col_idx + 1
            headers.insert(insert_idx, 'Reference #')
            target_sheet.update('A1', [headers])
            ref_col_idx = insert_idx
            values = target_sheet.get_all_values()  # Refresh values
            lower_headers = [h.lower() for h in headers]  # Refresh lower_headers after adding column
        
        # Add Posted Date column if it doesn't exist
        date_col_idx = find_header_column(headers, 'posted_date')
        if date_col_idx is None:
            # Add after Reference # column
            headers.insert(ref_col_idx + 1, 'Posted Date')
            target_sheet.update('A1', [headers])
            date_col_idx = ref_col_idx + 1
            values = target_sheet.get_all_values()  # Refresh values
            lower_headers = [h.lower() for h in headers]  # Refresh lower_headers after adding column
        
        # Add Tracking Number column if it doesn't exist (for consistency with bot)
        tracking_col_idx = find_header_column(headers, 'tracking_number')
        if tracking_col_idx is None:
            # Add Tracking Number column after Date column
            headers.insert(date_col_idx + 1, 'Tracking Number')
            target_sheet.update('A1', [headers])
            tracking_col_idx = date_col_idx + 1
            values = target_sheet.get_all_values()  # Refresh values
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
        
        for csv_row_idx, csv_row in enumerate(parsed_data):
            # Extract order number from Extended Details
            # Find the Extended Details column case-insensitively
            extended_details = csv_row.get('extended_details', csv_row.get('extended details', ''))
            if not extended_details:
                continue
            
            # Handle multiline Extended Details
            desc = extended_details.strip()
            desc_lines = desc.splitlines()
            
            # Find the line containing Description and extract order number
            order_number = None
            for line in desc_lines:
                if 'Description : ' in line:
                    # Extract text between "Description : " and " Price : "
                    if ' Price : ' in line:
                        parts = line.split('Description : ')[1].split(' Price : ')[0].strip()
                    else:
                        parts = line.split('Description : ')[1].strip()
                    
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
            
            # Get reference and date from CSV
            ref_number = csv_row.get('reference', csv_row.get('Reference', '')).strip("'")
            date_value = csv_row.get('date', csv_row.get('Date', '')).strip()
            
            # Update Reference # (only if not already filled)
            if ref_number:
                existing_ref = values[row_idx - 1][ref_col_idx] if len(values[row_idx - 1]) > ref_col_idx else ""
                if not existing_ref.strip():
                    # Update Reference #
                    ref_cell = chr(ord('A') + ref_col_idx) + str(row_idx)
                    batch_updates.append({'range': ref_cell, 'values': [[ref_number]]})
                    row_was_updated = True
                else:
                    skipped_fields.append('Reference #')
            
            # Update Date (only if not already filled)
            if date_value:
                existing_date = values[row_idx - 1][date_col_idx] if len(values[row_idx - 1]) > date_col_idx else ""
                if not existing_date.strip():
                    date_cell = chr(ord('A') + date_col_idx) + str(row_idx)
                    batch_updates.append({'range': date_cell, 'values': [[date_value]]})
                    row_was_updated = True
                else:
                    skipped_fields.append('Date')
            
            if row_was_updated:
                all_updated.append(order_number)
            if skipped_fields:
                skipped_updates.append((order_number, skipped_fields))
            
            if progress_callback:
                await progress_callback(csv_row_idx + 1, len(parsed_data), f"Reconciling order: {order_number}")
        
        # Apply batch updates
        if batch_updates:
            try:
                target_sheet.batch_update(batch_updates)
                logger.info(f"Successfully updated {len(all_updated)} orders")
            except Exception as e:
                logger.error(f"Batch update failed: {str(e)}")
                return False, f"Error updating sheet: {str(e)}"
        
        # Build summary message
        summary = f"Successfully reconciled {len(all_updated)} orders."
        if not_found_orders:
            summary += f" {len(not_found_orders)} orders not found in sheet."
        if skipped_updates:
            summary += f" {len(skipped_updates)} orders had existing data (skipped)."
        
        return True, summary
    
    except Exception as e:
        logger.exception("Error in process_reconcile_charges")
        return False, f"An unexpected error occurred during reconciliation: {e}"


def parse_csv(text: str, required_columns: List[str] = None) -> List[Dict[str, str]]:
    """
    Parse CSV file content and return list of dictionaries.
    Handles flexible column naming (case-insensitive, strips whitespace).
    """
    try:
        logger.info(f"Starting to parse CSV, text length: {len(text)}")
        
        if not text.strip():
            logger.warning("Empty file content")
            return []
        
        # Parse CSV
        import csv
        from io import StringIO
        csv_reader = csv.DictReader(StringIO(text))
        
        # Normalize headers (lowercase, strip whitespace)
        rows = list(csv_reader)
        if not rows:
            logger.warning("CSV has no data rows")
            return []
        
        # Create normalized data with lowercase keys and stripped values
        normalized_rows = []
        for row in rows:
            normalized_row = {}
            for key, value in row.items():
                # Normalize key: lowercase and strip
                norm_key = key.strip().lower().replace(' ', '_').replace('#', '')
                # Keep the value as-is but strip whitespace
                normalized_row[norm_key] = value.strip() if value else ''
            normalized_rows.append(normalized_row)
        
        logger.info(f"Parsed {len(normalized_rows)} CSV rows")
        if normalized_rows:
            logger.info(f"Sample row keys: {list(normalized_rows[0].keys())}")
        
        # Validate required columns if specified
        if required_columns and normalized_rows:
            first_row_keys = set(normalized_rows[0].keys())
            missing_cols = []
            for req_col in required_columns:
                # Check if any key matches the required column (flexible matching)
                norm_req = req_col.lower().replace(' ', '_')
                found = False
                for key in first_row_keys:
                    if norm_req in key or key in norm_req:
                        found = True
                        break
                if not found:
                    missing_cols.append(req_col)
            
            if missing_cols:
                logger.error(f"CSV missing required columns: {missing_cols}")
                return []
        
        return normalized_rows
        
    except Exception as e:
        logger.error(f"Error parsing CSV: {e}")
        return []

def parse_message(text: str) -> List[Dict[str, str]]:
    """
    Parses a message content and extracts order information.
    Uses the exact same logic as the working Discord bot.
    """
    try:
        logger.info(f"Starting to parse message, text length: {len(text)}")
        
        if not text.strip():
            logger.warning("Empty file content")
            return []
        
        # Log first few lines for debugging
        lines = text.strip().split('\n')
        logger.info(f"Split into {len(lines)} lines")
        logger.info(f"First 3 lines: {lines[:3]}")
        
        # The Discord bot expects files with "Successful Checkout" as separators
        # Let's try to detect if this is the case
        if "Successful Checkout" in text:
            logger.info("Found 'Successful Checkout' separator - processing as Discord bot format")
            messages = text.split("Successful Checkout")
            messages = [msg.strip() for msg in messages if msg.strip()]
            logger.info(f"Split into {len(messages)} messages")
            
            processed_orders = []
            for i, msg in enumerate(messages):
                if not msg.strip():
                    continue
                    
                logger.info(f"Processing message {i+1}: {msg[:100]}...")
                
                # Extract each field using the exact same regex patterns as the Discord bot
                product_match = re.search(r'Product\n(.*?)(?:\n|$)', msg)
                price_match = re.search(r'Price\n\$(.*?)(?:\n|$)', msg)
                profile_match = re.search(r'Profile\n(.*?)(?:\n|$)', msg)
                proxy_match = re.search(r'Proxy List\n(.*?)(?:\n|$)', msg)
                order_match = re.search(r'Order Number\n#?(.*?)(?:\n|$)', msg)  # Made # optional
                email_match = re.search(r'Email\n(.*?)(?:\n|$)', msg)
                quantity_match = re.search(r'Quantity\n(.*?)(?:\n|$)', msg)
                
                logger.info(f"Message {i+1} regex matches:")
                logger.info(f"  Product: {product_match.group(1) if product_match else 'None'}")
                logger.info(f"  Price: {price_match.group(1) if price_match else 'None'}")
                logger.info(f"  Order Number: {order_match.group(1) if order_match else 'None'}")
                
                # Extract data with fallbacks
                order_data = {
                    'Product': product_match.group(1) if product_match else '',
                    'Price': price_match.group(1) if price_match else '',
                    'Profile': profile_match.group(1) if profile_match else '',
                    'Proxy List': proxy_match.group(1) if proxy_match else '',
                    'Order Number': order_match.group(1) if order_match else '',
                    'Email': email_match.group(1) if email_match else '',
                    'Quantity': quantity_match.group(1) if quantity_match else '1'
                }
                
                # Clean up the data
                order_data = {k: v.strip() for k, v in order_data.items()}
                
                # Check if this message has valid order data
                if order_data['Product'] or order_data['Order Number']:
                    processed_orders.append(order_data)
                    logger.info(f"Successfully parsed order from message {i+1}: {order_data}")
                else:
                    logger.warning(f"Message {i+1} did not contain valid order data")
            
            logger.info(f"Successfully parsed {len(processed_orders)} orders from {len(messages)} messages")
            return processed_orders
        else:
            logger.info("No 'Successful Checkout' separator found - trying single message parsing")
            
            # Try to parse as a single message (like the Discord bot does for individual messages)
            # Extract each field using the exact same regex patterns as the Discord bot
            product_match = re.search(r'Product\n(.*?)(?:\n|$)', text)
            price_match = re.search(r'Price\n\$(.*?)(?:\n|$)', text)
            profile_match = re.search(r'Profile\n(.*?)(?:\n|$)', text)
            proxy_match = re.search(r'Proxy List\n(.*?)(?:\n|$)', text)
            order_match = re.search(r'Order Number\n#?(.*?)(?:\n|$)', text)  # Made # optional
            email_match = re.search(r'Email\n(.*?)(?:\n|$)', text)
            quantity_match = re.search(r'Quantity\n(.*?)(?:\n|$)', text)
            
            logger.info(f"Single message regex matches:")
            logger.info(f"  Product: {product_match.group(1) if product_match else 'None'}")
            logger.info(f"  Price: {price_match.group(1) if price_match else 'None'}")
            logger.info(f"  Order Number: {order_match.group(1) if order_match else 'None'}")
            logger.info(f"  Email: {email_match.group(1) if email_match else 'None'}")
            
            # Extract data with fallbacks
            order_data = {
                'Product': product_match.group(1) if product_match else '',
                'Price': price_match.group(1) if price_match else '',
                'Profile': profile_match.group(1) if profile_match else '',
                'Proxy List': proxy_match.group(1) if proxy_match else '',
                'Order Number': order_match.group(1) if order_match else '',
                'Email': email_match.group(1) if email_match else '',
                'Quantity': quantity_match.group(1) if quantity_match else '1'
            }
            
            # Clean up the data
            order_data = {k: v.strip() for k, v in order_data.items()}
            
            # Check if we have valid order data
            if order_data['Product'] or order_data['Order Number']:
                logger.info(f"Successfully parsed single order: {order_data}")
                return [order_data]  # Return as a list with one order
            else:
                logger.warning("No valid order data found in the text")
                logger.warning(f"Parsed data: {order_data}")
                return []
        
    except Exception as e:
        logger.error(f"Error parsing message: {e}")
        logger.error(f"File content preview: {text[:200]}...")
        return []
