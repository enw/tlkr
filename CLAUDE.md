# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is a web application for processing images using multiple vision models through Ollama, with support for OCR, document processing, and interactive chat. It provides a user-friendly interface for DeepSeek OCR, LLaVA, and Moondream models.

## Key Files

- **server.py**: Main Flask web application with SQLite database for state persistence
- **ocr_data.db**: SQLite database storing interactions, chat messages, and cost tracking
- **uploads/**: Directory containing uploaded images
- **prompt_examples.md**: Contains prompt patterns for different OCR use cases
- **shell_examples.md**: Contains shell command examples showing how to invoke models via Ollama CLI
- **requirements.txt**: Python dependencies (Flask)

## Application Architecture

### Database Schema

The application uses SQLite with two main tables:

1. **interactions**: Stores OCR/vision processing results
   - id, filename, intent, output, model, input_tokens, output_tokens, estimated_cost, timestamp

2. **chat_messages**: Stores follow-up chat conversations about images
   - id, interaction_id, role, content, tokens, cost, timestamp

### Supported Models

- **deepseek-ocr**: Specialized for document OCR and conversion (best for documents)
- **llava**: General-purpose vision model for image understanding
- **moondream**: Fast, lightweight vision model for quick queries

### Features

1. **Image Upload & Processing**: Upload images/PDFs and process with selected model
2. **Multiple Models**: Choose between DeepSeek OCR, LLaVA, or Moondream
3. **Custom Intents**: Predefined intents or custom prompts with `<|grounding|>` support
4. **Cost Tracking**: Token usage and estimated costs displayed in UI and stored in database
5. **Chat Functionality**: Ask follow-up questions about processed images
6. **Persistent Storage**: All interactions and chat history saved to SQLite database

## Running the Application

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the server
python server.py
# or
./start.sh
```

The app runs on http://localhost:8080

## OCR Usage Patterns

The application supports several OCR prompt patterns:

1. **Document Conversion**: `<|grounding|>Convert the document to markdown.`
2. **General OCR**: `<|grounding|>OCR this image.`
3. **Layout-free OCR**: `Free OCR.` (no grounding token)
4. **Figure Parsing**: `<|grounding|>Parse the figure.`
5. **Image Description**: `Describe this image in detail.` (no grounding token)
6. **Custom Intent**: User-defined prompt with optional `<|grounding|>` prefix

The `<|grounding|>` token is automatically added for document-focused tasks unless explicitly present or the intent is general image description.

## Development Notes

- Flask runs in debug mode by default
- Database is automatically initialized on startup
- Token estimates use ~4 characters per token heuristic
- Cost estimates based on MODEL_COSTS configuration in server.py
- File uploads limited to 16MB
- Ollama processing timeout set to 120 seconds
