#!/usr/bin/env bash
set -euo pipefail

echo "WorldMonitor AI — Bootstrap"

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
python -m spacy download en_core_web_sm

mkdir -p data
[ -f .env ] || cp .env.example .env

echo ""
echo "Bootstrap complete."
echo "Next steps:"
echo "  1. ollama serve"
echo "  2. ollama pull qwen2.5:7b"
echo "  3. python -m app.main"
echo "  4. Open http://localhost:8000"
