# Setup script for RAG Workflow Application (PowerShell)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "RAG Workflow Application Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Error: Python is not installed. Please install Python 3.9 or higher." -ForegroundColor Red
    exit 1
}

# Check if Docker is installed
try {
    $dockerVersion = docker --version 2>&1
    Write-Host "Found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "Warning: Docker is not installed. You'll need Docker to run OpenSearch." -ForegroundColor Yellow
    Write-Host "Please install Docker Desktop to continue." -ForegroundColor Yellow
    exit 1
}

# Navigate to backend directory
$backendPath = Join-Path $PSScriptRoot "..\backend"
Set-Location $backendPath

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Install dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip
pip install -r requirements.txt

# Create .env file from example if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file from .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host ""
    Write-Host "IMPORTANT: Please edit backend\.env and add your OpenAI API key!" -ForegroundColor Red
    Write-Host ""
} else {
    Write-Host ".env file already exists, skipping..." -ForegroundColor Green
}

# Navigate to docker directory
$dockerPath = Join-Path $PSScriptRoot "..\docker"
Set-Location $dockerPath

# Stop and remove existing containers if they exist
Write-Host "Checking for existing Docker containers..." -ForegroundColor Yellow
try {
    docker-compose down 2>&1 | Out-Null
} catch {
    # Ignore errors if containers don't exist
}

# Start OpenSearch
Write-Host "Starting OpenSearch with Docker Compose..." -ForegroundColor Yellow
docker-compose up -d

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Edit backend\.env and add your OpenAI API key"
Write-Host "2. Place your DICOM files in the data\ folder"
Write-Host "3. Create your JSON metadata file (see README.md for format)"
Write-Host "4. Run: python scripts\index_data.py"
Write-Host "5. Start the backend: cd backend && uvicorn app.main:app --reload"
Write-Host "6. Open frontend\web\index.html in your browser"
Write-Host ""

