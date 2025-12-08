#!/bin/bash

# Setup script for RAG Workflow Application

echo "=========================================="
echo "RAG Workflow Application Setup"
echo "=========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Warning: Docker is not installed. You'll need Docker to run OpenSearch."
    echo "Please install Docker and Docker Compose to continue."
    exit 1
fi

# Navigate to backend directory
cd "$(dirname "$0")/../backend" || exit 1

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file from example if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo ""
    echo "IMPORTANT: Please edit backend/.env and add your OpenAI API key!"
    echo ""
else
    echo ".env file already exists, skipping..."
fi

# Navigate to docker directory
cd ../docker || exit 1

# Stop and remove existing containers if they exist
echo "Checking for existing Docker containers..."
docker-compose down 2>/dev/null || true

# Start OpenSearch
echo "Starting OpenSearch with Docker Compose..."
docker-compose up -d

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit backend/.env and add your OpenAI API key"
echo "2. Place your DICOM files in the data/ folder"
echo "3. Create your JSON metadata file (see README.md for format)"
echo "4. Run: python scripts/index_data.py"
echo "5. Start the backend: cd backend && uvicorn app.main:app --reload"
echo "6. Open frontend/web/index.html in your browser"
echo ""

