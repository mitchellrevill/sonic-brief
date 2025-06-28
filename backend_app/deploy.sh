#!/bin/bash

# Build script for Azure Web App deployment
echo "Starting deployment build process..."

# Install Python dependencies
echo "Installing Python dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Start the app with Gunicorn and Uvicorn worker
echo "Starting the app with Gunicorn and Uvicorn worker..."
echo "Command: python3 -m gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000 --reload --log-level debug"
exec python3 -m gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000 --reload --log-level debug

echo "Deployment build process completed successfully!"
