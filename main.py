import os
import logging
import urllib.parse
from flask import Flask, render_template, request, jsonify
from telegram_client import TelegramQuizExtractor

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "telegram_quiz_extractor_secret")

# Initialize Telegram client in a separate module
telegram_client = TelegramQuizExtractor()

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/quiz/<quiz_id>', methods=['GET'])
def direct_quiz_extract(quiz_id):
    """Extract quiz data directly using a quiz ID parameter."""
    logger.info(f"Received direct quiz ID: {quiz_id}")
    
    try:
        # Process the parameter using the Telegram client
        result = telegram_client.process_quiz_parameter(quiz_id)
        
        if result.get('error'):
            return jsonify(result), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.exception(f"Error processing quiz ID: {e}")
        return jsonify({'error': f'Error processing quiz ID: {str(e)}'}), 500

@app.route('/extract', methods=['POST'])
def extract_quiz():
    """Extract quiz data from a Telegram QuizBot URL."""
    data = request.get_json()
    
    if not data or 'url' not in data:
        return jsonify({'error': 'No URL provided'}), 400
    
    url = data['url']
    logger.info(f"Received URL: {url}")
    
    try:
        # Parse the URL to extract the parameter
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        # Check if it's a valid QuizBot URL with a start parameter
        if not parsed_url.netloc.endswith('t.me') or 'start' not in query_params:
            return jsonify({'error': 'Invalid QuizBot URL'}), 400
        
        param = query_params['start'][0]
        logger.info(f"Extracted parameter: {param}")
        
        # Process the parameter using the Telegram client
        result = telegram_client.process_quiz_parameter(param)
        
        if result.get('error'):
            return jsonify(result), 400
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.exception(f"Error processing URL: {e}")
        return jsonify({'error': f'Error processing URL: {str(e)}'}), 500

# Cleanup resources on exit
def cleanup():
    if telegram_client:
        telegram_client.cleanup()

# Register cleanup function to be called on exit
import atexit
atexit.register(cleanup)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
