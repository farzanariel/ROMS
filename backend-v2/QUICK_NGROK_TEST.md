# ⚡ Quick ngrok Setup - Test Webhooks RIGHT NOW

Use this to test webhooks **immediately** while you set up your production Windows server.

---

## 🚀 Setup (2 minutes)

### Step 1: Install ngrok

```bash
brew install ngrok
```

### Step 2: Sign up (Free Account)

1. Go to: https://ngrok.com/
2. Sign up (free)
3. Copy your auth token from dashboard

### Step 3: Authenticate

```bash
ngrok config add-authtoken YOUR_TOKEN_HERE
```

### Step 4: Start Tunnel

**Open a NEW terminal window and run:**

```bash
ngrok http 8001
```

You'll see:
```
ngrok                                                                                                    

Session Status                online
Account                       Your Name (Plan: Free)
Version                       3.x.x
Region                        United States (us)
Latency                       20ms
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123-xyz.ngrok-free.app -> http://localhost:8001

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

### Step 5: Copy Your Webhook URL

Look for the line starting with `Forwarding`. Your webhook URL is:

```
https://abc123-xyz.ngrok-free.app/api/v2/webhooks/orders
```

**⚠️ Important:** 
- Keep this terminal window OPEN
- The URL changes every time you restart ngrok
- Don't close ngrok while testing

---

## 🎯 Update Refract

1. Open Refract settings
2. Find webhook URL field for **Checkout Success**
3. Replace with your ngrok URL:
   ```
   https://abc123-xyz.ngrok-free.app/api/v2/webhooks/orders
   ```
4. Save

---

## 🧪 Test It

### Send Test Checkout

1. Trigger a checkout in Refract
2. Watch ngrok terminal - you'll see:
   ```
   POST /api/v2/webhooks/orders    202 Accepted
   ```

3. Check your frontend: http://localhost:3001
   - New order should appear!

### Monitor in Real-Time

**Terminal 1:** Backend logs
```bash
cd backend-v2
tail -f backend.log
```

**Terminal 2:** ngrok tunnel (running)

**Terminal 3:** Webhook monitor
```bash
cd backend-v2
python monitor_webhooks.py
```

**Browser:** Frontend at http://localhost:3001

---

## 🎯 ngrok Web Interface

While ngrok is running, open:
```
http://localhost:4040
```

This shows:
- ✅ All incoming requests
- ✅ Request/response details
- ✅ Replay requests (for debugging)
- ✅ Request inspection

Super useful for debugging!

---

## ⚠️ ngrok Limitations (Free Tier)

- ❌ URL changes on restart
- ❌ 40 requests/minute limit
- ❌ Random subdomain
- ⏱️ 2 hour session timeout

**For Production:** Use your Windows server + domain (see PRODUCTION_DEPLOYMENT.md)

---

## 📊 What to Expect

When a real checkout webhook comes in:

```
ngrok terminal:
POST /api/v2/webhooks/orders    202 Accepted

Backend log:
✅ Webhook received and queued
✅ Worker processing webhook
✅ Order created: BBY01-123456789
✅ Broadcast via WebSocket

Frontend:
🎉 New row appears in table automatically!
```

**Processing time:** < 500ms

---

## 🔄 Commands Reference

```bash
# Start ngrok
ngrok http 8001

# Check ngrok status
curl http://localhost:4040/api/tunnels

# Stop ngrok
Ctrl+C in ngrok terminal

# Get current URL (if you forgot)
curl -s http://localhost:4040/api/tunnels | python3 -c "import sys,json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])"
```

---

## 🎉 You're Ready!

1. ✅ ngrok running
2. ✅ Backend running (port 8001)
3. ✅ Frontend running (port 3001)
4. ✅ Refract updated with ngrok URL
5. ✅ Send test checkouts!

**Watch the magic happen in real-time!** ✨

---

## 🚀 After Testing

When ready for production:
1. Stop ngrok
2. Follow `PRODUCTION_DEPLOYMENT.md`
3. Update Refract with your domain URL
4. Enjoy production webhooks!

---

**Questions? The ngrok URL is temporary - perfect for testing, but use your Windows server for production!**

