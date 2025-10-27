#!/bin/bash

# Start ROMS V2 Backend
echo "🚀 Starting ROMS V2 Backend..."

# Navigate to backend-v2 directory
cd "$(dirname "$0")/backend-v2" || exit 1

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Copy .env.example to .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit backend-v2/.env with your actual configuration!"
fi

# Run the backend
echo "🎯 Starting backend on port 8001..."
python main.py

