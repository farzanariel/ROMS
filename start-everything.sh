#!/bin/bash

# Cleanup function to stop all processes
cleanup() {
    echo ""
    echo "🛑 Shutting down ROMS Dashboard..."
    echo "   Stopping backend..."
    pkill -f "python3 main.py" 2>/dev/null
    pkill -f "uvicorn" 2>/dev/null
    
    echo "   Stopping frontend..."
    pkill -f "npm run dev" 2>/dev/null
    pkill -f "vite" 2>/dev/null
    
    echo "   Stopping processes on ports..."
    for port in 3000 3001 5173 8000 8001 5000 4000; do
        lsof -ti:$port 2>/dev/null | xargs kill -9 2>/dev/null || true
    done
    
    echo "✅ All processes stopped!"
    exit 0
}

# Set trap to cleanup on script exit or interrupt
trap cleanup SIGINT SIGTERM EXIT

echo "🚀 Starting ROMS Dashboard - One Command Does Everything!"
echo "========================================================"

# Kill any existing processes - MORE COMPREHENSIVE CLEANUP
echo "🧹 Cleaning up any old processes..."
echo "   Stopping backend processes..."
pkill -f "python3 main.py" 2>/dev/null
pkill -f "uvicorn" 2>/dev/null
pkill -f "python.*main" 2>/dev/null

echo "   Stopping frontend processes..."
pkill -f "npm run dev" 2>/dev/null
pkill -f "vite" 2>/dev/null
pkill -f "node.*dev" 2>/dev/null

echo "   Stopping processes on common ports..."
# Kill processes on common dev ports
for port in 3000 3001 5173 8000 8001 5000 4000; do
  lsof -ti:$port 2>/dev/null | xargs kill -9 2>/dev/null || true
done

# Wait a moment for cleanup
sleep 3

# Start backend in background
echo "🐍 Starting Python backend..."
cd backend
source ../venv/bin/activate
python3 main.py &
BACKEND_PID=$!
cd ..

# Wait for backend to be ready
echo "⏳ Waiting for backend to start..."
sleep 8

# Test backend
echo "🔍 Testing backend..."
if curl -s http://localhost:8000/api/health > /dev/null; then
    echo "✅ Backend is running!"
else
    echo "❌ Backend failed to start"
    exit 1
fi

# Start frontend
echo "⚛️  Starting React frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "🎉 SUCCESS! Your dashboard is starting up..."
echo ""
echo "📱 Frontend: http://localhost:3000 (or 5173)"
echo "🔧 Backend: http://localhost:8000"
echo ""
echo "⏰ Give it 10-15 seconds to fully load..."
echo ""
echo "�� To stop everything:"
echo "   • Press Ctrl+C (this script will clean up automatically)"
echo "   • Or run: ./start-everything.sh stop"
echo "   • Or manually: pkill -f 'uvicorn\|vite\|npm'"
echo ""

# Check if user wants to stop
if [ "$1" = "stop" ]; then
    echo "🛑 Stopping ROMS Dashboard..."
    cleanup
fi

# Keep script running and show logs
wait
