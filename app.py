import os
import logging
import urllib.parse
import json
import base64
import binascii
import re
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from utils.decoder import decode_quiz_param, decode_quiz_data
from utils.telegram_client import setup_telegram_client, get_quiz_data

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", os.urandom(24))

# Initialize Telegram client
telegram_client = None

# Initialize Telegram client on startup
def initialize():
    global telegram_client
    try:
        telegram_client = setup_telegram_client()
        logger.info("Telegram client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Telegram client: {str(e)}")
        telegram_client = None

# Run initialization
initialize()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/extract', methods=['POST'])
def extract():
    try:
        # Get URL from form
        quiz_url = request.form.get('quiz_url', '').strip()
        logger.debug(f"Received URL: {quiz_url}")
        
        if not quiz_url:
            flash("Please enter a QuizBot URL", "warning")
            return redirect(url_for('index'))
        
        # Check if URL is a valid Telegram QuizBot URL
        if not ('t.me/QuizBot' in quiz_url or 'telegram.me/QuizBot' in quiz_url):
            flash("Invalid QuizBot URL format", "danger")
            return redirect(url_for('index'))
        
        # Parse URL to extract start parameter
        parsed_url = urllib.parse.urlparse(quiz_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        # Extract the start parameter
        start_param = None
        if 'start' in query_params:
            start_param = query_params['start'][0]
        else:
            # Try to extract from path for URLs like t.me/QuizBot?start=abc
            path_match = re.search(r'start=([^&]+)', quiz_url)
            if path_match:
                start_param = path_match.group(1)
        
        logger.debug(f"Extracted start parameter: {start_param}")
        
        if not start_param:
            flash("Could not find start parameter in URL", "danger")
            return redirect(url_for('index'))
        
        # Decode the start parameter
        decoded_param = decode_quiz_param(start_param)
        logger.debug(f"Decoded parameter: {decoded_param}")
        
        if not decoded_param:
            flash("Failed to decode quiz parameter", "danger")
            return redirect(url_for('index'))
        
        # Use Telegram client to fetch quiz data if available
        quiz_data = None
        if telegram_client:
            quiz_data = get_quiz_data(telegram_client, start_param)
        
        # If we couldn't get data from Telegram, try to decode it locally
        if not quiz_data:
            quiz_data = decode_quiz_data(decoded_param)
        
        if not quiz_data:
            flash("Failed to extract quiz data", "danger")
            return redirect(url_for('index'))
        
        # Format the quiz data for display
        formatted_quiz = {
            'title': quiz_data.get('title', 'Unknown Quiz'),
            'description': quiz_data.get('description', 'No description available'),
            'questions': []
        }
        
        # Process questions
        questions = quiz_data.get('questions', [])
        for q in questions:
            question = {
                'text': q.get('text', 'Unknown question'),
                'options': q.get('options', []),
                'correct_option': q.get('correct_option', -1)
            }
            formatted_quiz['questions'].append(question)
        
        return render_template('result.html', quiz=formatted_quiz)
    
    except Exception as e:
        logger.error(f"Error extracting quiz: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.route('/api/decode', methods=['POST'])
def api_decode():
    try:
        data = request.get_json()
        quiz_url = data.get('url', '')
        
        if not quiz_url:
            return jsonify({'error': 'URL parameter is required'}), 400
        
        # Parse URL to extract start parameter
        parsed_url = urllib.parse.urlparse(quiz_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        # Extract the start parameter
        start_param = None
        if 'start' in query_params:
            start_param = query_params['start'][0]
        else:
            # Try to extract from path for URLs like t.me/QuizBot?start=abc
            path_match = re.search(r'start=([^&]+)', quiz_url)
            if path_match:
                start_param = path_match.group(1)
        
        if not start_param:
            return jsonify({'error': 'Could not find start parameter in URL'}), 400
        
        # Decode the start parameter
        decoded_param = decode_quiz_param(start_param)
        
        if not decoded_param:
            return jsonify({'error': 'Failed to decode quiz parameter'}), 400
        
        # Parse the decoded parameter
        quiz_data = decode_quiz_data(decoded_param)
        
        if not quiz_data:
            return jsonify({'error': 'Failed to extract quiz data'}), 400
        
        return jsonify({'success': True, 'data': quiz_data})
    
    except Exception as e:
        logger.error(f"API error: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html', error="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('index.html', error="Server error occurred"), 500
