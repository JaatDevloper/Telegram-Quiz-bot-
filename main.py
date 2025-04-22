from flask import Flask
from telethon import TelegramClient, events
import os

# Flask app setup
app = Flask(__name__)

# Your bot's Telegram client setup
API_ID = 'your_api_id'  # Replace with your actual API ID
API_HASH = 'your_api_hash'  # Replace with your actual API HASH
SESSION = 'quiz_userbot_session'

# Initialize Telegram client
client = TelegramClient(SESSION, API_ID, API_HASH)

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Koyeb"""
    return "OK", 200

@client.on(events.NewMessage(pattern=r'^/quiz\s+(https://t\.me/[\w/]+)$'))
async def quiz_handler(event):
    """Handle /quiz command"""
    url = event.pattern_match.group(1)
    await event.reply("Fetching quiz data...")

    # This is where you would add your code to fetch and process the quiz
    # For now, it's a placeholder that just echoes the URL.
    await event.reply(f"Quiz URL received: {url}")

    # Example: save the quiz questions in a .txt file (you can extend this part)
    filename = "quiz_questions.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("Sample quiz questions\n")
    
    # Send the .txt file
    await client.send_file(event.chat_id, filename, caption="Here are the quiz questions.")
    os.remove(filename)

@app.before_first_request
def start_bot():
    """Start the Telethon bot when the Flask app is ready."""
    client.start()

if __name__ == "__main__":
    # Run the Flask app and make sure it's accessible on all interfaces (0.0.0.0)
    app.run(debug=True, host="0.0.0.0", port=5000)
