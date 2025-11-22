#!/usr/bin/env python3
"""
DeepSeek OCR Web Application
Simple Flask server for uploading images and running OCR via Ollama
"""

from flask import Flask, request, jsonify, send_from_directory, render_template_string
import subprocess
import os
import base64
from pathlib import Path
import json
import sqlite3
from datetime import datetime
from contextlib import contextmanager

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = Path('uploads')
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
DB_PATH = 'ocr_data.db'

# Model cost per 1K tokens (approximate pricing for local models - using token estimates)
# For local models, we'll estimate based on model size and time
MODEL_COSTS = {
    'deepseek-ocr': {'input': 0.0001, 'output': 0.0001},  # Estimated cost per 1K tokens
    'llava': {'input': 0.0001, 'output': 0.0001},
    'moondream': {'input': 0.00005, 'output': 0.00005}  # Smaller model, lower cost estimate
}

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initialize the database with required tables"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Main interactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                intent TEXT NOT NULL,
                output TEXT NOT NULL,
                model TEXT DEFAULT 'deepseek-ocr',
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                estimated_cost REAL DEFAULT 0.0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Chat history table for follow-up questions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interaction_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tokens INTEGER DEFAULT 0,
                cost REAL DEFAULT 0.0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (interaction_id) REFERENCES interactions(id)
            )
        ''')

        conn.commit()

# Initialize database on startup
init_db()

def estimate_tokens(text):
    """Rough estimate of tokens (approximately 1 token per 4 characters)"""
    return len(text) // 4

def calculate_cost(input_tokens, output_tokens, model='deepseek-ocr'):
    """Calculate estimated cost based on token usage"""
    costs = MODEL_COSTS.get(model, MODEL_COSTS['deepseek-ocr'])
    input_cost = (input_tokens / 1000) * costs['input']
    output_cost = (output_tokens / 1000) * costs['output']
    return input_cost + output_cost

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DeepSeek OCR Web App</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        h1 {
            color: white;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }

        .upload-section {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            font-weight: 600;
            margin-bottom: 8px;
            color: #333;
        }

        input[type="file"] {
            display: block;
            width: 100%;
            padding: 12px;
            border: 2px dashed #667eea;
            border-radius: 8px;
            background: #f8f9ff;
            cursor: pointer;
            transition: all 0.3s;
        }

        input[type="file"]:hover {
            border-color: #764ba2;
            background: #f0f1ff;
        }

        input[type="text"], select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }

        input[type="text"]:focus, select:focus {
            outline: none;
            border-color: #667eea;
        }

        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 14px 32px;
            font-size: 16px;
            font-weight: 600;
            border-radius: 8px;
            cursor: pointer;
            width: 100%;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }

        button:active {
            transform: translateY(0);
        }

        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .results-section {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }

        .results-section h2 {
            color: #333;
            margin-bottom: 20px;
        }

        .results-table {
            width: 100%;
            border-collapse: collapse;
        }

        .results-table th {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }

        .results-table td {
            padding: 15px;
            border-bottom: 1px solid #e0e0e0;
            vertical-align: top;
        }

        .results-table tr:last-child td {
            border-bottom: none;
        }

        .results-table tr:hover {
            background: #f8f9ff;
        }

        .thumbnail {
            max-width: 200px;
            max-height: 200px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .output-text {
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            line-height: 1.6;
            color: #333;
            background: #f8f9ff;
            padding: 12px;
            border-radius: 6px;
            max-height: 400px;
            overflow-y: auto;
        }

        .loading {
            text-align: center;
            padding: 20px;
            color: #667eea;
            font-weight: 600;
        }

        .error {
            background: #fee;
            color: #c33;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            border-left: 4px solid #c33;
        }

        .success {
            background: #efe;
            color: #3a3;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            border-left: 4px solid #3a3;
        }

        .intent-info {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
            font-style: italic;
        }

        .no-results {
            text-align: center;
            color: #999;
            padding: 40px;
            font-style: italic;
        }

        .stats-section {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }

        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }

        .stat-value {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }

        .chat-section {
            margin-top: 20px;
            padding: 15px;
            background: #f8f9ff;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
        }

        .chat-messages {
            max-height: 300px;
            overflow-y: auto;
            margin-bottom: 15px;
        }

        .chat-message {
            margin-bottom: 10px;
            padding: 10px;
            border-radius: 6px;
        }

        .chat-message.user {
            background: #667eea;
            color: white;
            margin-left: 40px;
        }

        .chat-message.assistant {
            background: white;
            color: #333;
            margin-right: 40px;
            border: 1px solid #e0e0e0;
        }

        .chat-input-group {
            display: flex;
            gap: 10px;
        }

        .chat-input-group input {
            flex: 1;
        }

        .chat-input-group button {
            width: auto;
            padding: 10px 20px;
        }

        .chat-toggle {
            background: #667eea;
            color: white;
            border: none;
            padding: 8px 16px;
            font-size: 14px;
            border-radius: 6px;
            cursor: pointer;
            margin-top: 10px;
        }

        .chat-toggle:hover {
            background: #5568d3;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 DeepSeek OCR Web App</h1>

        <div class="upload-section">
            <form id="uploadForm">
                <div class="form-group">
                    <label for="fileInput">Select Image or PDF:</label>
                    <input type="file" id="fileInput" name="file" accept="image/*,.pdf" required>
                </div>

                <div class="form-group">
                    <label for="modelSelect">Model:</label>
                    <select id="modelSelect" name="model">
                        <option value="deepseek-ocr">DeepSeek OCR (Best for documents)</option>
                        <option value="llava">LLaVA (General purpose)</option>
                        <option value="moondream">Moondream (Fast & lightweight)</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="intentSelect">OCR Intent:</label>
                    <select id="intentSelect" name="intent">
                        <option value="Convert the document to markdown.">Document to Markdown</option>
                        <option value="OCR this image.">General OCR</option>
                        <option value="Free OCR.">Free OCR (no layout)</option>
                        <option value="Parse the figure.">Parse Figure</option>
                        <option value="Describe this image in detail.">Detailed Description</option>
                        <option value="custom">Custom Intent...</option>
                    </select>
                </div>

                <div class="form-group" id="customIntentGroup" style="display: none;">
                    <label for="customIntent">Custom Intent:</label>
                    <input type="text" id="customIntent" name="customIntent" placeholder="Enter custom intent...">
                    <div class="intent-info">Use &lt;|grounding|&gt; prefix for document-focused tasks</div>
                </div>

                <button type="submit" id="submitBtn">Process Image</button>
            </form>

            <div id="message"></div>
        </div>

        <div class="stats-section">
            <h2>Usage Statistics</h2>
            <div class="stats-grid" id="statsContainer">
                <div class="stat-card">
                    <div class="stat-value" id="totalInteractions">0</div>
                    <div class="stat-label">Total Interactions</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="totalTokens">0</div>
                    <div class="stat-label">Total Tokens</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="totalCost">$0.00</div>
                    <div class="stat-label">Estimated Cost</div>
                </div>
            </div>
        </div>

        <div class="results-section">
            <h2>Results</h2>
            <div id="resultsContainer">
                <div class="no-results">No results yet. Upload an image to get started!</div>
            </div>
        </div>
    </div>

    <script>
        const form = document.getElementById('uploadForm');
        const submitBtn = document.getElementById('submitBtn');
        const messageDiv = document.getElementById('message');
        const resultsContainer = document.getElementById('resultsContainer');
        const intentSelect = document.getElementById('intentSelect');
        const customIntentGroup = document.getElementById('customIntentGroup');
        const customIntentInput = document.getElementById('customIntent');

        // Show/hide custom intent input
        intentSelect.addEventListener('change', function() {
            if (this.value === 'custom') {
                customIntentGroup.style.display = 'block';
                customIntentInput.required = true;
            } else {
                customIntentGroup.style.display = 'none';
                customIntentInput.required = false;
            }
        });

        // Load results and stats on page load
        loadResults();
        loadStats();

        form.addEventListener('submit', async function(e) {
            e.preventDefault();

            const formData = new FormData();
            const fileInput = document.getElementById('fileInput');
            const modelSelect = document.getElementById('modelSelect');
            const file = fileInput.files[0];

            if (!file) {
                showMessage('Please select a file', 'error');
                return;
            }

            let intent;
            if (intentSelect.value === 'custom') {
                intent = customIntentInput.value.trim();
                if (!intent) {
                    showMessage('Please enter a custom intent', 'error');
                    return;
                }
            } else {
                intent = intentSelect.value;
            }

            formData.append('file', file);
            formData.append('intent', intent);
            formData.append('model', modelSelect.value);

            submitBtn.disabled = true;
            submitBtn.textContent = 'Processing...';
            showMessage('Uploading and processing image...', 'loading');

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (response.ok) {
                    showMessage('Processing complete!', 'success');
                    form.reset();
                    loadResults();
                    loadStats();
                } else {
                    showMessage('Error: ' + data.error, 'error');
                }
            } catch (error) {
                showMessage('Error: ' + error.message, 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Process Image';
            }
        });

        function showMessage(msg, type) {
            messageDiv.innerHTML = `<div class="${type}">${msg}</div>`;
            if (type === 'success' || type === 'error') {
                setTimeout(() => {
                    messageDiv.innerHTML = '';
                }, 5000);
            }
        }

        async function loadResults() {
            try {
                const response = await fetch('/results');
                const data = await response.json();

                if (data.results && data.results.length > 0) {
                    displayResults(data.results);
                } else {
                    resultsContainer.innerHTML = '<div class="no-results">No results yet. Upload an image to get started!</div>';
                }
            } catch (error) {
                console.error('Error loading results:', error);
            }
        }

        function displayResults(results) {
            const table = document.createElement('table');
            table.className = 'results-table';

            table.innerHTML = `
                <thead>
                    <tr>
                        <th style="width: 250px;">Image</th>
                        <th>OCR Output</th>
                        <th style="width: 150px;">Cost</th>
                    </tr>
                </thead>
                <tbody>
                    ${results.map(result => `
                        <tr>
                            <td>
                                <img src="/uploads/${result.filename}" alt="Uploaded image" class="thumbnail">
                                <div style="margin-top: 8px; font-size: 12px; color: #666;">
                                    <strong>Intent:</strong> ${escapeHtml(result.intent)}<br>
                                    <strong>Model:</strong> ${escapeHtml(result.model || 'deepseek-ocr')}<br>
                                    <strong>Date:</strong> ${new Date(result.timestamp).toLocaleString()}
                                </div>
                            </td>
                            <td colspan="2">
                                <div class="output-text">${escapeHtml(result.output)}</div>
                                <button class="chat-toggle" onclick="toggleChat(${result.id})">💬 Chat about this image</button>
                                <div id="chat-${result.id}" class="chat-section" style="display: none;">
                                    <div class="chat-messages" id="chat-messages-${result.id}">
                                        <div style="color: #666; font-style: italic; text-align: center;">No chat history yet. Ask a question about this image!</div>
                                    </div>
                                    <div class="chat-input-group">
                                        <input type="text" id="chat-input-${result.id}" placeholder="Ask a question about this image..." onkeypress="if(event.key==='Enter') sendChat(${result.id})">
                                        <button onclick="sendChat(${result.id})">Send</button>
                                    </div>
                                    <div style="margin-top: 10px; font-size: 12px; color: #666;">
                                        <strong>Tokens:</strong> In: ${result.input_tokens || 0}, Out: ${result.output_tokens || 0} |
                                        <strong style="color: #667eea;">Cost: $${(result.estimated_cost || 0).toFixed(4)}</strong>
                                    </div>
                                </div>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            `;

            resultsContainer.innerHTML = '';
            resultsContainer.appendChild(table);
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        async function loadStats() {
            try {
                const response = await fetch('/stats');
                const data = await response.json();

                document.getElementById('totalInteractions').textContent = data.total_interactions || 0;
                document.getElementById('totalTokens').textContent = (data.total_tokens || 0).toLocaleString();
                document.getElementById('totalCost').textContent = '$' + (data.total_cost || 0).toFixed(4);
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }

        function toggleChat(interactionId) {
            const chatDiv = document.getElementById(`chat-${interactionId}`);
            const isVisible = chatDiv.style.display !== 'none';

            if (isVisible) {
                chatDiv.style.display = 'none';
            } else {
                chatDiv.style.display = 'block';
                loadChatHistory(interactionId);
            }
        }

        async function loadChatHistory(interactionId) {
            try {
                const response = await fetch(`/chat/${interactionId}`);
                const data = await response.json();

                const messagesDiv = document.getElementById(`chat-messages-${interactionId}`);

                if (data.messages && data.messages.length > 0) {
                    messagesDiv.innerHTML = data.messages.map(msg => `
                        <div class="chat-message ${msg.role}">
                            <div style="font-weight: bold; margin-bottom: 5px;">${msg.role === 'user' ? 'You' : 'Assistant'}</div>
                            <div>${escapeHtml(msg.content)}</div>
                            <div style="font-size: 11px; margin-top: 5px; opacity: 0.8;">
                                ${new Date(msg.timestamp).toLocaleTimeString()} • ${msg.tokens} tokens • $${msg.cost.toFixed(4)}
                            </div>
                        </div>
                    `).join('');
                } else {
                    messagesDiv.innerHTML = '<div style="color: #666; font-style: italic; text-align: center;">No chat history yet. Ask a question about this image!</div>';
                }

                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            } catch (error) {
                console.error('Error loading chat history:', error);
            }
        }

        async function sendChat(interactionId) {
            const inputField = document.getElementById(`chat-input-${interactionId}`);
            const message = inputField.value.trim();

            if (!message) return;

            inputField.value = '';
            inputField.disabled = true;

            try {
                const response = await fetch(`/chat/${interactionId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ message: message })
                });

                const data = await response.json();

                if (response.ok) {
                    loadChatHistory(interactionId);
                    loadStats();
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (error) {
                alert('Error: ' + error.message);
            } finally {
                inputField.disabled = false;
                inputField.focus();
            }
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    intent = request.form.get('intent', 'OCR this image.')
    model = request.form.get('model', 'deepseek-ocr')

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Generate unique filename using timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{file.filename}"
    filepath = UPLOAD_FOLDER / filename
    file.save(filepath)

    try:
        # Build the prompt
        # Add <|grounding|> prefix if not already present and not a general description
        if intent.lower().startswith('describe this image'):
            prompt = f"{filepath}\n{intent}"
        elif not intent.startswith('<|grounding|>'):
            prompt = f"{filepath}\n<|grounding|>{intent}"
        else:
            prompt = f"{filepath}\n{intent}"

        # Call Ollama with specified model
        result = subprocess.run(
            ['ollama', 'run', model, prompt],
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )

        if result.returncode != 0:
            return jsonify({'error': f'Ollama error: {result.stderr}'}), 500

        output = result.stdout.strip()

        # Calculate token estimates and cost
        input_tokens = estimate_tokens(intent)
        output_tokens = estimate_tokens(output)
        estimated_cost = calculate_cost(input_tokens, output_tokens, model)

        # Store the result in database
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO interactions (filename, intent, output, model, input_tokens, output_tokens, estimated_cost)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (filename, intent, output, model, input_tokens, output_tokens, estimated_cost))
            conn.commit()

        return jsonify({
            'success': True,
            'filename': filename,
            'output': output,
            'tokens': {
                'input': input_tokens,
                'output': output_tokens
            },
            'cost': estimated_cost
        })

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'OCR processing timed out'}), 500
    except FileNotFoundError:
        return jsonify({'error': 'Ollama not found. Please ensure Ollama is installed and in PATH'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/results', methods=['GET'])
def get_results():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, filename, intent, output, model, input_tokens, output_tokens,
                   estimated_cost, timestamp
            FROM interactions
            ORDER BY timestamp DESC
        ''')
        rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append({
                'id': row['id'],
                'filename': row['filename'],
                'intent': row['intent'],
                'output': row['output'],
                'model': row['model'],
                'input_tokens': row['input_tokens'],
                'output_tokens': row['output_tokens'],
                'estimated_cost': row['estimated_cost'],
                'timestamp': row['timestamp']
            })

        return jsonify({'results': results})

@app.route('/stats', methods=['GET'])
def get_stats():
    with get_db() as conn:
        cursor = conn.cursor()

        # Get interaction stats
        cursor.execute('''
            SELECT
                COUNT(*) as total_interactions,
                SUM(input_tokens + output_tokens) as total_tokens,
                SUM(estimated_cost) as total_cost
            FROM interactions
        ''')
        interaction_row = cursor.fetchone()

        # Get chat message stats
        cursor.execute('''
            SELECT
                SUM(tokens) as chat_tokens,
                SUM(cost) as chat_cost
            FROM chat_messages
        ''')
        chat_row = cursor.fetchone()

        total_tokens = (interaction_row['total_tokens'] or 0) + (chat_row['chat_tokens'] or 0)
        total_cost = (interaction_row['total_cost'] or 0.0) + (chat_row['chat_cost'] or 0.0)

        return jsonify({
            'total_interactions': interaction_row['total_interactions'] or 0,
            'total_tokens': total_tokens,
            'total_cost': total_cost
        })

@app.route('/chat/<int:interaction_id>', methods=['GET'])
def get_chat_history(interaction_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT role, content, tokens, cost, timestamp
            FROM chat_messages
            WHERE interaction_id = ?
            ORDER BY timestamp ASC
        ''', (interaction_id,))
        rows = cursor.fetchall()

        messages = []
        for row in rows:
            messages.append({
                'role': row['role'],
                'content': row['content'],
                'tokens': row['tokens'],
                'cost': row['cost'],
                'timestamp': row['timestamp']
            })

        return jsonify({'messages': messages})

@app.route('/chat/<int:interaction_id>', methods=['POST'])
def send_chat_message(interaction_id):
    data = request.get_json()
    message = data.get('message', '').strip()

    if not message:
        return jsonify({'error': 'No message provided'}), 400

    # Get the original interaction details
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT filename, model
            FROM interactions
            WHERE id = ?
        ''', (interaction_id,))
        row = cursor.fetchone()

        if not row:
            return jsonify({'error': 'Interaction not found'}), 404

        filename = row['filename']
        model = row['model']
        filepath = UPLOAD_FOLDER / filename

    try:
        # Build prompt with image path
        prompt = f"{filepath}\n{message}"

        # Call Ollama with the model
        result = subprocess.run(
            ['ollama', 'run', model, prompt],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            return jsonify({'error': f'Ollama error: {result.stderr}'}), 500

        assistant_response = result.stdout.strip()

        # Calculate tokens and cost
        user_tokens = estimate_tokens(message)
        assistant_tokens = estimate_tokens(assistant_response)
        user_cost = calculate_cost(user_tokens, 0, model)
        assistant_cost = calculate_cost(0, assistant_tokens, model)

        # Store chat messages in database
        with get_db() as conn:
            cursor = conn.cursor()

            # Store user message
            cursor.execute('''
                INSERT INTO chat_messages (interaction_id, role, content, tokens, cost)
                VALUES (?, ?, ?, ?, ?)
            ''', (interaction_id, 'user', message, user_tokens, user_cost))

            # Store assistant response
            cursor.execute('''
                INSERT INTO chat_messages (interaction_id, role, content, tokens, cost)
                VALUES (?, ?, ?, ?, ?)
            ''', (interaction_id, 'assistant', assistant_response, assistant_tokens, assistant_cost))

            conn.commit()

        return jsonify({
            'success': True,
            'response': assistant_response
        })

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Chat processing timed out'}), 500
    except FileNotFoundError:
        return jsonify({'error': 'Ollama not found'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    print("Starting DeepSeek OCR Web App...")
    print("Open http://localhost:8080 in your browser")
    app.run(debug=True, host='0.0.0.0', port=8080)
