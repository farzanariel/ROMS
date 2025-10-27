# Frontend V2 - Navigation & Pages

## ✅ Features

### 🎨 Retractable Sidebar
- **Desktop**: Collapsible sidebar (wide ↔ narrow)
- **Mobile**: Hamburger menu with slide-out drawer
- **Persistent**: Remembers your preference
- **Smooth**: CSS transitions for all interactions

### 📱 Responsive Design
- **Desktop**: Full sidebar with icons and labels
- **Tablet**: Collapsible sidebar
- **Mobile**: Hamburger menu overlay

---

## 📄 Pages

### 1. All Orders
**Route**: Default page

**Features:**
- ✅ Real-time order table
- ✅ 15 columns with all order data
- ✅ Search and filter
- ✅ Pagination
- ✅ Auto-refresh every 5 seconds
- ✅ WebSocket live updates
- ✅ Compact row design

### 2. Analytics
**Route**: `/analytics`

**Status**: Coming Soon

**Planned Features:**
- Revenue tracking charts
- Order trend analysis
- Performance metrics
- Product insights

### 3. Settings
**Route**: `/settings`

**Tabs:**

#### General Settings
- System information
- Version info
- Environment details
- User preferences
  - Auto-refresh toggle
  - WebSocket status display
  - Desktop notifications

#### Debugging
- **Webhook Queue Stats**
  - Current queue size
  - Peak queue size
  - Total received/processed
  - Success rate
  - Worker status
  - Average processing time
  - Failed message count

- **Recent Webhook Logs**
  - Last 10 webhooks
  - Status codes
  - Processing status
  - Timestamps
  - Error messages

- **Actions**
  - Refresh data button
  - Real-time monitoring

#### API Info
- **Base URLs**
  - REST API endpoint
  - WebSocket endpoint
  - Webhook URL (for Refract)

- **Available Endpoints**
  - Orders API
  - Webhooks API
  - Queue management
  - System endpoints

- **Quick Links**
  - Interactive API docs
  - Health check
  - Direct links to endpoints

---

## 🎯 Navigation

### Sidebar Menu Items

| Icon | Name | Page | Status |
|---|---|---|---|
| 🏠 | All Orders | Orders table | ✅ Active |
| 📊 | Analytics | Charts & stats | 🚧 Coming Soon |
| ⚙️ | Settings | Configuration | ✅ Active |

### Keyboard Shortcuts
_(Not yet implemented)_
- `1` - All Orders
- `2` - Analytics
- `3` - Settings
- `[` - Collapse sidebar
- `]` - Expand sidebar

---

## 🎨 Sidebar States

### Desktop

**Expanded (Default)**
```
┌─────────────────────┐
│ 🅁 ROMS V2         ◀│
│   Order Management  │
├─────────────────────┤
│ 🏠 All Orders       │ ← Active
│ 📊 Analytics        │
│ ⚙️  Settings        │
│                     │
│ ● System Online     │
│   V2.0.0            │
└─────────────────────┘
```

**Collapsed**
```
┌──┐
│ 🅁│
│◀ │
├──┤
│🏠│ ← Active
│📊│
│⚙️ │
│  │
│● │
└──┘
```

### Mobile

**Closed**
```
┌─┐
│☰│ ← Tap to open
└─┘
```

**Open (Overlay)**
```
╔═════════════════════╗
║ 🅁 ROMS V2         ✕║
║   Order Management  ║
╠═════════════════════╣
║ 🏠 All Orders       ║
║ 📊 Analytics        ║
║ ⚙️  Settings        ║
║                     ║
║ ● System Online     ║
║   V2.0.0            ║
╚═════════════════════╝
```

---

## 🛠️ Component Structure

```
src/
├── components/
│   └── Sidebar.tsx          ← Main navigation
│
├── pages/
│   ├── AllOrders.tsx        ← Order table
│   ├── Analytics.tsx        ← Coming soon
│   └── Settings.tsx         ← Settings with tabs
│
└── App.tsx                  ← Routing logic
```

---

## 🎯 Usage

### Starting the App

```bash
cd frontend-v2
npm run dev
```

**Opens:** http://localhost:3001

**Default Page:** All Orders

### Navigation

1. **Desktop:**
   - Click menu items in sidebar
   - Click collapse button (◀/▶) to toggle size

2. **Mobile:**
   - Tap hamburger menu (☰)
   - Select page
   - Tap overlay or ✕ to close

---

## 🎨 Customization

### Change Sidebar Width

Edit `src/components/Sidebar.tsx`:

```tsx
// Expanded width
className="lg:w-64"  // Change to lg:w-72, lg:w-80, etc.

// Collapsed width
className="lg:w-20"  // Change to lg:w-16, lg:w-24, etc.
```

### Add New Page

1. **Create page component:**
```tsx
// src/pages/MyPage.tsx
export default function MyPage() {
  return <div>My Page Content</div>
}
```

2. **Add to sidebar:**
```tsx
// src/components/Sidebar.tsx
const navigation = [
  { name: 'My Page', icon: MyIcon, id: 'mypage' },
]
```

3. **Add routing:**
```tsx
// src/App.tsx
import MyPage from './pages/MyPage'

const renderPage = () => {
  switch (currentPage) {
    case 'mypage':
      return <MyPage />
  }
}
```

### Change Colors

Edit Tailwind classes in components:

- **Active state**: `bg-blue-50 text-blue-600`
- **Hover state**: `hover:bg-gray-50`
- **Sidebar background**: `bg-white`
- **Border**: `border-gray-200`

---

## 📊 Settings Page Features

### Real-Time Debugging

The debugging tab automatically fetches:
- Queue statistics from `/api/v2/webhooks/queue/stats`
- Recent logs from `/api/v2/webhooks/logs`

**Refresh:** Click "Refresh Data" button

### Queue Health Monitoring

Status indicator shows:
- 🟢 **Healthy**: Success rate > 95%
- 🟡 **Degraded**: Success rate < 95%

### Metrics Displayed

- Queue size (current)
- Peak queue size (max reached)
- Total received (all-time)
- Total processed (all-time)
- Success rate (percentage)
- Workers running (active/total)
- Average processing time (milliseconds)
- Failed messages (dead letter queue)

---

## 🎉 Features Summary

✅ **Retractable sidebar** - Collapse/expand on desktop
✅ **Mobile responsive** - Hamburger menu on mobile
✅ **All Orders page** - Full order table with auto-refresh
✅ **Settings page** - 3 tabs (General, Debugging, API)
✅ **Real-time debugging** - Live queue stats and logs
✅ **API documentation** - All endpoints listed
✅ **System status** - Live indicator in sidebar
✅ **Smooth transitions** - Professional animations

---

## 🚀 Next Steps

**Ready to use! Just:**

1. Start backend: `cd backend-v2 && python main.py`
2. Start frontend: `cd frontend-v2 && npm run dev`
3. Open: http://localhost:3001
4. Click sidebar items to navigate!

---

**Enjoy your professional navigation system! 🎊**

