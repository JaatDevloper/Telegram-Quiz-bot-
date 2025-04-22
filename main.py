import base64
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
SESSION_STRING = os.getenv("SESSION_STRING", '1BVtsOKEBu0M0...')  # Shortened here

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

def decode_param(start_param):
    try:
        padding = '=' * (-len(start_param) % 4)
        start_param += padding
        decoded = base64.urlsafe_b64decode(start_param.encode()).decode('utf-8')
        return json.loads(decoded)
    except Exception as e:
        print(f"Error decoding param: {e}")
        return None

async def fetch_quiz_data(url):
    try:
        start_param = url.split("start=")[1]
    except IndexError:
        return None

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

        filename = "quiz_questions.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n\n".join(questions))

        return filename
    return None

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
      
