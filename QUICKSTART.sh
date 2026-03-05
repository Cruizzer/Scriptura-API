#!/bin/bash
# Quick Start Guide for New Features

echo "=========================================="
echo "Scriptura API - New Features Quick Start"
echo "=========================================="
echo ""

# Activate virtual environment
echo "1. Activating virtual environment..."
source /uolstore/home/student_lnxhome01/sc22hd/Desktop/Scriptura-API/venv/bin/activate
cd /uolstore/home/student_lnxhome01/sc22hd/Desktop/Scriptura-API/scriptura_api

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
