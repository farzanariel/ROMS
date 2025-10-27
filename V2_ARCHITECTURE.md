# ROMS Version 2.0 - Architecture & Implementation Plan

## Overview
Version 2.0 will be an automated, event-driven system that replaces manual file uploads with:
- **Webhook integration** for real-time order capture
- **Email scraping** (every 30 minutes) for orders, shipments, cancellations
- **Web scraping** for external data sources
- **SQLite database** for data persistence
- **Backward compatibility** with v1 Google Sheets system

## Directory Structure

```
ROMS/
├── backend/                    # V1 - Current Google Sheets backend (KEEP AS IS)
│   ├── main.py
│   ├── sheet_operations.py
│   └── ...
│
├── backend-v2/                 # V2 - New automated backend
│   ├── main.py                 # FastAPI app with webhooks & scheduled tasks
│   ├── database/
│   │   ├── models.py          # SQLAlchemy models
│   │   ├── schemas.py         # Pydantic schemas
│   │   ├── database.py        # Database connection & session
│   │   └── migrations/        # Alembic migrations
│   ├── services/
│   │   ├── webhook_handler.py # Handle incoming order webhooks
│   │   ├── email_scraper.py   # Email parsing service
│   │   ├── web_scraper.py     # Web scraping service
│   │   ├── order_processor.py # Business logic for orders
│   │   └── sync_service.py    # Sync to Google Sheets (optional bridge)
│   ├── scrapers/
│   │   ├── email/
│   │   │   ├── gmail_client.py
│   │   │   ├── parsers.py     # Parse different email formats
│   │   │   └── filters.py     # Email classification
│   │   └── web/
│   │       ├── base_scraper.py
│   │       └── site_specific.py
│   ├── tasks/
│   │   ├── scheduler.py       # APScheduler for periodic tasks
│   │   └── jobs.py            # Scheduled job definitions
│   ├── api/
│   │   ├── orders.py          # Order endpoints
│   │   ├── webhooks.py        # Webhook endpoints
│   │   └── analytics.py       # Analytics endpoints
│   ├── config.py              # Configuration management
│   ├── requirements.txt       # V2 dependencies
│   └── .env.example           # Environment variables template
│
├── frontend/                   # V1 frontend (KEEP AS IS)
│   └── ...
│
├── frontend-v2/                # V2 frontend (new React app)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx  # Real-time dashboard
│   │   │   ├── Orders.tsx     # Order management
│   │   │   ├── Webhooks.tsx   # Webhook configuration
│   │   │   ├── EmailSync.tsx  # Email sync status
│   │   │   └── Settings.tsx   # V2 settings
│   │   ├── components/
│   │   │   ├── RealTimeOrders.tsx
│   │   │   ├── SyncStatus.tsx
│   │   │   └── ...
│   │   └── services/
│   │       └── api-v2.ts      # V2 API client
│   └── ...
│
├── shared/                     # Shared utilities between v1 & v2
│   ├── parsers.py             # Common parsing logic
│   └── validators.py          # Data validation
│
├── bot.py                      # Discord bot (KEEP AS IS)
├── start-v1.sh                # Start V1 system
├── start-v2.sh                # Start V2 system
└── start-both.sh              # Run both systems simultaneously
```

---

## Phase 1: Database Setup (Week 1)

### 1.1 SQLite Schema Design

**Core Tables:**
- `orders` - All order information
- `order_events` - Event log (created, shipped, cancelled, etc.)
- `products` - Product catalog
- `customers` - Customer information
- `shipments` - Tracking and shipment data
- `reconciliations` - Credit card reconciliation records
- `webhooks_log` - Incoming webhook audit trail
- `email_sync_log` - Email processing history
- `scraping_jobs` - Web scraping job status

### 1.2 Technology Stack

**Backend:**
- **FastAPI** (already using, expand for v2)
- **SQLAlchemy** - ORM for database
- **Alembic** - Database migrations
- **APScheduler** - Scheduled tasks (email scraping every 30 min)
- **Celery** (optional) - For heavy background tasks
- **Redis** (optional) - Task queue & caching

**Scraping & Integration:**
- **httpx** - Async HTTP client for webhooks
- **IMAPClient** or **gmail API** - Email access
- **BeautifulSoup4** or **Playwright** - Web scraping
- **pydantic** - Data validation

**Frontend:**
- Keep existing React + TypeScript
- **Socket.io** or **WebSockets** - Real-time updates
- **React Query** - Data fetching & caching

---

## Phase 2: Backend V2 Core (Week 2-3)

### 2.1 Webhook System

```python
# backend-v2/api/webhooks.py
from fastapi import APIRouter, Request, HTTPException
from services.webhook_handler import process_order_webhook

router = APIRouter()

@router.post("/webhooks/orders")
async def receive_order_webhook(request: Request):
    """
    Receive order webhooks from external software
    Signature verification for security
    """
    payload = await request.json()
    # Verify signature
    # Parse & store in database
    # Trigger real-time frontend update
    return {"status": "received"}
```

### 2.2 Email Scraper (Every 30 Minutes)

```python
# backend-v2/services/email_scraper.py
import imaplib
from email.parser import BytesParser
from tasks.scheduler import scheduler

class EmailOrderScraper:
    def __init__(self):
        self.imap_client = None
    
    async def connect(self):
        """Connect to email server"""
        pass
    
    async def fetch_unprocessed_emails(self):
        """Fetch new emails since last run"""
        pass
    
    async def parse_order_email(self, email_data):
        """Parse order from email content"""
        # Detect email type (order, shipment, cancellation)
        # Extract relevant data
        # Store in database
        pass
    
    async def parse_shipment_email(self, email_data):
        """Parse shipment notification"""
        pass
    
    async def parse_cancellation_email(self, email_data):
        """Parse cancellation notification"""
        pass

# Scheduled job
@scheduler.scheduled_job('interval', minutes=30)
async def scrape_emails_job():
    scraper = EmailOrderScraper()
    await scraper.connect()
    await scraper.fetch_unprocessed_emails()
```

### 2.3 Web Scraper

```python
# backend-v2/services/web_scraper.py
from playwright.async_api import async_playwright

class WebDataScraper:
    async def scrape_site(self, url: str):
        """Scrape data from external site"""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url)
            # Extract data
            # Store in database
            await browser.close()
```

---

## Phase 3: Migration & Coexistence Strategy (Week 4)

### 3.1 Run Both Systems Simultaneously

**Port Allocation:**
- V1 Backend: `http://localhost:8000`
- V2 Backend: `http://localhost:8001`
- V1 Frontend: `http://localhost:3000`
- V2 Frontend: `http://localhost:3001`

**Startup Scripts:**

```bash
# start-v1.sh
cd backend && uvicorn main:app --port 8000 &
cd frontend && npm run dev -- --port 3000
```

```bash
# start-v2.sh
cd backend-v2 && uvicorn main:app --port 8001 &
cd frontend-v2 && npm run dev -- --port 3001
```

### 3.2 Data Sync Bridge (Optional)

Create a sync service to keep Google Sheets updated from SQLite:

```python
# backend-v2/services/sync_service.py
class GoogleSheetsSync:
    """
    Optional: Sync SQLite data to Google Sheets
    Keeps V1 system functional during transition
    """
    async def sync_orders_to_sheets(self):
        # Read new orders from SQLite
        # Push to Google Sheets via V1 API
        pass
```

---

## Phase 4: Frontend V2 Features (Week 4-5)

### 4.1 Real-Time Dashboard
- Live order feed (WebSocket)
- Sync status indicators (email, webhooks, scraping)
- Error notifications

### 4.2 Webhook Management UI
- Configure webhook endpoints
- View webhook logs
- Test webhooks

### 4.3 Email Sync Monitor
- Last sync time
- Emails processed
- Parsing errors
- Manual trigger

---

## Phase 5: Testing & Deployment (Week 6)

### 5.1 Testing Strategy
1. **V2 Shadow Mode**: Run V2 in background, compare results with V1
2. **Gradual Migration**: Start with one data source (e.g., webhooks only)
3. **Parallel Operation**: Run both systems for 2-4 weeks
4. **Data Validation**: Ensure V2 captures all data V1 does

### 5.2 Rollout Plan
1. **Week 1-3**: Build V2 backend + database
2. **Week 4**: Build V2 frontend
3. **Week 5-6**: Run V2 in shadow mode (no UI exposure)
4. **Week 7-8**: Beta testing with V2 UI
5. **Week 9+**: Full production, deprecate V1 gradually

---

## Key Technologies & Libraries

### Backend V2 New Dependencies:
```txt
# backend-v2/requirements.txt
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
alembic==1.12.1
pydantic==2.5.0
httpx==0.25.1
apscheduler==3.10.4
python-dotenv==1.0.0

# Email scraping
imapclient==3.0.1
google-auth==2.24.0
google-auth-oauthlib==1.1.0
google-api-python-client==2.108.0

# Web scraping
beautifulsoup4==4.12.2
playwright==1.40.0
selenium==4.15.2

# Database
aiosqlite==0.19.0

# Optional: Background tasks
celery==5.3.4
redis==5.0.1
```

---

## Environment Configuration

```bash
# backend-v2/.env
# Database
DATABASE_URL=sqlite+aiosqlite:///./roms_v2.db

# Webhook Security
WEBHOOK_SECRET=your_webhook_secret_key

# Email Configuration
EMAIL_PROVIDER=gmail
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993

# Web Scraping
TARGET_SITE_URL=https://example.com
SCRAPING_INTERVAL_MINUTES=30

# API Configuration
API_V2_PORT=8001
API_V2_HOST=0.0.0.0

# Google Sheets (optional bridge)
ENABLE_SHEETS_SYNC=false
V1_API_URL=http://localhost:8000
```

---

## Migration Checklist

- [ ] Create `backend-v2` directory structure
- [ ] Set up SQLite database with SQLAlchemy
- [ ] Implement webhook receiver endpoint
- [ ] Build email scraper service
- [ ] Build web scraper service
- [ ] Set up APScheduler for periodic tasks
- [ ] Create V2 FastAPI endpoints (orders, analytics)
- [ ] Build real-time WebSocket connection
- [ ] Create frontend-v2 with React
- [ ] Implement sync bridge (optional)
- [ ] Write migration scripts (Sheets → SQLite)
- [ ] Set up monitoring & logging
- [ ] Create startup scripts for both systems
- [ ] Test parallel operation
- [ ] Document V2 API
- [ ] Train on V2 system usage

---

## Benefits of This Approach

1. **Zero Downtime**: V1 continues working while building V2
2. **Gradual Migration**: Test thoroughly before switching
3. **Easy Rollback**: Can revert to V1 if issues arise
4. **Learn from V1**: Improve architecture based on V1 experience
5. **Future-Proof**: SQLite → PostgreSQL migration easier than Sheets → Postgres

---

## Next Steps

1. **Review this plan** - Adjust timeline/features as needed
2. **Set up development environment** - Install dependencies
3. **Create database schema** - Design tables
4. **Start with webhook system** - Easiest to test
5. **Add email scraper** - Most valuable automation
6. **Build frontend gradually** - One page at a time

Let me know when you're ready to start, and I'll help you build each component! 🚀

