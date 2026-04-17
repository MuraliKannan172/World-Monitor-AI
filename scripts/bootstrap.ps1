param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "WorldMonitor AI — Bootstrap" -ForegroundColor Cyan

# Create and activate venv
python -m venv .venv
& ".\.venv\Scripts\Activate.ps1"

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Create data directory
if (-not (Test-Path "data")) { New-Item -ItemType Directory -Path "data" | Out-Null }

# Copy env example
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }

Write-Host ""
Write-Host "Bootstrap complete." -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Start Ollama:       ollama serve" -ForegroundColor White
Write-Host "  2. Pull a model:       ollama pull qwen2.5:7b" -ForegroundColor White
Write-Host "  3. Run the app:        python -m app.main" -ForegroundColor White
Write-Host "  4. Open browser:       http://localhost:8000" -ForegroundColor White
