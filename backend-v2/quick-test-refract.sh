#!/bin/bash

echo "=================================================="
echo "🚀 ROMS V2 - Quick Refract Webhook Test"
echo "=================================================="
echo ""

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: Please run this from the backend-v2 directory"
    echo "   cd backend-v2"
    echo "   ./quick-test-refract.sh"
    exit 1
fi

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# Check if backend is already running
if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null ; then
    echo "✅ Backend already running on port 8001"
else
    echo "🚀 Starting backend server..."
    python main.py > backend.log 2>&1 &
    BACKEND_PID=$!
    echo "   Backend PID: $BACKEND_PID"
    
    # Wait for backend to start
    echo "⏳ Waiting for backend to start..."
    sleep 3
    
    # Check if it's running
    if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null ; then
        echo "✅ Backend started successfully"
    else
        echo "❌ Backend failed to start. Check backend.log for errors:"
        tail -n 20 backend.log
        exit 1
    fi
fi

echo ""
echo "=================================================="
echo "🧪 Running Refract Webhook Test"
echo "=================================================="
echo ""

# Run the test
python test_refract_webhook.py

echo ""
echo "=================================================="
echo "📊 Next Steps"
echo "=================================================="
echo ""
echo "1. Configure Refract with webhook URL:"
echo "   http://localhost:8001/api/v2/webhooks/orders"
echo ""
echo "2. View orders in database:"
echo "   sqlite3 roms_v2.db"
echo "   SELECT * FROM orders;"
echo ""
echo "3. View webhook logs:"
echo "   curl http://localhost:8001/api/v2/webhooks/logs"
echo ""
echo "4. View API documentation:"
echo "   open http://localhost:8001/docs"
echo ""
echo "5. For production, use ngrok:"
echo "   ngrok http 8001"
echo ""
echo "=================================================="

