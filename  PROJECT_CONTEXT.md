# Discord Order Dashboard - Project Context

## Overview
This web dashboard is being built to replace/enhance an existing Discord bot for order management. The bot currently handles order processing, Google Sheets integration, and CSV data management. This web interface will provide better analytics, real-time dashboards, and improved user experience while maintaining all existing functionality.

## Current Discord Bot System

### Core Functionality
The existing Discord bot processes order data through several key features:

1. **Upload Orders** - Processes text files containing "Successful Checkout" messages
2. **Mark Received** - Updates order status and financial data from CSV files  
3. **Track Orders** - Adds tracking numbers to existing orders
4. **Cancel Orders** - Marks orders as cancelled
5. **Reconcile Charges** - Syncs payment and charge data from CSV files

### Data Processing Flow

Text/CSV Files → Discord Bot → Parse/Format → Google Sheets (19-column format)


## Google Sheets Integration

### Authentication
- Uses Google Service Account with `credentials.json`
- Requires sheets and drive API access
- Real-time bi-directional sync capability

### Standard 19-Column Sheet Format
| Position | Column Name | Data Type | Format | Filled By |
|----------|------------|-----------|---------|-----------|
| 0 | Date | Date | YYYY-MM-DD | Upload Orders |
| 1 | Time | Time | HH:MM:SS AM/PM | Upload Orders |
| 2 | Product | Text | Raw text | Upload Orders |
| 3 | Price | Currency | $X,XXX.XX | Upload Orders |
| 4 | Total | Currency | $X,XXX.XX | Mark Received |
| 5 | Commission | Currency | $X.XX | Mark Received |
| 6 | Quantity | Integer | 5 | Upload Orders |
| 7 | Profile | Text | Raw text | Upload Orders |
| 8 | Proxy List | Text | IP:Port format | Upload Orders |
| 9 | Order Number | Text | Order ID | Upload Orders |
| 10 | Email | Text | customer@email.com | Upload Orders |
| 11 | Reference # | Text | Payment ref | Reconcile Charges |
| 12 | Posted Date | Date | YYYY-MM-DD | Reconcile Charges |
| 13 | Tracking Number | Text | Tracking ID | Track Orders |
| 14 | Status | Text | VERIFIED/UNVERIFIED | Mark Received |
| 15 | QTY Received | Integer | 5 | Mark Received |
| 16 | Order ID | Text | Internal ID | Mark Received |
| 17 | Created | Timestamp | MM-DD-YYYY, HH:MM:SS | Mark Received |
| 18 | Modified | Timestamp | MM-DD-YYYY, HH:MM:SS | Mark Received |

## Data Formatting Rules (CRITICAL)

### Currency Formatting
- **Price**: `$X,XXX.XX` (with comma separators)
- **Total**: `$X,XXX.XX` (with comma separators) 
- **Commission**: `$X.XX` (no comma needed for smaller amounts)

### Number Formatting
- **Quantity**: Integer (e.g., `5`, not `"5"`)
- **QTY Received**: Integer (e.g., `3`, not `"3"`)

### Text Parsing
- **Proxy List**: Handles multiple formats:
  - Standard: `Proxy List\n192.168.1.1:8080`
  - With colon: `Proxy List: 192.168.1.1:8080`
  - Short form: `Proxy\n192.168.1.1:8080`
  - Case insensitive matching

## Key Technical Issues Solved

### 1. Message Length Limits
- **Problem**: Discord has 2000 character limit, large CSV results caused failures
- **Solution**: Implemented `send_long_list()` function that splits long lists across multiple messages
- **Implementation**: Splits at 1800 chars with part numbering

### 2. Data Formatting
- **Problem**: Raw numbers/text instead of proper currency/integer formatting
- **Solution**: Format data during processing:
  - Price: `f"${float(x):,.2f}"` 
  - Quantity: `int(x)`
  - Total/Commission: Currency format with proper comparison logic

### 3. Proxy List Parsing Failures
- **Problem**: Different message formats caused proxy data to be missed
- **Solution**: Multiple regex patterns with fallbacks:
  - `r'Proxy List\n(.*?)(?:\n|$)'` (primary)
  - `r'Proxy List:(.*?)(?:\n|$)'` (with colon)
  - `r'Proxy\n(.*?)(?:\n|$)'` (short form)
  - Plus case-insensitive matching

## Message Processing Details

### Upload Orders - Text File Format
Processes "Successful Checkout" messages with this structure:

Successful Checkout
Product
[Product Name]
Price
$29.99
Quantity
1
Profile
[Profile Name]
Proxy List
192.168.1.1:8080
Order Number
#12345
Email
customer@email.com


### Mark Received - CSV Format
Expects CSV with columns: `tracking_number, total, commission, status, qty, order_number, created, modified`

### CSV Processing Features
- Auto-detects column names (case-insensitive)
- Validates required columns before processing
- Batch updates for performance
- Progress tracking with visual indicators
- Error handling with detailed reporting

## Web Dashboard Requirements

### Core Features to Implement
1. **Real-time Dashboard** with KPIs:
   - Total revenue, orders today, pending shipments
   - Order pipeline visualization
   - Status breakdown charts

2. **Editable Data Table**:
   - Google Sheets-style inline editing
   - Real-time sync with Google Sheets
   - Bulk operations and filtering

3. **CSV Processing**:
   - Drag & drop file upload
   - Column mapping interface
   - Progress tracking
   - Same validation as Discord bot

4. **Analytics & Reporting**:
   - Performance metrics
   - Trend analysis
   - Supplier performance tracking
   - Financial insights

### Technical Stack Recommendations
- **Backend**: FastAPI (Python) - reuse existing logic
- **Frontend**: React + TypeScript
- **Database**: PostgreSQL for caching/analytics
- **Real-time**: WebSockets for live updates
- **Deployment**: Vercel (frontend) + Railway/Render (backend)

### Data Sync Strategy
- **Bi-directional sync**: Edit on web → updates Google Sheets, edit in Sheets → updates web
- **Real-time updates**: WebSocket connections for live collaboration
- **Conflict resolution**: Handle simultaneous edits gracefully
- **Offline support**: Queue changes when internet is down

## Integration Approach

### Phase 1: Read-Only Dashboard (Safe Start)
- Connect to existing Google Sheets (read-only)
- Build analytics dashboard
- Implement data visualization
- **Zero risk** to current operations

### Phase 2: Write Capabilities
- Add CSV upload processing
- Implement table editing
- Test on sheet copies first
- Gradual feature migration

### Phase 3: Full Integration
- Complete feature parity with Discord bot
- Advanced analytics and reporting
- Mobile responsive design
- Team collaboration features

## Current Bot File Structure

Discord Order Automation/
├── bot.py (main bot file - 6000+ lines)
├── credentials.json (Google service account)
├── auth.py (user authentication)
├── csv_processor.py (CSV handling)
├── sheet_manager.py (Google Sheets operations)
├── mark_received.py (order status updates)
├── order_tracker.py (tracking management)
├── config.py (configuration settings)
└── requirements.txt (Python dependencies)
!
Instructions for you:
Copy this entire content into a file called PROJECT_CONTEXT.md in your new project
When you start a new Cursor project, begin your first conversation with Claude by saying: "Please read the PROJECT_CONTEXT.md file in this project for full background, then let's start building the web dashboard"
Reference specific sections as needed: "As mentioned in the context file, we need to handle the 19-column format..."
This gives any future Claude session complete context about your current system, technical requirements, and goals!


## Environment Setup
- Python 3.9+
- Discord.py library
- gspread for Google Sheets
- FastAPI for future web backend
- React for future frontend

---

## Prompt for Future Claude Sessions

Hey Claude! I'm building a web dashboard to replace/enhance a Discord bot for order management. Here's the complete context:

**Current System**: Discord bot processes checkout messages and CSV files, managing order data in Google Sheets with a standardized 19-column format. Key features include Upload Orders (text file processing), Mark Received (CSV status updates), tracking management, and charge reconciliation.

**Technical Details**: 
- Google Sheets integration with real-time sync
- Specific data formatting (currency: $X,XXX.XX, integers for quantities)
- Complex message parsing with multiple fallback patterns
- Batch processing with progress tracking
- Message length handling for Discord limits

**Web Dashboard Goals**:
- Real-time analytics dashboard with KPIs
- Google Sheets-style editable data table
- Drag & drop CSV processing
- Bi-directional sync with existing Google Sheets
- Mobile-responsive design with advanced filtering

**Architecture**: FastAPI backend + React frontend, PostgreSQL for caching, WebSockets for real-time updates. Start with read-only implementation for safety, then gradually add write capabilities.

Ready to build this step by step, starting with [specific feature you want to work on]!