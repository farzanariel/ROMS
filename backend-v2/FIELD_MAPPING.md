# Refract Webhook → Database Field Mapping

## 📊 Complete Field Mapping

This shows exactly how your Refract webhook message maps to database columns.

### Your Example Message:
```
Successful Checkout | Best Buy US
Product
STARLINK - Mini Kit AC Dual Band Wi-Fi System - White
Price
$299.99
Profile
Lennar #8-$48-@07
Proxy Details
Wealth Resi | http://resi-edge-pool.wealthproxies.com:5959/
Order Number
#BBY01-807102506907
Email
woozy_byes28@icloud.com
```

### Database Result:

| Database Column | Value | How It's Set |
|---|---|---|
| ✅ **order_number** | `BBY01-807102506907` | Parsed from "Order Number\n#BBY01..." (# removed) |
| ✅ **product** | `STARLINK - Mini Kit AC Dual Band...` | Parsed from "Product\n..." |
| ✅ **price** | `299.99` | Parsed from "Price\n$299.99" ($ removed) |
| ✅ **total** | `299.99` | Same as price (if Total not specified) |
| ✅ **quantity** | `1` | Default (unless "Quantity\n2" in message) |
| ✅ **email** | `woozy_byes28@icloud.com` | Parsed from "Email\n..." |
| ✅ **profile** | `Lennar #8-$48-@07` | Parsed from "Profile\n..." |
| ✅ **proxy_list** | `Wealth Resi \| http://resi-edge...` | Parsed from "Proxy Details\n..." |
| ✅ **status** | `verified` | Auto-detected from "Successful Checkout" |
| ✅ **order_date** | `2024-10-27 17:56:00` | Current timestamp when received |
| ✅ **order_time** | `05:56:00 PM` | Current time when received |
| ✅ **source** | `webhook` | Automatically set |
| ✅ **created_at** | `2024-10-27 17:56:00` | Auto-generated |
| ✅ **updated_at** | `2024-10-27 17:56:00` | Auto-generated |
| ⚪ **commission** | `NULL` | Optional - include "Commission\n$50" in message |
| ⚪ **customer_name** | `NULL` | Optional - include "Name\nJohn Doe" in message |
| ⚪ **reference_number** | `NULL` | Optional - include "Reference #\nREF123" in message |
| ⚪ **tracking_number** | `NULL` | Optional - include "Tracking Number\n1Z..." in message |
| ⚪ **posted_date** | `NULL` | Optional - updated later when posted |
| ⚪ **shipped_date** | `NULL` | Optional - updated when shipped |
| ⚪ **delivered_date** | `NULL` | Optional - updated when delivered |
| ⚪ **payment_method** | `NULL` | Optional - include "Payment Method\nCredit Card" |
| ⚪ **shipping_address** | `NULL` | Optional - include "Shipping Address\n123 Main St" |
| ⚪ **shipping_method** | `NULL` | Optional - include "Shipping Method\nExpress" |
| ⚪ **notes** | `NULL` | Optional - include "Notes\nSpecial instructions" |
| ⚪ **qty_received** | `0` | Default - updated when items received |
| ⚪ **worksheet_name** | `NULL` | Not used for webhooks (only for Sheets) |

---

## 🎯 Your Desired Headers (from request)

You asked for these columns:
```
Date, Time, Product, Price, Total, Commission, Quantity, Profile, Proxy List, 
Order Number, Email, Reference #, Posted Date, Tracking Number, Status, Notes, 
Payment Method, Shipping Address, Shipping Method, QTY Received, Order ID, 
Created, Modified
```

### ✅ Mapping Status:

| Your Header | Database Column | Status |
|---|---|---|
| Date | order_date | ✅ Populated |
| Time | order_time | ✅ Populated |
| Product | product | ✅ Populated |
| Price | price | ✅ Populated |
| Total | total | ✅ Populated |
| Commission | commission | ⚠️ NULL (add to message) |
| Quantity | quantity | ✅ Default 1 |
| Profile | profile | ✅ Populated |
| Proxy List | proxy_list | ✅ Populated |
| Order Number | order_number | ✅ Populated |
| Email | email | ✅ Populated |
| Reference # | reference_number | ⚠️ NULL (add to message) |
| Posted Date | posted_date | ⚠️ NULL (update later) |
| Tracking Number | tracking_number | ⚠️ NULL (update later) |
| Status | status | ✅ "verified" |
| Notes | notes | ⚠️ NULL (add to message) |
| Payment Method | payment_method | ⚠️ NULL (add to message) |
| Shipping Address | shipping_address | ⚠️ NULL (add to message) |
| Shipping Method | shipping_method | ⚠️ NULL (add to message) |
| QTY Received | qty_received | ✅ Default 0 |
| Order ID | id | ✅ Auto-generated |
| Created | created_at | ✅ Auto-generated |
| Modified | updated_at | ✅ Auto-generated |

---

## 📝 How to Include Optional Fields

### To populate ALL fields from your Refract message:

```
Successful Checkout | Best Buy US
Product
STARLINK - Mini Kit AC Dual Band Wi-Fi System - White
Price
$299.99
Quantity
1
Total
$299.99
Commission
$50.00
Profile
Lennar #8-$48-@07
Proxy Details
Wealth Resi | http://resi-edge-pool.wealthproxies.com:5959/
Order Number
#BBY01-807102506907
Email
woozy_byes28@icloud.com
Reference #
REF-2024-001
Tracking Number
1Z999AA10123456784
Status
verified
Payment Method
Credit Card
Shipping Address
123 Main St, City, State 12345
Shipping Method
Express Shipping
Notes
Customer requested gift wrap
```

---

## 🔄 Updating Orders

### When Refract sends an update for the same order:

**Original Message:**
```
Order Number
#BBY01-807102506907
Status
pending
```

**Update Message (later):**
```
Order Number
#BBY01-807102506907
Status
shipped
Tracking Number
1Z999AA10123456784
Shipped Date
2024-10-28
```

**Result:**
- Same order_number → Updates existing order
- Only changed fields get updated
- System logs the changes in `order_events` table
- `updated_at` timestamp is updated

---

## 🎨 Parser Logic Details

### Product Extraction:
```python
Regex: r'Product\n(.*?)(?:\n|$)'
Example: "Product\nNike Shoes" → "Nike Shoes"
```

### Price Extraction:
```python
Regex: r'Price\n\$?([\d,]+\.?\d*)'
Examples:
  "Price\n$299.99" → 299.99
  "Price\n299.99" → 299.99
  "Price\n$1,299.99" → 1299.99
```

### Order Number Extraction:
```python
Regex: r'Order Number\n#?(.*?)(?:\n|$)'
Examples:
  "Order Number\n#BBY01-123" → "BBY01-123"
  "Order Number\nBBY01-123" → "BBY01-123"
```

### Status Detection:
```python
Logic:
  If message contains "Successful Checkout" → status = "verified"
  Else if "Status\npending" found → status = "pending"
  Else if "Status\nshipped" found → status = "shipped"
  Else → status = "pending" (default)
```

---

## 🗄️ Example Database Row

After receiving your Refract message, the database will contain:

```sql
INSERT INTO orders (
    order_number,
    product,
    price,
    total,
    quantity,
    email,
    profile,
    proxy_list,
    status,
    order_date,
    order_time,
    source,
    created_at,
    updated_at
) VALUES (
    'BBY01-807102506907',
    'STARLINK - Mini Kit AC Dual Band Wi-Fi System - White',
    299.99,
    299.99,
    1,
    'woozy_byes28@icloud.com',
    'Lennar #8-$48-@07',
    'Wealth Resi | http://resi-edge-pool.wealthproxies.com:5959/',
    'verified',
    '2024-10-27 17:56:00',
    '05:56:00 PM',
    'webhook',
    '2024-10-27 17:56:00',
    '2024-10-27 17:56:00'
);
```

---

## 📊 Query Your Data

### Get all orders:
```sql
SELECT * FROM orders ORDER BY created_at DESC;
```

### Get orders with all columns you requested:
```sql
SELECT 
    order_date AS Date,
    order_time AS Time,
    product AS Product,
    price AS Price,
    total AS Total,
    commission AS Commission,
    quantity AS Quantity,
    profile AS Profile,
    proxy_list AS "Proxy List",
    order_number AS "Order Number",
    email AS Email,
    reference_number AS "Reference #",
    posted_date AS "Posted Date",
    tracking_number AS "Tracking Number",
    status AS Status,
    notes AS Notes,
    payment_method AS "Payment Method",
    shipping_address AS "Shipping Address",
    shipping_method AS "Shipping Method",
    qty_received AS "QTY Received",
    id AS "Order ID",
    created_at AS Created,
    updated_at AS Modified
FROM orders
ORDER BY created_at DESC;
```

### Export to CSV:
```bash
sqlite3 -header -csv backend-v2/roms_v2.db \
  "SELECT * FROM orders" > orders_export.csv
```

---

## ✅ Summary

**Automatically Populated from Your Message:**
- ✅ Order Number, Product, Price, Email
- ✅ Profile, Proxy List
- ✅ Date, Time, Status
- ✅ Order ID, Created, Modified

**Set to Defaults:**
- ✅ Quantity (1), Total (same as price), QTY Received (0)

**Optional (add to message if needed):**
- ⚠️ Commission, Reference #, Tracking Number
- ⚠️ Payment Method, Shipping Address/Method, Notes

**Updated Later (via separate webhooks):**
- 📅 Posted Date, Shipped Date, Delivered Date
- 📦 Tracking Number, QTY Received

---

Your webhook is ready! 🚀 Test it with: `python backend-v2/test_refract_webhook.py`

