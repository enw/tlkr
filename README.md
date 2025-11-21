# DeepSeek OCR Web App

A simple web application for running DeepSeek OCR on uploaded images and PDFs using Ollama.

## Features

- 📤 Upload images or PDF files
- 🎯 Choose from predefined OCR intents or create custom ones
- 🖼️ View results in a table with image thumbnails and OCR output
- 💾 Results persist during the session
- 🎨 Modern, responsive UI

## Prerequisites

1. **Ollama**: Install from [ollama.ai](https://ollama.ai)
2. **DeepSeek OCR Model**: Pull the model with:
   ```bash
   ollama pull deepseek-ocr
   ```
3. **Python 3.7+**: Required for running the Flask server

## Quick Start

The easiest way to start the application:

```bash
./start.sh
```

This script will:
- Create a virtual environment if it doesn't exist
- Install dependencies
- Check for Ollama and deepseek-ocr model
- Start the server on port 8080

Then open your browser to: **http://localhost:8080**

## Manual Installation

1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Manual Usage

1. Activate the virtual environment:
   ```bash
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Start the server:
   ```bash
   python server.py
   ```

3. Open your browser to:
   ```
   http://localhost:8080
   ```

4. Upload an image or PDF, select an intent (or create a custom one), and click "Process with DeepSeek OCR"

## Predefined Intents

- **Document to Markdown**: Convert documents to markdown format
- **General OCR**: Standard OCR for text extraction
- **Free OCR**: OCR without layout preservation
- **Parse Figure**: Extract information from figures/charts
- **Detailed Description**: Generate detailed image descriptions
- **Custom Intent**: Define your own prompt

## Custom Intents

When using custom intents, you can optionally include the `<|grounding|>` prefix for document-focused tasks:

```
<|grounding|>Extract all table data from this document.
```

For general image tasks, the prefix is not needed:
```
Describe this image in detail.
```

## File Storage

Uploaded files are stored in the `uploads/` directory. Results are kept in memory during the server session.

## Technical Details

- Built with Flask for the backend
- Single-page application with vanilla JavaScript
- Direct integration with Ollama CLI
- No database required (in-memory storage)
