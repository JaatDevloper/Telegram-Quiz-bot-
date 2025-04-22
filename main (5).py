import base64
import binascii
import json
import os
import asyncio
from flask import Flask, request, jsonify
from threading import Thread
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Flask app setup
app = Flask(__name__)

# Telegram client setup
API_ID = int(os.getenv("API_ID", "28624690"))
API_HASH = os.getenv("API_HASH", "67e6593b5a9b5ab20b11ccef6700af5b")
SESSION_STRING = os.getenv("SESSION_STRING", '1BVtsOKEBu0M0NiU2jKhDl1XFCRgj6MxCBfeYIW8VDHP-LX_BR-bTDOWByKUfiiw9Y-EjjhXCaZ0zcZjRxlirhR6nPKxpC1st_PW4kAZbMp6TLvgUXMOkVSd5rzz-vWxOZcd6WsdLxWjs9-lhi-xfWgL23p2iLGXyZi-BW17o3X38C3K-sHavdR1ggmV598L6x6bXnclPcQNmCDIBQF7KakTF0-k-Em33zsy4N-rUhb2egQO4k98F6DYTnnHQVwgJnlpLPFJdZ8g9-LDmqgUEmRsoXoUVx_Hf0lB7ykIpzlXUOeabteip8OsiSaFPIPj2f90wVCIxnfmXm1LMF70N9Z3HGVUa2g0=')  # Shortened here

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

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
                
        # Method 6: Telegram QuizBot specific format (short code handler)
        # Sometimes Telegram uses a short code that's actually a reference to a server-side quiz
        if len(start_param) < 12 and not start_param.startswith('{'):
            print(f"Detected possible Telegram short code: {start_param}")
            try:
                # For short codes, let's try to use the Telegram client to fetch quiz data
                async def _fetch_from_telegram():
                    try:
                        chat = await client.get_entity("QuizBot")
                        await client.send_message(chat, f"/start {start_param}")
                        # Wait for a response
                        response = await client.get_messages(chat, limit=1)
                        if response and response[0]:
                            return {"quiz_title": "Telegram Quiz", 
                                    "questions": [{"question": "Quiz data needs to be fetched from Telegram directly", 
                                                  "options": [{"text": "This requires user interaction with @QuizBot"}]}]}
                    except Exception as e:
                        print(f"Error fetching from Telegram: {e}")
                    return None
                
                # Try to get data via Telegram API
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(_fetch_from_telegram())
                if result:
                    return result
                
                # If we can't fetch via API, construct a placeholder with instructions
                return {
                    "questions": [
                        {
                            "question": f"This appears to be a QuizBot short code ({start_param})",
                            "options": [
                                {"text": "Short codes require direct interaction with @QuizBot"}
                            ]
                        }
                    ]
                }
            except Exception as e:
                print(f"Telegram-specific decoding failed: {e}")
        
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
    print(f"Received URL: {url}")
    await event.reply("Fetching quiz data...")

    filename = await fetch_quiz_data(url)

    if filename:
        await client.send_file(event.chat_id, filename, caption="Here are the quiz questions.")
        os.remove(filename)
    else:
        await event.reply("Sorry, something went wrong while fetching the quiz.")

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
            
        # Extract the start parameter from URL
        if "start=" in url:
            start_param = url.split("start=")[1]
            print(f"Web: Extracted parameter: {start_param}")
        else:
            return "No start parameter in URL", 400
            
        # Try to decode the parameter
        quiz_data = decode_param(start_param)
        
        if not quiz_data:
            return "Failed to decode quiz data", 400
            
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
            print(f"Error formatting quiz data: {str(e)}")
            if quiz_data:
                return f"Error formatting quiz data: {str(quiz_data)}", 400
            return "Error formatting quiz data", 400
            
        if not questions:
            return "No questions found in quiz data", 400
            
        result = "\n\n".join(questions)
        return f"<pre>{result}</pre>"
        
    return """
    <form method="post">
        <label for="url">Enter QuizBot URL:</label><br>
        <input type="text" id="url" name="url" size="50"><br>
        <input type="submit" value="Extract Quiz">
    </form>
    """

@app.route("/", methods=["GET"])
def index():
    return """
    <h1>Telegram QuizBot Extractor</h1>
    <p>This tool helps extract quiz data from Telegram QuizBot links.</p>
    <p>Use the <a href="/extract">Extract</a> page to process a quiz link.</p>
    <p>Or send a message to the Telegram bot with: /quiz https://t.me/QuizBot?start=XXXXX</p>
    """

def run_flask():
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    # Run Flask in a background thread
    Thread(target=run_flask).start()
    # Start Telethon in main thread
    with client:
        client.run_until_disconnected()