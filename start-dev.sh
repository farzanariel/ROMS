#!/bin/bash

echo "🚀 Starting Order Management Dashboard in development mode..."

# Function to kill background processes on exit
cleanup() {
    echo "🛑 Stopping servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit
}

# Set up trap to cleanup on script exit
trap cleanup SIGINT SIGTERM EXIT

# Start backend
echo "🔧 Starting FastAPI backend..."
cd backend
# Activate virtual environment and start backend
source ../venv/bin/activate
python3 main.py &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 3

# Start frontend
echo "🎨 Starting React frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "🎉 Dashboard is starting up!"
echo "📊 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo ""
echo "📋 Quick start:"
echo "1. Visit http://localhost:3000/settings"
echo "2. Enter your Google Sheets URL"
echo "3. Go to http://localhost:3000/pending to see your inventory overview"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for background processes
wait
