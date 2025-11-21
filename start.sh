#!/bin/bash
# Start script for DeepSeek OCR Web App

echo "Starting DeepSeek OCR Web App..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
if ! pip show Flask > /dev/null 2>&1; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "Error: Ollama is not installed. Please install it from https://ollama.ai"
    exit 1
fi

# Check if deepseek-ocr model is available
if ! ollama list | grep -q deepseek-ocr; then
    echo "Error: deepseek-ocr model not found."
    echo "Please run: ollama pull deepseek-ocr"
    exit 1
fi

# Start the server
python server.py
