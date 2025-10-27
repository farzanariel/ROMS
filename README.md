# Order Management Dashboard

A modern web dashboard to replace/enhance your Discord bot for order management, providing better analytics and **inventory visibility** - addressing your main pain point of tracking pending orders and overall inventory status.

## 🎯 Key Features

### Inventory Overview (Your Main Need)
- **Real-time pending orders tracking** - No more guessing what needs attention
- **Quantity completion tracking** - See what's been received vs. ordered
- **Status breakdown visualization** - Verified, unverified, and cancelled orders at a glance
- **Missing tracking alerts** - Quickly identify orders without tracking numbers

### Analytics Dashboard
- Total revenue, orders today, pending shipments KPIs
- Order pipeline visualization with completion rates
- Top products analysis
- Status distribution charts

### Live Order Management
- **Real-time editable tables** - Click any cell to edit directly
- **Instant Google Sheets sync** - Changes reflect immediately in your sheet
- **Live data updates** - See changes from Discord bot or direct sheet edits in real-time
- Sortable, filterable order tables with pending orders highlighting
- Advanced search across all order fields
- WebSocket-powered live updates

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- Google Service Account with Sheets API access
- Existing Google Sheets with 19-column format (as per your PROJECT_CONTEXT.md)

### Backend Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Add your Google credentials
# Place your credentials.json file in the backend directory

# Start the FastAPI server
cd backend
python main.py
```

### Frontend Setup
```bash
# Install Node.js dependencies
cd frontend
npm install

# Start the development server
npm run dev
```

### Configuration
1. Visit http://localhost:3000/settings
2. Enter your Google Sheets URL
3. Test the connection
4. Navigate to Dashboard to see your inventory overview

## 📊 Dashboard Features

### Main Dashboard - Inventory Focus
- **Total Overview**: Revenue, orders, pending items at a glance
- **Quantity Tracking**: Total ordered vs. received with completion percentage
- **Pending Alerts**: Highlighted pending orders count with direct navigation
- **Real-time Updates**: Auto-refresh every 30 seconds

### Pending Orders Page - Your Main Tool
- **Filtered View**: Only shows orders needing attention
- **Quick Stats**: No tracking, unverified, partial received breakdowns  
- **Smart Highlighting**: Visual indicators for different pending types
- **Search & Filter**: Find specific orders quickly

### All Orders Page
- **Complete Dataset**: Full order history with pagination
- **Advanced Sorting**: Click column headers to sort
- **Search**: Real-time search across all fields

## 🔧 Technical Details

### Backend (FastAPI)
- **Google Sheets Integration**: Direct connection using service account
- **Data Formatting**: Maintains your 19-column specification
- **Currency Handling**: Proper $X,XXX.XX formatting
- **Real-time Sync**: Live data from your existing sheets

### Frontend (React + TypeScript)
- **Modern UI**: Clean, responsive design with Tailwind CSS
- **Real-time Updates**: React Query for data fetching and caching
- **Performance**: Optimized for large datasets with pagination
- **Accessibility**: Screen reader friendly with proper ARIA labels

### Data Format Compatibility
Fully compatible with your existing Discord bot's 19-column format:
- Date, Time, Product, Price, Total, Commission
- Quantity, Profile, Proxy List, Order Number, Email
- Reference #, Posted Date, Tracking Number, Status
- QTY Received, Order ID, Created, Modified

## 🔐 Security & Permissions

### Google Sheets Access
- Uses service account authentication (credentials.json)
- Read-only by default for safety
- Requires Editor permissions on your sheets
- No data modification capabilities (use Discord bot for changes)

### Safe Implementation
- **Read-only Mode**: Dashboard only reads data, doesn't modify
- **No Risk**: Your existing Discord bot workflow unchanged
- **Backup Safe**: Original data and processes remain intact

## 📈 Solving Your Pain Points

### Before (Discord Bot Only)
- ❌ No visibility into overall inventory
- ❌ Manual checking for pending orders
- ❌ No completion rate tracking
- ❌ Limited analytics and insights

### After (Web Dashboard)
- ✅ **Real-time inventory overview** with pending counts
- ✅ **Live editable tables** - click any cell to edit Google Sheets directly
- ✅ **Instant synchronization** - changes appear immediately in both web and sheets
- ✅ **Dedicated pending orders page** with smart filtering
- ✅ **Completion rate tracking** and quantity analysis
- ✅ **Visual analytics** with charts and KPIs
- ✅ **WebSocket live updates** - see changes from Discord bot in real-time

## 🛣️ Development Phases

### ✅ Phase 1: Live Dashboard (Current)
- Google Sheets integration (read & write)
- **Live editable tables** - click to edit any cell
- **Real-time data sync** via WebSockets
- Inventory overview and analytics
- Pending orders tracking
- **Instant sheet synchronization**

### 🔄 Phase 2: Enhanced Features (Next)
- CSV upload processing through web interface
- Bulk edit operations
- Export capabilities
- Advanced validation rules

### 🔮 Phase 3: Advanced Integration (Future)
- Conflict resolution for simultaneous edits
- Audit trail and change history
- Mobile app
- Advanced reporting and forecasting

## 📁 Project Structure

```
ROMS/
├── backend/
│   ├── main.py              # FastAPI application
│   └── credentials.json     # Google service account (add this)
├── frontend/
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/          # Dashboard, Pending, All Orders, Settings
│   │   └── services/       # API integration
│   └── package.json
├── requirements.txt         # Python dependencies
└── README.md
```

## 🤝 Integration with Existing System

This dashboard **complements** your existing Discord bot:
- **Discord Bot**: Continues handling uploads, mark received, tracking, etc.
- **Web Dashboard**: Provides analytics and inventory visibility
- **Google Sheets**: Remains the single source of truth
- **No Conflicts**: Read-only access ensures no interference

## 📞 Support

For questions about the 19-column format, Discord bot integration, or Google Sheets setup, refer to your PROJECT_CONTEXT.md file which contains all the technical specifications and data formatting rules.

---

Built to solve your specific need for **inventory visibility and pending order tracking** while maintaining compatibility with your existing Discord bot workflow.
