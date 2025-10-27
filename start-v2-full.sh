#!/bin/bash

echo "=================================================="
echo "🚀 Starting ROMS V2 (Backend + Frontend)"
echo "=================================================="
echo ""

# Kill any existing processes on the ports
echo "🧹 Cleaning up existing processes..."
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
lsof -ti:3001 | xargs kill -9 2>/dev/null || true
sleep 1

# Start Backend V2
echo ""
echo "📡 Starting Backend V2 (port 8001)..."
cd backend-v2
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8001 --reload > backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 4

# Check if backend is running
if curl -s http://localhost:8001/health > /dev/null; then
    echo "✅ Backend is running on http://localhost:8001"
else
    echo "❌ Backend failed to start. Check backend-v2/backend.log"
    exit 1
fi

# Start Frontend V2
echo ""
echo "🎨 Starting Frontend V2 (port 3001)..."
cd ../frontend-v2

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi

npm run dev > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

echo ""
echo "=================================================="
echo "✅ ROMS V2 is Running!"
echo "=================================================="
echo ""
echo "🌐 Frontend: http://localhost:3001"
echo "📡 Backend API: http://localhost:8001"
echo "📚 API Docs: http://localhost:8001/docs"
echo ""
echo "🪝 Webhook URL: http://localhost:8001/api/v2/webhooks/orders"
echo ""
echo "To stop:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "Logs:"
echo "  Backend: tail -f backend-v2/backend.log"
echo "  Frontend: tail -f frontend-v2/frontend.log"
echo ""
echo "=================================================="
echo "🎉 Open http://localhost:3001 to see your orders!"
echo "=================================================="

