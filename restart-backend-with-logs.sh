#!/bin/bash
# Stop existing backend
pkill -f "python.*main.py"
sleep 2

# Activate venv and start backend with logs
cd /Users/farzan/Documents/Projects/ROMS
source venv/bin/activate
cd backend
echo "Starting backend with logging..."
python3 main.py 2>&1 | tee backend.log &
echo "Backend started! Logs are being written to backend/backend.log"
echo "You can view logs with: tail -f backend/backend.log"
