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

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = Path('uploads')
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Store results in memory (for simplicity)
results_store = []

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

                <button type="submit" id="submitBtn">Process with DeepSeek OCR</button>
            </form>

            <div id="message"></div>
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

        // Load results on page load
        loadResults();

        form.addEventListener('submit', async function(e) {
            e.preventDefault();

            const formData = new FormData();
            const fileInput = document.getElementById('fileInput');
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
                } else {
                    showMessage('Error: ' + data.error, 'error');
                }
            } catch (error) {
                showMessage('Error: ' + error.message, 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Process with DeepSeek OCR';
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
                    </tr>
                </thead>
                <tbody>
                    ${results.map(result => `
                        <tr>
                            <td>
                                <img src="/uploads/${result.filename}" alt="Uploaded image" class="thumbnail">
                                <div style="margin-top: 8px; font-size: 12px; color: #666;">
                                    <strong>Intent:</strong> ${escapeHtml(result.intent)}
                                </div>
                            </td>
                            <td>
                                <div class="output-text">${escapeHtml(result.output)}</div>
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

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Save the uploaded file
    filename = f"{len(results_store)}_{file.filename}"
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

        # Call Ollama with deepseek-ocr
        result = subprocess.run(
            ['ollama', 'run', 'deepseek-ocr', prompt],
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )

        if result.returncode != 0:
            return jsonify({'error': f'Ollama error: {result.stderr}'}), 500

        output = result.stdout.strip()

        # Store the result
        results_store.append({
            'filename': filename,
            'intent': intent,
            'output': output
        })

        return jsonify({
            'success': True,
            'filename': filename,
            'output': output
        })

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'OCR processing timed out'}), 500
    except FileNotFoundError:
        return jsonify({'error': 'Ollama not found. Please ensure Ollama is installed and in PATH'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/results', methods=['GET'])
def get_results():
    return jsonify({'results': results_store})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    print("Starting DeepSeek OCR Web App...")
    print("Open http://localhost:8080 in your browser")
    app.run(debug=True, host='0.0.0.0', port=8080)
