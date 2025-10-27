# ROMS V2 - Automated Order Management System

Version 2.0 introduces automated data capture through webhooks, email scraping, and web scraping, replacing manual file uploads with a SQLite database backend.

## 🚀 Quick Start

### 1. Set Up Environment

```bash
# From the ROMS root directory
cd backend-v2

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual configuration
nano .env  # or use your preferred editor
```

**Required Configuration:**
- `EMAIL_ADDRESS` - Your Gmail address
- `EMAIL_APP_PASSWORD` - Gmail app password (not your regular password!)
- `WEBHOOK_SECRET` - Secret key for webhook verification
- `SECRET_KEY` - Application secret key

### 3. Initialize Database

```bash
# Run the application once to create the database
python main.py
```

The database file `roms_v2.db` will be created automatically.

### 4. Run the Backend

```bash
# Development mode (auto-reload)
python main.py

# Or use uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### 5. Access the API

- **API**: http://localhost:8001
- **Interactive Docs**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health

---

## 📁 Project Structure

```
backend-v2/
├── main.py                     # FastAPI application entry point
├── requirements.txt            # Python dependencies
├── .env.example               # Environment template
├── roms_v2.db                 # SQLite database (auto-generated)
│
├── database/
│   ├── models.py              # SQLAlchemy models
│   ├── database.py            # Database connection
│   └── migrations/            # Alembic migrations (future)
│
├── services/
│   ├── webhook_handler.py     # Process incoming webhooks
│   ├── email_scraper.py       # Email parsing service
│   ├── web_scraper.py         # Web scraping service
│   └── order_processor.py     # Business logic
│
├── scrapers/
│   ├── email/
│   │   ├── gmail_client.py    # Gmail API integration
│   │   └── parsers.py         # Email format parsers
│   └── web/
│       └── site_scraper.py    # Website scraping logic
│
├── tasks/
│   ├── scheduler.py           # APScheduler setup
│   └── jobs.py                # Scheduled task definitions
│
└── api/
    ├── orders.py              # Order endpoints
    ├── webhooks.py            # Webhook endpoints
    └── analytics.py           # Analytics endpoints
```

---

## 🔌 Features

### ✅ Currently Available
- [x] SQLite database with SQLAlchemy ORM
- [x] FastAPI backend with async support
- [x] WebSocket for real-time updates
- [x] Health check endpoints
- [x] CORS middleware
- [x] Environment-based configuration

### 🚧 To Be Implemented
- [ ] Webhook receiver endpoint
- [ ] Email scraper (Gmail integration)
- [ ] Web scraper (Playwright/Selenium)
- [ ] APScheduler for periodic tasks
- [ ] Order CRUD endpoints
- [ ] Analytics endpoints
- [ ] Authentication & API keys

---

## 📊 Database Models

### Core Tables

1. **orders** - Main order data
   - Order information, customer details, status, tracking
   - Timestamps and metadata

2. **order_events** - Audit log of order changes
   - Event type (created, shipped, cancelled)
   - Source tracking (webhook, email, scrape)

3. **webhook_logs** - Incoming webhook audit trail
   - Payload, headers, processing status

4. **email_sync_logs** - Email scraping history
   - Emails fetched/processed, errors

5. **scraping_jobs** - Web scraping job status
   - Job type, records scraped, errors

6. **products** - Product catalog

7. **customers** - Customer information

8. **reconciliations** - Credit card reconciliation

---

## 🔧 Next Steps

### Phase 1: Webhook Integration
1. Create `api/webhooks.py`
2. Implement webhook signature verification
3. Parse incoming order data
4. Store in database
5. Broadcast via WebSocket

### Phase 2: Email Scraper
1. Set up Gmail API credentials
2. Create `services/email_scraper.py`
3. Implement email parsing for different formats
4. Schedule every 30 minutes with APScheduler
5. Handle different email types (orders, shipments, cancellations)

### Phase 3: Web Scraper
1. Set up Playwright
2. Create site-specific scrapers
3. Schedule periodic scraping
4. Store scraped data in database

### Phase 4: Frontend
1. Create `frontend-v2` directory
2. Build real-time dashboard with WebSocket
3. Add webhook configuration UI
4. Add email sync monitor
5. Add scraping job status

---

## 🛠️ Development

### Running Both V1 and V2

```bash
# From ROMS root directory
chmod +x start-both.sh
./start-both.sh
```

This will start:
- V1 Backend on port 8000
- V2 Backend on port 8001
- V1 Frontend on port 3000

### Database Migrations (Future)

```bash
# Initialize Alembic
alembic init database/migrations

# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

### Testing

```bash
# Run tests (when implemented)
pytest

# With coverage
pytest --cov=.
```

---

## 📚 API Documentation

Once running, visit **http://localhost:8001/docs** for interactive API documentation.

### Example: Create Order via API

```bash
curl -X POST http://localhost:8001/api/v2/orders \
  -H "Content-Type: application/json" \
  -d '{
    "order_number": "12345",
    "product": "Nike Shoes",
    "price": 120.00,
    "email": "customer@example.com",
    "status": "pending"
  }'
```

---

## 🔐 Security

### Webhook Security
- Use `WEBHOOK_SECRET` to verify incoming webhooks
- Validate signatures for all webhook payloads

### Email Security
- Use Gmail App Passwords (not your regular password)
- Enable 2FA on your Google account
- Restrict API access scopes

### API Security (Future)
- Implement API key authentication
- Rate limiting
- Input validation with Pydantic

---

## 🐛 Troubleshooting

### Database Not Creating
```bash
# Manually create database
python -c "from database.database import init_db; import asyncio; asyncio.run(init_db())"
```

### Port Already in Use
```bash
# Find process using port 8001
lsof -i :8001

# Kill the process
kill -9 <PID>
```

### Email Scraping Not Working
- Verify Gmail App Password is correct
- Check IMAP is enabled in Gmail settings
- Verify `.env` configuration

---

## 📞 Support

For issues or questions, refer to:
- Main documentation: `../V2_ARCHITECTURE.md`
- API docs: http://localhost:8001/docs

---

## 🎯 Roadmap

**Week 1-2**: Core database and webhook system  
**Week 3**: Email scraping integration  
**Week 4**: Web scraping integration  
**Week 5-6**: Frontend V2  
**Week 7+**: Testing and production deployment

