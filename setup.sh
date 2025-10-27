#!/bin/bash

echo "🚀 Setting up Order Management Dashboard..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed. Please install Python 3.9+ first."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not installed. Please install Node.js 16+ first."
    exit 1
fi

echo "✅ Python and Node.js found"

# Set up Python virtual environment
echo "📦 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Set up frontend dependencies
echo "📦 Installing frontend dependencies..."
cd frontend
npm install
cd ..

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📄 Creating .env file..."
    cp .env.example .env
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Add your Google Service Account credentials.json to the backend directory"
echo "2. Share your Google Sheet with the service account email (Editor access)"
echo "3. Start the backend: cd backend && python main.py"
echo "4. In a new terminal, start the frontend: cd frontend && npm run dev"
echo "5. Visit http://localhost:3000 and go to Settings to configure your sheet URL"
echo ""
echo "🔗 Your main inventory dashboard will be at: http://localhost:3000"
echo "📊 Pending orders view (your main tool): http://localhost:3000/pending"
echo ""
