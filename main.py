import base64
import binascii
import json
import os
import asyncio
import logging
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, jsonify, render_template, redirect, url_for
from threading import Thread
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from utils.quiz_extractor import extract_quiz, QuizExtractor
from utils.database import QuizDatabase
from models import db, Quiz, QuizAttempt

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)

# Configure database - Get the DATABASE_URL from environment variables
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("postgres://koyeb-adm:npg_AdrGeCaH91Kx@ep-green-water-a2s2rmb5.eu-central-1.pg.koyeb.app/koyebdb")  # Use environment variable for database URL
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Set up the secret key
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "quiz-extractor-secret-key")

# Initialize the database
db = SQLAlchemy(app)

# Telegram client setup
API_ID = int(os.getenv("API_ID", "28624690"))
API_HASH = os.getenv("API_HASH", "67e6593b5a9b5ab20b11ccef6700af5b")
SESSION_STRING = os.getenv("SESSION_STRING", '1BVtsOKEBu0M0NiU2jKhDl1XFCRgj6MxCBfeYIW8VDHP-LX_BR-bTDOWByKUfiiw9Y-EjjhXCaZ0zcZjRxlirhR6nPKxpC1st_PW4kAZbMp6TLvgUXMOkVSd5rzz-vWxOZcd6WsdLxWjs9-lhi-xfWgL23p2iLGXyZi-BW17o3X38C3K-sHavdR1ggmV598L6x6bXnclPcQNmCDIBQF7KakTF0-k-Em33zsy4N-rUhb2egQO4k98F6DYTnnHQVwgJnlpLPFJdZ8g9-LDmqgUEmRsoXoUVx_Hf0lB7ykIpzlXUOeabteip8OsiSaFPIPj2f90wVCIxnfmXm1LMF70N9Z3HGVUa2g0=')  # Shortened here

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# Initialize database tables
with app.app_context():
    db.create_all()
    logger.info("Database tables created")

def decode_param(start_param):
    try:
        # Log the parameter we're trying to decode for debugging
        print(f"Attempting to decode parameter: {start_param}")
        
        # Add proper padding if needed
        padding = '=' * (-len(start_param) % 4)
        padded_param = start_param + padding
        
        # Try multiple decoding methods
        
        # Method 1: Standard base64 decode
        try:
            decoded_bytes = base64.b64decode(padded_param)
            for encoding in ['latin-1', 'utf-8', 'iso-8859-1', 'windows-1252']:
                try:
                    decoded_text = decoded_bytes.decode(encoding)
                    return json.loads(decoded_text)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
        except Exception as e:
            print(f"Standard base64 decode failed: {e}")
        
        # Method 2: URL-safe base64 decode
        try:
            decoded_bytes = base64.urlsafe_b64decode(padded_param)
            for encoding in ['latin-1', 'utf-8', 'iso-8859-1', 'windows-1252']:
                try:
                    decoded_text = decoded_bytes.decode(encoding)
                    return json.loads(decoded_text)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
        except Exception as e:
            print(f"URL-safe base64 decode failed: {e}")
        
        # Method 3: Try with adjusted padding
        for i in range(4):
            try:
                alt_padded = start_param.rstrip('=') + ('=' * i)
                decoded_bytes = base64.urlsafe_b64decode(alt_padded)
                decoded_text = decoded_bytes.decode('latin-1')  # Latin-1 handles all byte values
                return json.loads(decoded_text)
            except:
                continue
        
        # Method 4: Convert URL-safe to standard base64 characters
        try:
            standard_param = padded_param.replace('-', '+').replace('_', '/')
            decoded_bytes = base64.b64decode(standard_param)
            
            for encoding in ['latin-1', 'utf-8', 'iso-8859-1', 'windows-1252']:
                try:
                    decoded_text = decoded_bytes.decode(encoding)
                    return json.loads(decoded_text)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
        except Exception as e:
            print(f"Custom base64 decode failed: {e}")
        
        # Method 5: Treat as hex if it looks like hex
        if all(c in '0123456789abcdefABCDEF' for c in start_param):
            try:
                hex_bytes = bytes.fromhex(start_param)
                for encoding in ['latin-1', 'utf-8', 'iso-8859-1']:
                    try:
                        return json.loads(hex_bytes.decode(encoding))
                    except:
                        continue
                return {"binary_data": str(hex_bytes)}
            except Exception as e:
                print(f"Hex decode failed: {e}")
                
        # Method 6: Handle short codes
        if len(start_param) < 12 and not start_param.startswith('{'):
            print(f"Detected possible Telegram short code: {start_param}")
            # Create a structured response for short codes
            quiz_data = {
                "quiz_title": "Telegram Quiz",
                "questions": [
                    {
                        "question": f"This appears to be a QuizBot short code: {start_param}",
                        "options": [
                            {"text": "Short codes require using the Telegram bot directly", "correct": False},
                            {"text": f"Send /start {start_param} to @QuizBot in Telegram", "correct": True}
                        ]
                    }
                ]
            }
            return quiz_data
        
        # Method 7: Try reversing the string (some encodings might be reversed)
        try:
            reversed_param = start_param[::-1]
            padding = '=' * (-len(reversed_param) % 4)
            reversed_padded = reversed_param + padding
            decoded_bytes = base64.urlsafe_b64decode(reversed_padded)
            
            for encoding in ['latin-1', 'utf-8', 'iso-8859-1', 'windows-1252']:
                try:
                    decoded_text = decoded_bytes.decode(encoding)
                    return json.loads(decoded_text)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
        except Exception as e:
            print(f"Reversed string decoding failed: {e}")
        
        print("All decoding methods failed for parameter")
        # If all else fails, return a message about the parameter
        return {
            "questions": [
                {
                    "question": f"Could not decode quiz data from parameter: {start_param}",
                    "options": [
                        {"text": "The format may not be supported by this decoder"}
                    ]
                }
            ]
        }
    except Exception as e:
        print(f"Error in decode_param: {e}")
        # Return a error message as structured data
        return {
            "questions": [
                {
                    "question": f"Error processing quiz data: {str(e)}",
                    "options": [
                        {"text": "Please try a different quiz link"}
                    ]
                }
            ]
        }

async def fetch_quiz_data(url):
    try:
        # Extract the start parameter from URL
        if "start=" in url:
            start_param = url.split("start=")[1]
            print(f"Extracted parameter: {start_param}")
        else:
            print("Could not find 'start' parameter in URL")
            return None
    except IndexError:
        print("Could not extract 'start' parameter from URL")
        return None

    # Try to decode the parameter
    quiz_data = decode_param(start_param)
    
    if not quiz_data:
        print("Failed to decode quiz data")
        return None

    # Format quiz questions
    questions = []
    count = 1

    try:
        for q in quiz_data.get("questions", []):
            question_text = q.get('question', '')
            if not question_text:
                # Try alternate keys that might contain the question
                for key in ['text', 'title', 'q']:
                    if key in q:
                        question_text = q[key]
                        break
            
            formatted = f"{count}. {question_text}\n"
            
            # Handle options with different possible structures
            options = q.get('options', [])
            if not options and 'answers' in q:
                options = q['answers']
            
            for i, option in enumerate(options):
                # Handle both object and string options
                if isinstance(option, dict):
                    option_text = option.get('text', '')
                    is_correct = option.get('correct', False)
                else:
                    option_text = str(option)
                    is_correct = False
                
                formatted += f"{chr(65 + i)}. {option_text}"
                if is_correct:
                    formatted += " ✅"
                formatted += "\n"
            
            questions.append(formatted)
            count += 1
    except Exception as e:
        print(f"Error formatting quiz data: {e}")
        if quiz_data:
            # If we have some data but can't parse it properly, return it raw
            return str(quiz_data)
        return None

    if not questions:
        print("No questions found in quiz data")
        return None

    # Write quiz to file
    filename = "quiz_questions.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n\n".join(questions))

    return filename

@client.on(events.NewMessage(pattern=r'^/quiz\s+(https://t\.me/[\w/?=]+)$'))
async def quiz_handler(event):
    url = event.pattern_match.group(1)
    logger.info(f"Received quiz URL: {url}")
    await event.reply("Fetching quiz data...")
    
    try:
        # Extract the start parameter from URL
        if "start=" in url:
            start_param = url.split("start=")[1]
            logger.info(f"Extracted parameter: {start_param}")
        else:
            await event.reply("Invalid URL format. Must contain 'start=' parameter.")
            return
            
        # Check if this quiz is already in our database
        with app.app_context():
            existing_quiz = QuizDatabase.get_quiz_by_id(start_param)
            
            if existing_quiz:
                logger.info(f"Quiz already exists in database: {start_param}")
                await event.reply("Quiz already exists in our database. Sending the saved quiz data...")
                
                # Send the formatted quiz data
                filename = f"quiz_{start_param}.txt"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(existing_quiz.formatted_data)
                
                await client.send_file(
                    event.chat_id, 
                    filename, 
                    caption=f"Here's your quiz with {existing_quiz.question_count} questions"
                )
                
                # Update access count
                existing_quiz.increment_access()
                db.session.commit()
                
                # Clean up
                os.remove(filename)
                return
        
        # For short codes (typical format: 8-10 alphanumeric characters)
        if len(start_param) < 12 and start_param.isalnum():
            await event.reply("Detected Telegram short code. Using advanced extraction method...")
            
            # Use our advanced extraction method
            quiz_data = extract_quiz(start_param, API_ID, API_HASH, SESSION_STRING)
            
            if quiz_data:
                # Save to database
                with app.app_context():
                    QuizDatabase.save_quiz(start_param, quiz_data)
                
                # Create a file with the formatted data
                filename = f"quiz_{start_param}.txt"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(quiz_data.get('formatted_text', ''))
                
                # Send the file
                await client.send_file(
                    event.chat_id, 
                    filename, 
                    caption=f"Here's your quiz with {len(quiz_data.get('questions', []))} questions"
                )
                
                # Clean up
                os.remove(filename)
                return
            else:
                await event.reply("Could not extract quiz data using advanced method. Trying standard method...")
        
        # For standard encoded parameters
        # Try to decode the parameter using our original method
        quiz_data = decode_param(start_param)
        
        if not quiz_data:
            await event.reply("Sorry, could not decode the quiz data.")
            return
            
        # Format quiz questions
        questions = []
        count = 1
        
        for q in quiz_data.get("questions", []):
            question_text = q.get('question', '')
            if not question_text:
                for key in ['text', 'title', 'q']:
                    if key in q:
                        question_text = q[key]
                        break
            
            formatted = f"{count}. {question_text}\n"
            
            options = q.get('options', [])
            if not options and 'answers' in q:
                options = q['answers']
            
            for i, option in enumerate(options):
                if isinstance(option, dict):
                    option_text = option.get('text', '')
                    is_correct = option.get('correct', False)
                else:
                    option_text = str(option)
                    is_correct = False
                
                formatted += f"{chr(65 + i)}. {option_text}"
                if is_correct:
                    formatted += " ✅"
                formatted += "\n"
            
            questions.append(formatted)
            count += 1
        
        if not questions:
            await event.reply("No questions found in quiz data.")
            return
            
        # Create formatted text content
        formatted_text = "\n\n".join(questions)
        
        # Create a structured version for database storage
        structured_quiz = {
            'quiz_id': start_param,
            'title': quiz_data.get('quiz_title', 'Telegram Quiz'),
            'question_count': len(questions),
            'questions': quiz_data.get('questions', []),
            'formatted_text': formatted_text
        }
        
        # Save to database
        with app.app_context():
            QuizDatabase.save_quiz(start_param, structured_quiz)
        
        # Write to file and send
        filename = f"quiz_{start_param}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(formatted_text)
            
        await client.send_file(
            event.chat_id, 
            filename, 
            caption=f"Here's your quiz with {len(questions)} questions"
        )
        
        # Clean up
        os.remove(filename)
        
    except Exception as e:
        logger.error(f"Error processing quiz: {str(e)}")
        await event.reply(f"Sorry, an error occurred while processing the quiz: {str(e)}")

@app.route("/health", methods=["GET"])
def health_check():
    return "OK", 200

@app.route("/api/decode", methods=["POST"])
def api_decode():
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({"error": "No URL provided"}), 400
            
        # Extract the start parameter from URL
        if "start=" in url:
            start_param = url.split("start=")[1]
            print(f"API: Extracted parameter: {start_param}")
        else:
            return jsonify({"error": "No start parameter in URL"}), 400
            
        # Try to decode the parameter
        quiz_data = decode_param(start_param)
        
        if not quiz_data:
            return jsonify({"error": "Failed to decode quiz data"}), 400
            
        return jsonify(quiz_data), 200
    except Exception as e:
        print(f"API decode error: {str(e)}")
        return jsonify({"error": f"Error processing request: {str(e)}"}), 500

@app.route("/extract", methods=["GET", "POST"])
def extract():
    if request.method == "POST":
        url = request.form.get('url')
        if not url:
            return "No URL provided", 400
        
        # Extract the parameter
        start_param = ""
        if "start=" in url:
            start_param = url.split("start=")[1]
            logger.info(f"Web: Extracted parameter: {start_param}")
        elif len(url) < 12 and url.isalnum():
            # Direct shortcode input
            start_param = url
            logger.info(f"Web: Using direct shortcode: {start_param}")
        else:
            return "Invalid URL or shortcode format", 400
        
        # Check if we already have this quiz in the database
        existing_quiz = QuizDatabase.get_quiz_by_id(start_param)
        if existing_quiz:
            logger.info(f"Quiz found in database: {start_param}")
            
            # Update access count
            existing_quiz.increment_access()
            db.session.commit()
            
            # Return the formatted quiz data
            result = f"""
            <h2>{existing_quiz.title}</h2>
            <p>Quiz ID: {existing_quiz.quiz_id}</p>
            <p>Questions: {existing_quiz.question_count}</p>
            <p>This quiz has been accessed {existing_quiz.access_count} times.</p>
            <hr>
            <pre>{existing_quiz.formatted_data}</pre>
            """
            return result
        
        # For short codes (typical format: 8-10 alphanumeric characters)
        result = ""
        if len(start_param) < 12 and start_param.isalnum():
            logger.info("Detected Telegram short code, using advanced extraction")
            
            # Use advanced extraction
            quiz_data = extract_quiz(start_param, API_ID, API_HASH, SESSION_STRING)
            
            if quiz_data:
                # Save to database
                QuizDatabase.save_quiz(start_param, quiz_data)
                
                # Format for display
                result = f"""
                <h2>{quiz_data.get('title', 'Telegram Quiz')}</h2>
                <p>Quiz ID: {start_param}</p>
                <p>Questions: {len(quiz_data.get('questions', []))}</p>
                <hr>
                <pre>{quiz_data.get('formatted_text', '')}</pre>
                """
                return result
            else:
                result = "<p>Could not extract quiz data using advanced method. Trying standard method...</p>"
        
        # Standard decoding for encoded parameters
        quiz_data = decode_param(start_param)
        
        if not quiz_data:
            return "Failed to decode quiz data. This may be a shortcode that requires advanced extraction.", 400
        
        # Format quiz questions
        questions = []
        count = 1
        
        try:
            for q in quiz_data.get("questions", []):
                question_text = q.get('question', '')
                if not question_text:
                    # Try alternate keys that might contain the question
                    for key in ['text', 'title', 'q']:
                        if key in q:
                            question_text = q[key]
                            break
                
                formatted = f"{count}. {question_text}\n"
                
                # Handle options with different possible structures
                options = q.get('options', [])
                if not options and 'answers' in q:
                    options = q['answers']
                
                for i, option in enumerate(options):
                    # Handle both object and string options
                    if isinstance(option, dict):
                        option_text = option.get('text', '')
                        is_correct = option.get('correct', False)
                    else:
                        option_text = str(option)
                        is_correct = False
                    
                    formatted += f"{chr(65 + i)}. {option_text}"
                    if is_correct:
                        formatted += " ✅"
                    formatted += "\n"
                
                questions.append(formatted)
                count += 1
        except Exception as e:
            logger.error(f"Error formatting quiz data: {str(e)}")
            if quiz_data:
                return f"Error formatting quiz data: {str(quiz_data)}", 400
            return "Error formatting quiz data", 400
        
        if not questions:
            return "No questions found in quiz data", 400
        
        # Create formatted content
        formatted_text = "\n\n".join(questions)
        
        # Create structured data for database
        structured_quiz = {
            'quiz_id': start_param,
            'title': quiz_data.get('quiz_title', 'Telegram Quiz'),
            'question_count': len(questions),
            'questions': quiz_data.get('questions', []),
            'formatted_text': formatted_text
        }
        
        # Save to database
        QuizDatabase.save_quiz(start_param, structured_quiz)
        
        # Return formatted result
        result = f"""
        <h2>{structured_quiz['title']}</h2>
        <p>Quiz ID: {start_param}</p>
        <p>Questions: {structured_quiz['question_count']}</p>
        <hr>
        <pre>{formatted_text}</pre>
        """
        return result
    
    # GET request - show the form
    recent_quizzes = QuizDatabase.get_recent_quizzes(5)
    recent_quiz_list = ""
    if recent_quizzes:
        recent_quiz_list = "<ul class='list-group mt-4'>"
        for quiz in recent_quizzes:
            recent_quiz_list += f"""
            <li class='list-group-item bg-dark'>
                <div class='d-flex justify-content-between align-items-center'>
                    <a href="/quiz/{quiz.quiz_id}">{quiz.title}</a>
                    <span class='badge bg-primary rounded-pill'>{quiz.question_count} Q</span>
                </div>
                <small class='text-muted'>Accessed {quiz.access_count} times • Last: {quiz.last_accessed.strftime('%Y-%m-%d')}</small>
            </li>
            """
        recent_quiz_list += "</ul>"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Extract Quiz - Telegram QuizBot Extractor</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <style>
            body {{ padding: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb">
                    <li class="breadcrumb-item"><a href="/">Home</a></li>
                    <li class="breadcrumb-item active" aria-current="page">Extract Quiz</li>
                </ol>
            </nav>
        
            <div class="card bg-dark mb-4">
                <div class="card-header">
                    <h2>Extract Quiz Data</h2>
                </div>
                <div class="card-body">
                    <form method="post">
                        <div class="form-group mb-3">
                            <label for="url" class="form-label">Enter QuizBot URL or short code:</label>
                            <input type="text" class="form-control" id="url" name="url" 
                                   placeholder="https://t.me/QuizBot?start=XXXXX or shortcode">
                            <small class="form-text text-muted">You can enter a full QuizBot URL or just the shortcode (e.g., gMBZoDtx)</small>
                        </div>
                        <button type="submit" class="btn btn-primary">Extract Quiz</button>
                    </form>
                </div>
            </div>
            
            <div class="card bg-dark">
                <div class="card-header">
                    <h3>Recently Extracted Quizzes</h3>
                </div>
                <div class="card-body">
                    {recent_quiz_list if recent_quiz_list else "<p>No quizzes have been extracted yet.</p>"}
                </div>
            </div>
            
            <div class="mt-4">
                <a href="/" class="btn btn-secondary">Back to Home</a>
            </div>
        </div>
    </body>
    </html>
    """

@app.route("/quiz/<quiz_id>", methods=["GET"])
def view_quiz(quiz_id):
    """View a specific quiz by ID"""
    quiz = QuizDatabase.get_quiz_by_id(quiz_id)
    
    if not quiz:
        return "Quiz not found", 404
    
    # Update access count
    quiz.increment_access()
    db.session.commit()
    
    # Format the quiz data for display
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{quiz.title} - Quiz</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <style>
            body {{ padding: 20px; }}
            pre {{ white-space: pre-wrap; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{quiz.title}</h1>
            <p>Quiz ID: {quiz.quiz_id}</p>
            <p>Questions: {quiz.question_count}</p>
            <p>This quiz has been accessed {quiz.access_count} times.</p>
            <p>Last accessed: {quiz.last_accessed.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            
            <div class="d-flex justify-content-between mt-3 mb-4">
                <a href="/" class="btn btn-secondary">Home</a>
                <a href="/extract" class="btn btn-primary">Extract Another Quiz</a>
                <a href="#" class="btn btn-info" 
                   onclick="navigator.clipboard.writeText(window.location.href); alert('Link copied!'); return false;">
                   Copy Link
                </a>
            </div>
            
            <hr>
            <div class="card bg-dark">
                <div class="card-body">
                    <pre>{quiz.formatted_data}</pre>
                </div>
            </div>
            
            <div class="mt-4">
                <p>Download as:</p>
                <a href="/download/{quiz.quiz_id}/txt" class="btn btn-sm btn-outline-light">Text File</a>
                <a href="/download/{quiz.quiz_id}/json" class="btn btn-sm btn-outline-light">JSON</a>
            </div>
        </div>
    </body>
    </html>
    """

@app.route("/download/<quiz_id>/<format>", methods=["GET"])
def download_quiz(quiz_id, format):
    """Download a quiz in various formats"""
    quiz = QuizDatabase.get_quiz_by_id(quiz_id)
    
    if not quiz:
        return "Quiz not found", 404
    
    if format == "txt":
        # Plain text download
        response = app.response_class(
            response=quiz.formatted_data,
            status=200,
            mimetype="text/plain"
        )
        response.headers["Content-Disposition"] = f"attachment; filename=quiz_{quiz_id}.txt"
        return response
        
    elif format == "json":
        # JSON download
        try:
            # Extract the JSON data
            raw_data = json.loads(quiz.raw_data)
            response = app.response_class(
                response=json.dumps(raw_data, indent=2),
                status=200,
                mimetype="application/json"
            )
            response.headers["Content-Disposition"] = f"attachment; filename=quiz_{quiz_id}.json"
            return response
        except:
            return "Could not generate JSON file", 400
    
    return "Invalid format", 400

@app.route("/", methods=["GET"])
def index():
    """Home page with quiz listing and stats"""
    # Get quiz statistics
    quiz_count = Quiz.query.count()
    recent_quizzes = QuizDatabase.get_recent_quizzes(5)
    popular_quizzes = QuizDatabase.get_popular_quizzes(5)
    
    # Format recent quizzes list
    recent_list = "<p>No quizzes extracted yet.</p>"
    if recent_quizzes:
        recent_list = "<ul class='list-group'>"
        for quiz in recent_quizzes:
            recent_list += f"""
            <li class='list-group-item bg-dark'>
                <div class='d-flex justify-content-between align-items-center'>
                    <a href="/quiz/{quiz.quiz_id}">{quiz.title}</a>
                    <span class='badge bg-primary rounded-pill'>{quiz.question_count} Q</span>
                </div>
                <small class='text-muted'>Accessed {quiz.access_count} times • Last: {quiz.last_accessed.strftime('%Y-%m-%d')}</small>
            </li>
            """
        recent_list += "</ul>"
    
    # Format popular quizzes list
    popular_list = ""
    if popular_quizzes:
        popular_list = """
        <div class='mt-4'>
            <h3>Most Popular Quizzes</h3>
            <ul class='list-group'>
        """
        for quiz in popular_quizzes:
            popular_list += f"""
            <li class='list-group-item bg-dark'>
                <div class='d-flex justify-content-between align-items-center'>
                    <a href="/quiz/{quiz.quiz_id}">{quiz.title}</a>
                    <span class='badge bg-info rounded-pill'>{quiz.access_count} views</span>
                </div>
            </li>
            """
        popular_list += "</ul></div>"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Telegram QuizBot Extractor</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <style>
            body {{ padding: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="jumbotron bg-dark p-4 mb-4">
                <h1>Telegram QuizBot Extractor</h1>
                <p class="lead">Extract complete quiz data from Telegram QuizBot links and short codes</p>
                <p>This tool can extract quiz data directly from QuizBot URLs or short codes without having to play through the quiz.</p>
                <a href="/extract" class="btn btn-primary btn-lg mt-2">Extract Quiz</a>
            </div>
            
            <div class="row">
                <div class="col-md-8">
                    <div class="card bg-dark mb-4">
                        <div class="card-header">
                            <h3>Recently Extracted Quizzes</h3>
                        </div>
                        <div class="card-body">
                            {recent_list}
                        </div>
                    </div>
                    
                    {popular_list}
                </div>
                
                <div class="col-md-4">
                    <div class="card bg-dark">
                        <div class="card-header">
                            <h3>How to Use</h3>
                        </div>
                        <div class="card-body">
                            <ol>
                                <li>Go to the <a href="/extract">Extract</a> page</li>
                                <li>Enter a Telegram QuizBot URL: <br><code>https://t.me/QuizBot?start=XXXXX</code></li>
                                <li>Or enter just the short code (e.g., <code>gMBZoDtx</code>)</li>
                                <li>Click "Extract Quiz" to get all questions and answers</li>
                            </ol>
                            <p>You can also send a message to our Telegram bot:<br>
                            <code>/quiz https://t.me/QuizBot?start=XXXXX</code></p>
                        </div>
                    </div>
                    
                    <div class="card bg-dark mt-4">
                        <div class="card-header">
                            <h3>Statistics</h3>
                        </div>
                        <div class="card-body">
                            <p><strong>Total Quizzes:</strong> {quiz_count}</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

def run_flask():
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    # Run Flask in a background thread
    Thread(target=run_flask).start()
    # Start Telethon in main thread
    with client:
        client.run_until_disconnected()
