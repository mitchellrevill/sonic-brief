#!/bin/bash

# Build script for Azure Web App deployment
echo "Starting deployment build process..."

# Install Python dependencies
echo "Installing Python dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "Build process completed successfully!"
