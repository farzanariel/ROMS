#!/bin/bash

echo "🚀 Starting Order Management Dashboard..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Setting up..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    echo "✅ Virtual environment found"
fi

# Function to kill background processes on exit
cleanup() {
    echo ""
    echo "🛑 Stopping servers..."
    pkill -f "python3 main.py" 2>/dev/null
    pkill -f "npm run dev" 2>/dev/null
    exit
}

# Set up trap to cleanup on script exit
trap cleanup SIGINT SIGTERM EXIT

# Start backend
echo "🔧 Starting FastAPI backend..."
cd backend
source ../venv/bin/activate
python3 main.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start and test connection
echo "⏳ Waiting for backend to start..."
sleep 5

# Test backend connection
echo "🔍 Testing backend connection..."
if curl -s http://localhost:8000/api/health > /dev/null; then
    echo "✅ Backend is running"
else
    echo "❌ Backend failed to start"
    exit 1
fi

# Check if node_modules exists in frontend
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

# Start frontend
echo "🎨 Starting React frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "🎉 Dashboard is ready!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Quick start guide:"
echo "1. Open http://localhost:3000 in your browser"
echo "2. Enter your Google Sheets URL in settings"
echo "3. View your dashboard and pending orders"
echo ""
echo "💡 Tip: Your data will automatically sync every 2 minutes"
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait for background processes
wait
