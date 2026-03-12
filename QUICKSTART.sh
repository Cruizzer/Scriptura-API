#!/bin/bash
# Quick Start Guide for New Features

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/scriptura_api"
VENV_ACTIVATE="$SCRIPT_DIR/venv/bin/activate"

echo "=========================================="
echo "Scriptura API - New Features Quick Start"
echo "=========================================="
echo ""

# Activate virtual environment
echo "1. Activating virtual environment..."
if [ -f "$VENV_ACTIVATE" ]; then
	# shellcheck disable=SC1090
	source "$VENV_ACTIVATE"
else
	echo "   Warning: virtual environment not found at $VENV_ACTIVATE"
fi

cd "$PROJECT_DIR" || exit 1

# Run migrations (if not already done)
echo "2. Applying migrations..."
python manage.py migrate

# Run tests
echo "3. Running tests..."
python manage.py test
echo ""

# Start server
echo "4. Starting Django development server..."
echo "   Server will run at http://localhost:8000/"
echo "   API Documentation at http://localhost:8000/api/docs/"
echo "   OpenAPI Schema at http://localhost:8000/api/schema/"
echo ""
echo "5. In another terminal, run the demo:"
echo "   python API_DEMO.py"
echo ""
echo "=========================================="
python manage.py runserver
