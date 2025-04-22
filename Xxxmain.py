import base64
import json
import os
from flask import Flask
from telethon import TelegramClient, events

# Flask app setup
app = Flask(__name__)

# Your bot's Telegram client setup
API_ID = '28624690'  # Replace with your actual API ID
API_HASH = '67e6593b5a9b5ab20b11ccef6700af5b'  # Replace with your actual API HASH
SESSION = '1BVtsOKEBu0M0NiU2jKhDl1XFCRgj6MxCBfeYIW8VDHP-LX_BR-bTDOWByKUfiiw9Y-EjjhXCaZ0zcZjRxlirhR6nPKxpC1st_PW4kAZbMp6TLvgUXMOkVSd5rzz-vWxOZcd6WsdLxWjs9-lhi-xfWgL23p2iLGXyZi-BW17o3X38C3K-sHavdR1ggmV598L6x6bXnclPcQNmCDIBQF7KakTF0-k-Em33zsy4N-rUhb2egQO4k98F6DYTnnHQVwgJnlpLPFJdZ8g9-LDmqgUEmRsoXoUVx_Hf0lB7ykIpzlXUOeabteip8OsiSaFPIPj2f90wVCIxnfmXm1LMF70N9Z3HGVUa2g0='

# Initialize the Telegram client
client = TelegramClient(SESSION, API_ID, API_HASH)

def decode_param(start_param):
    """Decodes the start param base64url to get the quiz data."""
    try:
        # Add padding if it's missing
        padding = '=' * (-len(start_param) % 4)
        start_param += padding
        decoded = base64.urlsafe_b64decode(start_param.encode()).decode('utf-8')
        return json.loads(decoded)  # Assuming it returns a JSON structure
    except Exception as e:
        print(f"Error decoding param: {e}")
        return None

async def fetch_quiz_data(url):
    """Fetches and decodes quiz data from the URL."""
    start_param = url.split("start=")[1]  # Extract start parameter from URL
    quiz_data = decode_param(start_param)

    if quiz_data:
        questions = []
        count = 1

        for q in quiz_data.get("questions", []):
            formatted = f"{count}. {q['question']}\n"
            for i, option in enumerate(q['options']):
                formatted += f"{chr(65 + i)}. {option['text']}"
                if option.get("correct"):
                    formatted += " ✅"
                formatted += "\n"
            questions.append(formatted)
            count += 1

        # Save to a .txt file
        filename = "quiz_questions.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n\n".join(questions))

        return filename
    else:
        return None

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Koyeb"""
    return "OK", 200

@client.on(events.NewMessage(pattern=r'^/quiz\s+(https://t\.me/[\w/]+)$'))
async def quiz_handler(event):
    """Handles the /quiz command"""
    url = event.pattern_match.group(1)
    await event.reply("Fetching quiz data...")

    filename = await fetch_quiz_data(url)

    if filename:
        await client.send_file(event.chat_id, filename, caption="Here are the quiz questions.")
        os.remove(filename)
    else:
        await event.reply("Sorry, something went wrong while fetching the quiz.")

@app.before_first_request
def start_bot():
    """Start the Telethon bot when the Flask app is ready."""
    client.start()

if __name__ == "__main__":
    # Run the Flask app and make sure it's accessible on all interfaces (0.0.0.0)
    app.run(debug=True, host="0.0.0.0", port=5000)

    # This will run the Telethon client in the background after Flask starts
    client.run_until_disconnected()
    
