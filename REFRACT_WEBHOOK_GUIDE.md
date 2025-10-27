# Refract Webhook Integration Guide

## 🎯 Quick Setup

Your webhook is ready to receive Refract messages!

**Webhook URL:**
```
http://localhost:8001/api/v2/webhooks/orders
```

**For Production (with domain):**
```
https://your-domain.com/api/v2/webhooks/orders
```

---

## 📋 Supported Message Format

Your webhook automatically parses Refract's text format:

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
Share Link
Click Here
Order Number
#BBY01-807102506907
Email
woozy_byes28@icloud.com
Image
```

### 📊 What Gets Stored in Database

| Message Field | Database Column | Example |
|---|---|---|
| Product | product | "STARLINK - Mini Kit..." |
| Price | price & total | 299.99 |
| Profile | profile | "Lennar #8-$48-@07" |
| Proxy Details | proxy_list | "Wealth Resi \| http://..." |
| Order Number | order_number | "BBY01-807102506907" |
| Email | email | "woozy_byes28@icloud.com" |
| (auto) | status | "verified" (from "Successful Checkout") |
| (auto) | order_date | Current timestamp |
| (auto) | order_time | Current time |
| (auto) | quantity | 1 (default) |

### 📝 Optional Fields

If your Refract message includes these, they'll be parsed:

```
Quantity
2
Total
$599.98
Commission
$50.00
Tracking Number
1Z999AA10123456784
Reference #
REF123
Payment Method
Credit Card
Shipping Address
123 Main St, City, State
Shipping Method
Express
Status
pending
Notes
Special instructions here
```

---

## 🚀 Testing Your Webhook

### Step 1: Start Backend V2

```bash
cd backend-v2

# Install dependencies (first time only)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start the server
python main.py
```

You should see:
```
🚀 ROMS V2 API Server starting...
📊 Database: SQLite (roms_v2.db)
🔌 WebSocket manager initialized
✅ Server running on http://0.0.0.0:8001
```

### Step 2: Test with Your Exact Message

```bash
cd backend-v2
python test_refract_webhook.py
```

This will:
- ✅ Send your exact Refract message format
- ✅ Parse all fields
- ✅ Store in database
- ✅ Show you what was parsed
- ✅ Verify everything works

Expected output:
```
🧪 Testing Refract Webhook Format
============================================================
📤 Sending webhook message...
📊 Response Status: 200

✅ Webhook processed successfully!

📦 Order Details:
   Order ID: 1
   Order Number: BBY01-807102506907
   Message: Order received and processed successfully

✅ SUCCESS! Your Refract webhook is working!

📋 What got parsed:
   - Product: STARLINK - Mini Kit...
   - Price: $299.99
   - Order Number: BBY01-807102506907
   - Email: woozy_byes28@icloud.com
   - Profile: Lennar #8-$48-@07
   - Proxy List: Wealth Resi | http://...
   - Status: verified (auto-detected)
```

---

## ⚙️ Configure Refract

### In Your Refract/Discord Bot Settings:

1. **Find Webhook Settings**
   - Look for "Webhooks", "Integrations", or "Notifications"

2. **Add New Webhook**
   - URL: `http://localhost:8001/api/v2/webhooks/orders`
   - Method: `POST`
   - Content-Type: `text/plain` (or leave default)

3. **Select Events**
   - Enable: "Successful Checkout"
   - Optional: "Order Update", "Tracking Update", etc.

4. **Save & Test**
   - Send a test checkout
   - Verify order appears in database

---

## 🌐 Production Setup (Public URL)

### Option 1: ngrok (Quick Testing)

```bash
# Install ngrok
brew install ngrok  # Mac
# or from https://ngrok.com

# Start tunnel
ngrok http 8001
```

You'll get a URL like:
```
https://abc123.ngrok.io
```

**Use this in Refract:**
```
https://abc123.ngrok.io/api/v2/webhooks/orders
```

### Option 2: Deploy to Server

Deploy to a VPS and use your domain:
```
https://api.yourdomain.com/api/v2/webhooks/orders
```

---

## 📊 Viewing Your Orders

### Method 1: SQLite Database

```bash
cd backend-v2
sqlite3 roms_v2.db

# View recent orders
SELECT 
    order_number, 
    product, 
    price, 
    email, 
    status, 
    created_at 
FROM orders 
ORDER BY created_at DESC 
LIMIT 10;

# Exit
.exit
```

### Method 2: Webhook Logs API

```bash
# View recent webhook activity
curl http://localhost:8001/api/v2/webhooks/logs?limit=10
```

### Method 3: Interactive API Docs

Visit: **http://localhost:8001/docs**

- Browse all endpoints
- Test queries directly
- View request/response schemas

---

## 🔄 How It Works

```
Refract sends message
      ↓
Webhook receives text
      ↓
Parser extracts fields:
  - Product: from "Product\n..."
  - Price: from "Price\n$..."
  - Order #: from "Order Number\n#..."
  - Email: from "Email\n..."
  - etc.
      ↓
Validator checks data
      ↓
Database stores order
      ↓
WebSocket broadcasts to frontend
      ↓
Success response to Refract
```

---

## 🐛 Troubleshooting

### Problem: "Connection refused"
**Solution:**
- Check backend is running: `curl http://localhost:8001/health`
- Restart: `cd backend-v2 && python main.py`

### Problem: "Could not parse webhook content"
**Solution:**
- Check message format matches example
- View error in webhook logs: `curl http://localhost:8001/api/v2/webhooks/logs`
- Check backend console for detailed errors

### Problem: Order appears but some fields are empty
**Solution:**
- Fields are optional (only order_number is required)
- Check that Refract message includes those fields
- View raw message in webhook logs to see what was sent

### Problem: Refract can't reach webhook
**Solution:**
- Use ngrok for testing: `ngrok http 8001`
- Check firewall settings
- Verify URL is correct (no typos)

### Problem: Duplicate orders
**Solution:**
- System auto-updates existing orders with same order_number
- Check `order_events` table to see update history:
  ```sql
  SELECT * FROM order_events WHERE order_id = 1;
  ```

---

## 🧪 Advanced Testing

### Test Different Scenarios

**Test 1: Minimal order (only required fields)**
```
Successful Checkout | Store
Product
Test Product
Price
$99.99
Order Number
TEST-001
Email
test@example.com
```

**Test 2: Complete order (all fields)**
```
Successful Checkout | Store
Product
Test Product
Price
$99.99
Quantity
2
Total
$199.98
Commission
$20.00
Profile
Profile 1
Proxy Details
Proxy 1
Order Number
TEST-002
Email
test@example.com
Tracking Number
1Z999AA10123456784
Reference #
REF123
Payment Method
Credit Card
Status
shipped
```

**Test 3: Order update (same order number)**
```
Successful Checkout | Store
Order Number
TEST-001
Status
shipped
Tracking Number
1Z999AA10123456784
```

This will update the existing TEST-001 order.

---

## 📚 Database Schema

Your orders are stored with these columns:

```sql
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    order_number VARCHAR(255) NOT NULL UNIQUE,
    product VARCHAR(255),
    price FLOAT,
    total FLOAT,
    commission FLOAT,
    quantity INTEGER DEFAULT 1,
    email VARCHAR(255),
    customer_name VARCHAR(255),
    profile VARCHAR(255),
    proxy_list VARCHAR(255),
    reference_number VARCHAR(255),
    status VARCHAR(50),
    tracking_number VARCHAR(255),
    qty_received INTEGER DEFAULT 0,
    payment_method VARCHAR(255),
    shipping_address TEXT,
    shipping_method VARCHAR(255),
    notes TEXT,
    order_date DATETIME,
    order_time VARCHAR(50),
    posted_date DATETIME,
    shipped_date DATETIME,
    delivered_date DATETIME,
    source VARCHAR(50),
    worksheet_name VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

All fields except `order_number` are optional.

---

## 🎯 Next Steps

1. ✅ Test webhook with `python test_refract_webhook.py`
2. ✅ Configure Refract with webhook URL
3. ✅ Make a test purchase
4. ✅ Verify order in database
5. ✅ Set up ngrok or deploy to server for production
6. 🚀 Build frontend dashboard to view orders in real-time

---

## 📞 Need Help?

- **API Documentation:** http://localhost:8001/docs
- **Webhook Logs:** http://localhost:8001/api/v2/webhooks/logs
- **Health Check:** http://localhost:8001/health
- **Architecture Guide:** `V2_ARCHITECTURE.md`

---

## 🎉 You're All Set!

Your webhook is now automatically capturing and parsing Refract orders into your database!

**What's automatic:**
- ✅ Receives Refract messages
- ✅ Parses all fields
- ✅ Stores in database
- ✅ Updates existing orders
- ✅ Logs everything
- ✅ Real-time WebSocket updates

**No more manual data entry! 🎊**

