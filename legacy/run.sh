#!/usr/bin/env bash
set -e

# ==============================================================================
# RISKWISE AI: Enterprise Risk Copilot & Autonomous Action Agent Launch Script
# ==============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "======================================================================"
echo "🛡️  RISKWISE AI — Enterprise Risk Copilot & Autonomous Action Engine"
echo "======================================================================"
echo "Directory: $PROJECT_DIR"

# Activate Virtual Environment
if [ -d "$PROJECT_DIR/.venv" ]; then
    source "$PROJECT_DIR/.venv/bin/activate"
    echo "✓ Activated Python virtual environment (.venv)"
else
    echo "❌ Error: Virtual environment .venv not found in $PROJECT_DIR"
    exit 1
fi

export PYTHONPATH="$PROJECT_DIR/backend:$PYTHONPATH"

# Run Test Suite to Ensure Platform Health
echo "Running automated verification test suite..."
python backend/test_suite.py
echo "✓ All 17 unit & integration tests passed successfully!"

echo ""
echo "Starting FastAPI Server & UI Dashboard on http://localhost:8000 ..."
echo "Press Ctrl+C to stop the server."
echo "======================================================================"

exec uvicorn api_server:app --app-dir "$PROJECT_DIR/backend" --host 0.0.0.0 --port 8000 --reload
