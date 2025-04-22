import base64
import binascii
import json
import os
import asyncio
from flask import Flask
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
        
        print("All decoding methods failed for parameter")
        return None
    except Exception as e:
        print(f"Error in decode_param: {e}")
        return None

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

def run_flask():
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    # Run Flask in a background thread
    Thread(target=run_flask).start()
    # Start Telethon in main thread
    with client:
        client.run_until_disconnected()
