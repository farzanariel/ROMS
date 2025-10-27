#!/bin/bash

# 🚀 ARIEL'S DASHBOARD - QUICK START
# Just run: ./quick-start.sh

clear
echo "🎯 Starting Ariel's Order Management Dashboard..."
echo ""

# Kill any existing processes
pkill -f "python3 main.py" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    pkill -f "python3 main.py" 2>/dev/null
    pkill -f "npm run dev" 2>/dev/null
    exit
}
trap cleanup SIGINT SIGTERM

# Start backend
echo "🔧 Starting backend server..."
cd backend
source ../venv/bin/activate
python3 main.py &
BACKEND_PID=$!
cd ..

# Wait and test backend
sleep 3
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "✅ Backend running on http://localhost:8000"
else
    echo "❌ Backend failed to start"
    exit 1
fi

# Start frontend
echo "🎨 Starting frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for frontend
sleep 5

# Success message
echo ""
echo "🎉 Dashboard Ready!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Open: http://localhost:3000"
echo "⚙️  Settings: http://localhost:3000/settings"
echo "📋 Pending: http://localhost:3000/pending"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "👋 Welcome Ariel! Your dashboard is ready."
echo "💡 Add your Google Sheet URL in Settings to get started"
echo ""
echo "Press Ctrl+C to stop"

# Wait for processes
wait
