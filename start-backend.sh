#!/bin/bash

echo "🔧 Starting FastAPI Backend Only..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run ./start.sh first to set up."
    exit 1
fi

# Function to kill backend on exit
cleanup() {
    echo ""
    echo "🛑 Stopping backend..."
    pkill -f "python3 main.py" 2>/dev/null
    exit
}

# Set up trap to cleanup on script exit
trap cleanup SIGINT SIGTERM EXIT

# Start backend
echo "🔧 Starting FastAPI backend..."
cd backend
source ../venv/bin/activate

echo "✅ Virtual environment activated"
echo "🔍 Google Sheets credentials: $(ls -la credentials.json 2>/dev/null || echo 'Not found')"
echo ""

# Start with verbose logging
python3 main.py

echo ""
echo "Backend stopped."
