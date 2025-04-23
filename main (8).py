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
    if not telegram_client.client_ready:
        # If the Telegram client isn't ready, show a helpful error page
        error_title = "Telegram Client Not Connected"
        error_message = "The application couldn't connect to Telegram. Please check your API credentials."
        error_details = "Check your TELEGRAM_API_ID, TELEGRAM_API_HASH, and TELEGRAM_PHONE environment variables."
        
        # Check specific error conditions
        if telegram_client.api_id == 0:
            error_title = "Invalid API ID"
            error_message = "Your TELEGRAM_API_ID must be a number."
            error_details = "Make sure TELEGRAM_API_ID is set as a number without quotes."
        
        return render_template('error.html', 
                              error_title=error_title,
                              error_message=error_message,
                              error_details=error_details)
    
    return render_template('index.html')

@app.route('/quiz/<quiz_id>', methods=['GET'])
def direct_quiz_extract(quiz_id):
    """Extract quiz data directly using a quiz ID parameter."""
    # Remove any spaces or trimming
    quiz_id = quiz_id.strip()
    logger.info(f"Received direct quiz ID: {quiz_id}")
    
    # Check if Telegram client is not ready
    if not telegram_client.client_ready:
        error_title = "Telegram Client Not Connected"
        error_message = "The application couldn't connect to Telegram. Please check your API credentials."
        error_details = "Check your TELEGRAM_API_ID, TELEGRAM_API_HASH, and TELEGRAM_PHONE environment variables."
        
        # Show specialized error page instead of JSON response
        return render_template('error.html', 
                             error_title=error_title,
                             error_message=error_message,
                             error_details=error_details)
    
    try:
        # Process the parameter using the Telegram client
        logger.info(f"Processing quiz ID through telegram client: {quiz_id}")
        result = telegram_client.process_quiz_parameter(quiz_id)
        logger.info(f"Result from telegram client: {result}")
        
        if result.get('error'):
            logger.error(f"Error in quiz extraction: {result.get('error')}")
            
            # Check if request accepts JSON (API call) or HTML (browser)
            if request.headers.get('Accept', '').find('application/json') >= 0:
                return jsonify(result), 400
            else:
                return render_template('quiz_error.html',
                                      error_message="Failed to extract quiz data",
                                      error_details=result.get('error'))
        
        # If successful, return JSON response for now (can be changed to HTML later)
        return jsonify(result), 200
        
    except Exception as e:
        logger.exception(f"Error processing quiz ID: {e}")
        
        # Check if request accepts JSON (API call) or HTML (browser)
        if request.headers.get('Accept', '').find('application/json') >= 0:
            return jsonify({'error': f'Error processing quiz ID: {str(e)}'}), 500
        else:
            return render_template('quiz_error.html',
                                  error_message="An unexpected error occurred",
                                  error_details=str(e))

# Add routes for handling various URL formats with quiz IDs
@app.route('/quiz <quiz_id>', methods=['GET'])
def direct_quiz_extract_with_space(quiz_id):
    """Handle quiz extraction with space in URL."""
    logger.info(f"Received direct quiz ID (with space): {quiz_id}")
    return direct_quiz_extract(quiz_id)

@app.route('/quiz/<path:quiz_id>', methods=['GET'])
def direct_quiz_extract_path(quiz_id):
    """Handle quiz extraction with path-like quiz ID."""
    logger.info(f"Received path-like quiz ID: {quiz_id}")
    return direct_quiz_extract(quiz_id)

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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)