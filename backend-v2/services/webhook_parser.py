"""
Parse webhook text messages from Refract/Discord format
"""
import re
from datetime import datetime
from typing import Dict, Optional


def parse_refract_message(text: str) -> Dict[str, any]:
    """
    Parse Refract webhook message format
    
    Example format:
    Successful Checkout | Best Buy US
    Product
    STARLINK - Mini Kit AC Dual Band Wi-Fi System - White
    Price
    $299.99
    Profile
    Lennar #8-$48-@07
    Proxy Details
    Wealth Resi | http://...
    Order Number
    #BBY01-807102506907
    Email
    woozy_byes28@icloud.com
    """
    data = {}
    
    # Extract Product
    product_match = re.search(r'Product\n(.*?)(?:\n|$)', text, re.IGNORECASE)
    if product_match:
        data['product'] = product_match.group(1).strip()
    
    # Extract Price
    price_match = re.search(r'Price\n\$?([\d,]+\.?\d*)', text, re.IGNORECASE)
    if price_match:
        price_str = price_match.group(1).replace(',', '')
        data['price'] = float(price_str)
        data['total'] = float(price_str)  # Total = Price if not specified
    
    # Extract Profile
    profile_match = re.search(r'Profile\n(.*?)(?:\n|$)', text, re.IGNORECASE)
    if profile_match:
        data['profile'] = profile_match.group(1).strip()
    
    # Extract Proxy Details (multiple possible labels)
    proxy_match = re.search(r'(?:Proxy Details|Proxy List|Proxy)\n(.*?)(?:\n|$)', text, re.IGNORECASE)
    if proxy_match:
        data['proxy_list'] = proxy_match.group(1).strip()
    
    # Extract Order Number (with or without #)
    order_match = re.search(r'Order Number\n#?(.*?)(?:\n|$)', text, re.IGNORECASE)
    if order_match:
        order_num = order_match.group(1).strip()
        # Remove leading # if present
        data['order_number'] = order_num.lstrip('#')
    
    # Extract Email
    email_match = re.search(r'Email\n(.*?)(?:\n|$)', text, re.IGNORECASE)
    if email_match:
        data['email'] = email_match.group(1).strip()
    
    # Extract Quantity (if present)
    quantity_match = re.search(r'Quantity\n(\d+)', text, re.IGNORECASE)
    if quantity_match:
        data['quantity'] = int(quantity_match.group(1))
    else:
        data['quantity'] = 1  # Default to 1
    
    # Extract Total (if present - don't default to price)
    total_match = re.search(r'Total\n\$?([\d,]+\.?\d*)', text, re.IGNORECASE)
    if total_match:
        total_str = total_match.group(1).replace(',', '')
        data['total'] = float(total_str)
    # Note: Don't set default - leave blank if not provided
    
    # Extract Commission (if present)
    commission_match = re.search(r'Commission\n\$?([\d,]+\.?\d*)', text, re.IGNORECASE)
    if commission_match:
        commission_str = commission_match.group(1).replace(',', '')
        data['commission'] = float(commission_str)
    
    # Extract Tracking Number (if present)
    tracking_match = re.search(r'Tracking(?: Number)?\n(.*?)(?:\n|$)', text, re.IGNORECASE)
    if tracking_match:
        data['tracking_number'] = tracking_match.group(1).strip()
    
    # Extract Reference Number (if present)
    reference_match = re.search(r'Reference(?: #)?\n(.*?)(?:\n|$)', text, re.IGNORECASE)
    if reference_match:
        data['reference_number'] = reference_match.group(1).strip()
    
    # Extract Status (if present - leave blank if not specified)
    status_match = re.search(r'Status\n(.*?)(?:\n|$)', text, re.IGNORECASE)
    if status_match:
        status = status_match.group(1).strip().lower()
        # Map to valid status values
        status_map = {
            'pending': 'pending',
            'processing': 'processing',
            'shipped': 'shipped',
            'delivered': 'delivered',
            'cancelled': 'cancelled',
            'verified': 'verified',
            'unverified': 'unverified',
        }
        data['status'] = status_map.get(status, None)
    # Note: Don't auto-detect or set defaults - leave blank if not in message
    
    # Extract Payment Method (if present)
    payment_match = re.search(r'Payment(?: Method)?\n(.*?)(?:\n|$)', text, re.IGNORECASE)
    if payment_match:
        data['payment_method'] = payment_match.group(1).strip()
    
    # Extract Shipping Address (if present)
    shipping_addr_match = re.search(r'Shipping Address\n(.*?)(?:\n|$)', text, re.IGNORECASE)
    if shipping_addr_match:
        data['shipping_address'] = shipping_addr_match.group(1).strip()
    
    # Extract Shipping Method (if present)
    shipping_method_match = re.search(r'Shipping Method\n(.*?)(?:\n|$)', text, re.IGNORECASE)
    if shipping_method_match:
        data['shipping_method'] = shipping_method_match.group(1).strip()
    
    # Add timestamp (current time since message doesn't include it)
    now = datetime.utcnow()
    data['order_date'] = now
    data['order_time'] = now.strftime('%I:%M:%S %p')
    
    return data


def is_text_webhook(content: str) -> bool:
    """
    Detect if webhook content is text format (vs JSON)
    """
    # Check for common text webhook indicators
    indicators = [
        'Successful Checkout',
        'Product\n',
        'Price\n',
        'Order Number\n',
        'Email\n',
    ]
    
    return any(indicator in content for indicator in indicators)


def parse_discord_embed(payload: Dict) -> Dict[str, any]:
    """
    Parse Discord embed format (used by Refract/Discord webhooks)
    
    Example format:
    {
      "embeds": [{
        "author": {"name": "Successful Checkout | Best Buy US"},
        "description": "Product\nNike Shoes\nPrice\n$99.99\n...",
        "fields": [...]
      }]
    }
    """
    # Check if this is a Discord embed payload
    if not isinstance(payload, dict) or 'embeds' not in payload:
        return payload
    
    embeds = payload.get('embeds', [])
    if not embeds or len(embeds) == 0:
        raise ValueError("Discord webhook has no embeds")
    
    embed = embeds[0]  # Take first embed
    
    # Extract text content from embed
    # Discord embeds can have content in multiple places
    text_parts = []
    
    # Author name (e.g., "Successful Checkout | Best Buy US")
    if 'author' in embed and 'name' in embed['author']:
        text_parts.append(embed['author']['name'])
    
    # Title
    if 'title' in embed:
        text_parts.append(embed['title'])
    
    # Description (main content - this is where Refract puts order details)
    if 'description' in embed:
        text_parts.append(embed['description'])
    
    # Fields (alternative location for data)
    if 'fields' in embed:
        for field in embed['fields']:
            if 'name' in field:
                text_parts.append(field['name'])
            if 'value' in field:
                text_parts.append(field['value'])
    
    # Combine all text parts
    full_text = '\n'.join(text_parts)
    
    # Now parse the extracted text as a Refract message
    return parse_refract_message(full_text)


def parse_webhook_content(content: str, content_type: str = None) -> Dict[str, any]:
    """
    Parse webhook content - auto-detect format (JSON or text)
    """
    import json
    
    # Try JSON first
    if content_type and 'json' in content_type.lower():
        try:
            payload = json.loads(content)
            # Check if it's a Discord embed
            if isinstance(payload, dict) and 'embeds' in payload:
                return parse_discord_embed(payload)
            return payload
        except:
            pass
    
    # Check if it looks like JSON
    content_stripped = content.strip()
    if content_stripped.startswith('{') and content_stripped.endswith('}'):
        try:
            payload = json.loads(content)
            # Check if it's a Discord embed
            if isinstance(payload, dict) and 'embeds' in payload:
                return parse_discord_embed(payload)
            return payload
        except:
            pass
    
    # If it's text format, parse it
    if is_text_webhook(content):
        return parse_refract_message(content)
    
    # Last resort: try JSON anyway
    try:
        payload = json.loads(content)
        # Check if it's a Discord embed
        if isinstance(payload, dict) and 'embeds' in payload:
            return parse_discord_embed(payload)
        return payload
    except:
        raise ValueError("Could not parse webhook content as JSON or text format")

