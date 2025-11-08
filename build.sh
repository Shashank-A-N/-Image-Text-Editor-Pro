#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Starting build process..."

# Install system dependencies
echo "Installing Tesseract OCR..."
apt-get update -y
apt-get install -y tesseract-ocr tesseract-ocr-eng

# Verify installation
echo "Verifying Tesseract installation..."
which tesseract || echo "Tesseract not in PATH"
tesseract --version || echo "Cannot run tesseract"
ls -la /usr/bin/tesseract || echo "Tesseract binary not found"

# Install Python dependencies
echo "Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Build complete!"
