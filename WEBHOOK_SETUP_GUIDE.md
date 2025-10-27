# Webhook Setup Guide - ROMS V2

## 🎯 Quick Start

Your webhook URL is ready! Just paste this into your external software:

```
http://localhost:8001/api/v2/webhooks/orders
```

For production (with a domain):
```
https://your-domain.com/api/v2/webhooks/orders
```

---

## 📋 Step-by-Step Setup

### Step 1: Start the V2 Backend

```bash
cd backend-v2
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

The backend will start on **http://localhost:8001**

### Step 2: Test the Webhook is Working

Open your browser or use curl:

```bash
# Test if webhook endpoint is accessible
curl http://localhost:8001/api/v2/webhooks/test
```

You should see:
```json
{
  "status": "ok",
  "message": "Webhook endpoint is operational",
  "timestamp": "2024-10-27T...",
  "signature_required": false
}
```

### Step 3: Send a Test Order

```bash
curl -X POST http://localhost:8001/api/v2/webhooks/orders \
  -H "Content-Type: application/json" \
  -d '{
    "order_number": "12345",
    "product": "Nike Shoes",
    "price": 99.99,
    "quantity": 1,
    "email": "customer@example.com",
    "status": "pending"
  }'
```

Success response:
```json
{
  "success": true,
  "message": "Order received and processed successfully",
  "order_id": 1,
  "order_number": "12345"
}
```

### Step 4: Verify Order was Stored

```bash
# Check webhook logs
curl http://localhost:8001/api/v2/webhooks/logs
```

---

## 🔌 Supported Field Mappings

The webhook automatically maps various field names to your database:

| Your Field Names | Database Column | Example Values |
|---|---|---|
| `product`, `product_name`, `item` | product | "Nike Shoes" |
| `price`, `unit_price` | price | 99.99 |
| `total`, `total_price`, `amount` | total | 199.98 |
| `commission`, `profit` | commission | 15.00 |
| `quantity`, `qty` | quantity | 2 |
| `email`, `customer_email` | email | "test@email.com" |
| `customer_name`, `name` | customer_name | "John Doe" |
| `profile` | profile | "Profile1" |
| `proxy_list`, `proxy` | proxy_list | "Proxy1" |
| `reference`, `reference_number` | reference_number | "REF123" |
| `status`, `order_status` | status | "pending" |
| `tracking`, `tracking_number`, `shipment_id` | tracking_number | "1Z999AA10123456784" |
| `order_date`, `created_at`, `date` | order_date | "2024-10-27T10:30:00Z" |

**This means your webhook can send ANY of these field names and they'll be mapped correctly!**

---

## 📝 Example Webhook Payloads

### Minimal Order (only required fields)
```json
{
  "order_number": "ORD-001"
}
```

### Standard Order
```json
{
  "order_number": "ORD-001",
  "product": "Nike Air Max",
  "price": 120.00,
  "quantity": 1,
  "email": "customer@example.com",
  "status": "pending"
}
```

### Complete Order (all fields)
```json
{
  "order_number": "ORD-001",
  "product": "Nike Air Max",
  "price": 120.00,
  "total": 120.00,
  "commission": 15.00,
  "quantity": 1,
  "email": "customer@example.com",
  "customer_name": "John Doe",
  "profile": "Profile1",
  "proxy_list": "Proxy1",
  "reference_number": "REF123",
  "status": "verified",
  "tracking_number": "1Z999AA10123456784",
  "order_date": "2024-10-27T10:30:00Z"
}
```

### Update Existing Order
Send the same `order_number` with new data:
```json
{
  "order_number": "ORD-001",
  "status": "shipped",
  "tracking_number": "1Z999AA10123456784"
}
```

The system will:
- Find the existing order
- Update only the changed fields
- Log the update in order_events table

---

## 🔐 Security: Webhook Signatures (Optional but Recommended)

### Why Use Signatures?
Signatures ensure that webhooks are actually from your software and haven't been tampered with.

### How to Generate Signature

**Python:**
```python
import hmac
import hashlib
import json
import requests

# Your payload
payload = {
    "order_number": "12345",
    "product": "Nike Shoes",
    "price": 99.99
}

# Convert to JSON string
payload_string = json.dumps(payload)

# Your secret (set in backend-v2/.env)
secret = "your-webhook-secret"

# Generate signature
signature = hmac.new(
    secret.encode(),
    payload_string.encode(),
    hashlib.sha256
).hexdigest()

# Send request
headers = {
    "Content-Type": "application/json",
    "X-Webhook-Signature": signature
}

response = requests.post(
    "http://localhost:8001/api/v2/webhooks/orders",
    json=payload,
    headers=headers
)
```

**Node.js:**
```javascript
const crypto = require('crypto');
const axios = require('axios');

const payload = {
    order_number: "12345",
    product: "Nike Shoes",
    price: 99.99
};

const payloadString = JSON.stringify(payload);
const secret = "your-webhook-secret";

const signature = crypto
    .createHmac('sha256', secret)
    .update(payloadString)
    .digest('hex');

axios.post('http://localhost:8001/api/v2/webhooks/orders', payload, {
    headers: {
        'Content-Type': 'application/json',
        'X-Webhook-Signature': signature
    }
});
```

**curl:**
```bash
SECRET="your-webhook-secret"
PAYLOAD='{"order_number":"12345","product":"Nike Shoes","price":99.99}'
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

curl -X POST http://localhost:8001/api/v2/webhooks/orders \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: $SIGNATURE" \
  -d "$PAYLOAD"
```

---

## 🌐 Production Setup (Exposing to Internet)

### Option 1: Using ngrok (Quick Testing)

```bash
# Install ngrok
brew install ngrok  # Mac
# or download from https://ngrok.com

# Start ngrok tunnel
ngrok http 8001
```

You'll get a public URL like:
```
https://abc123.ngrok.io
```

Your webhook URL becomes:
```
https://abc123.ngrok.io/api/v2/webhooks/orders
```

### Option 2: Deploy to Cloud (Production)

**Using a VPS (DigitalOcean, AWS, etc):**

1. Deploy your backend to the server
2. Set up a domain (e.g., `api.yourdomain.com`)
3. Configure nginx/Apache as reverse proxy
4. Use SSL certificate (Let's Encrypt)

Your webhook URL:
```
https://api.yourdomain.com/api/v2/webhooks/orders
```

---

## 📊 Monitoring & Debugging

### View Webhook Logs

```bash
# See last 50 webhook requests
curl http://localhost:8001/api/v2/webhooks/logs

# See more
curl "http://localhost:8001/api/v2/webhooks/logs?limit=100"
```

### Check API Documentation

Visit: **http://localhost:8001/docs**

This shows:
- All available endpoints
- Request/response schemas
- Try it out directly in browser

### View Database

```bash
cd backend-v2

# Install sqlite3 if not already installed
# brew install sqlite  # Mac

# Open database
sqlite3 roms_v2.db

# View orders
SELECT * FROM orders ORDER BY created_at DESC LIMIT 10;

# View webhook logs
SELECT * FROM webhook_logs ORDER BY created_at DESC LIMIT 10;

# Exit
.exit
```

---

## 🎯 Configure Your External Software

### Generic Webhook Configuration

Most software will ask for:

1. **Webhook URL:**
   ```
   http://localhost:8001/api/v2/webhooks/orders
   ```
   (or your public URL if deployed)

2. **HTTP Method:** `POST`

3. **Content-Type:** `application/json`

4. **Headers (optional):**
   - `X-Webhook-Signature`: (your generated signature)

5. **Events to trigger:**
   - New order created
   - Order updated
   - Order status changed

### Example Configurations

**Shopify:**
- Go to Settings → Notifications → Webhooks
- Click "Create webhook"
- Event: "Order creation"
- Format: JSON
- URL: Your webhook URL

**WooCommerce:**
- Install "WooCommerce Webhooks" plugin
- Go to WooCommerce → Settings → Advanced → Webhooks
- Add webhook
- Topic: "Order created"
- Delivery URL: Your webhook URL

**Custom Software:**
Configure your software to POST JSON to your webhook URL whenever an order is created/updated.

---

## ✅ Testing Checklist

- [ ] V2 backend is running on port 8001
- [ ] Can access http://localhost:8001/health
- [ ] Webhook test endpoint responds: http://localhost:8001/api/v2/webhooks/test
- [ ] Can create test order via curl or Postman
- [ ] Order appears in database (check logs endpoint)
- [ ] External software is configured with webhook URL
- [ ] Signature verification working (if enabled)
- [ ] Webhook logs show successful processing

---

## 🐛 Troubleshooting

### Webhook Returns 404
- Check backend is running: `curl http://localhost:8001/health`
- Verify URL: `http://localhost:8001/api/v2/webhooks/orders`

### Webhook Returns 401 (Invalid Signature)
- Verify `WEBHOOK_SECRET` matches in both places
- Check signature generation code
- Ensure payload string is exactly the same as sent

### Webhook Returns 400 (Invalid Payload)
- Check JSON is valid
- `order_number` is required
- Check field names match supported mappings

### Order Not Appearing in Database
- Check webhook logs: `curl http://localhost:8001/api/v2/webhooks/logs`
- Look for error messages in logs
- Check backend console for error output

### Can't Access from External Software
- Use ngrok for testing
- Check firewall settings
- Verify port 8001 is accessible

---

## 📚 Additional Resources

- **API Documentation:** http://localhost:8001/docs
- **Signature Help:** http://localhost:8001/api/v2/webhooks/signature-help
- **Architecture Guide:** `/Users/farzan/Documents/Projects/ROMS/V2_ARCHITECTURE.md`
- **Backend README:** `/Users/farzan/Documents/Projects/ROMS/backend-v2/README.md`

---

## 🎉 You're All Set!

Your webhook receiver is now ready to automatically capture orders from your external software! No more manual file uploads needed.

**Next Steps:**
1. Configure your external software to send webhooks
2. Monitor incoming orders via webhook logs
3. Build a frontend dashboard to view orders in real-time
4. Set up email scraping (next feature)

