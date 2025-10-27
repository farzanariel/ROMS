#!/bin/bash

# Start both ROMS V1 and V2 systems simultaneously
echo "🚀 Starting ROMS V1 & V2 Systems..."

# Function to handle cleanup
cleanup() {
    echo ""
    echo "🛑 Shutting down all services..."
    kill $(jobs -p) 2>/dev/null
    exit 0
}

# Trap Ctrl+C and call cleanup
trap cleanup SIGINT SIGTERM

# Start V1 Backend (port 8000)
echo "📡 Starting V1 Backend on port 8000..."
cd backend
source ../venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000 &
V1_BACKEND_PID=$!
cd ..

# Wait a bit for V1 to start
sleep 2

# Start V2 Backend (port 8001)
echo "📡 Starting V2 Backend on port 8001..."
cd backend-v2
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "⚠️  V2 virtual environment not found. Run start-v2.sh first!"
fi
python main.py &
V2_BACKEND_PID=$!
cd ..

# Wait a bit for backends to start
sleep 2

# Start V1 Frontend (port 3000)
echo "🎨 Starting V1 Frontend on port 3000..."
cd frontend
npm run dev -- --port 3000 &
V1_FRONTEND_PID=$!
cd ..

echo ""
echo "✅ All systems started!"
echo ""
echo "📊 Access Points:"
echo "  • V1 Frontend:  http://localhost:3000"
echo "  • V1 Backend:   http://localhost:8000"
echo "  • V1 API Docs:  http://localhost:8000/docs"
echo "  • V2 Backend:   http://localhost:8001"
echo "  • V2 API Docs:  http://localhost:8001/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for all background processes
wait

