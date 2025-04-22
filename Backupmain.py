import base64
import json
import os
from telethon import TelegramClient, events

API_ID = 'your_api_id'  # Add your API ID
API_HASH = 'your_api_hash'  # Add your API HASH
SESSION = 'quiz_userbot_session'

client = TelegramClient(SESSION, API_ID, API_HASH)

def decode_param(start_param):
    """Decodes the start param base64url to get the quiz data"""
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
    """Fetches and decodes quiz data from the URL"""
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

@client.on(events.NewMessage(pattern=r'^/quiz\s+(https://t\.me/[\w/]+)$'))
async def quiz_handler(event):
    url = event.pattern_match.group(1)
    await event.reply("Fetching quiz data...")

    filename = await fetch_quiz_data(url)

    if filename:
        await client.send_file(event.chat_id, filename, caption="Here are the quiz questions.")
        os.remove(filename)
    else:
        await event.reply("Sorry, something went wrong while fetching the quiz.")

client.start()
print("Userbot is running...")
client.run_until_disconnected()
