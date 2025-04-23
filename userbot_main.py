import os
import re
import asyncio
import logging
import nest_asyncio
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
import time
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Configuration from environment variables
try:
    API_ID = int(os.environ.get('TELEGRAM_API_ID', '0').strip().strip('"').strip("'"))
except ValueError:
    logger.error("Invalid TELEGRAM_API_ID - must be a number")
    API_ID = 0

API_HASH = os.environ.get('TELEGRAM_API_HASH', '')
PHONE = os.environ.get('TELEGRAM_PHONE', '')
SESSION_FILE = 'quiz_extractor_session'

# Initialize the client
client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

# Quiz extraction pattern
quiz_url_pattern = r'https?://t\.me/QuizBot\?start=([a-zA-Z0-9_-]+)'
direct_quiz_pattern = r'^/quiz\s+([a-zA-Z0-9_-]+)$'

async def extract_quiz_data(quiz_param):
    """Extract quiz data from QuizBot using the parameter."""
    try:
        logger.info(f"Extracting quiz data for parameter: {quiz_param}")
        
        async with client.conversation('@QuizBot') as conv:
            # Send the start command with the quiz parameter
            await conv.send_message(f"/start {quiz_param}")
            
            # Get the initial response
            response = await conv.get_response(timeout=30)
            
            if not response:
                return {"error": "No response from QuizBot"}
            
            quiz_data = {
                "title": "",
                "param": quiz_param,
                "questions": []
            }
            
            # Extract title from initial response
            text = response.text
            quiz_data["title"] = extract_title(text)
            
            # Start the quiz
            await conv.send_message("/play")
            
            # Process questions
            question_count = 0
            while True:
                try:
                    # Wait for question
                    question_msg = await conv.get_response(timeout=15)
                    
                    # Check if quiz ended
                    if "Quiz finished" in question_msg.text or "Your result" in question_msg.text:
                        break
                    
                    # Extract question data
                    question_text = question_msg.text
                    question_data = {"question": question_text, "options": [], "correct_option": None}
                    
                    # Get options (usually 4 buttons)
                    async for message in client.iter_messages('@QuizBot', limit=1):
                        if message.buttons:
                            for row in message.buttons:
                                for button in row:
                                    question_data["options"].append(button.text)
                    
                    # Click any option (first one) to move forward
                    await question_msg.click(0)
                    
                    # Get result (which shows correct answer)
                    result_msg = await conv.get_response(timeout=15)
                    
                    # Extract correct answer from result message
                    correct_option = extract_correct_option(result_msg.text, question_data["options"])
                    if correct_option:
                        question_data["correct_option"] = correct_option
                    
                    # Add question to our collection
                    quiz_data["questions"].append(question_data)
                    question_count += 1
                    
                    # Click "Next" to go to the next question
                    await result_msg.click(0)
                    
                except Exception as e:
                    logger.error(f"Error processing question: {e}")
                    break
            
            quiz_data["question_count"] = question_count
            return quiz_data
    
    except Exception as e:
        logger.exception(f"Error extracting quiz data: {e}")
        return {"error": f"Failed to extract quiz data: {str(e)}"}

def extract_title(text):
    """Extract the quiz title from the initial response."""
    if "Get ready for the quiz" in text:
        title_match = re.search(r'Get ready for the quiz [\'\"](.+?)[\'\"]', text)
        if title_match:
            return title_match.group(1)
    return "Untitled Quiz"

def extract_correct_option(result_text, options):
    """Extract the correct option from the result message."""
    # Look for indication of correct answer (typically an emoji like ✅)
    for i, option in enumerate(options):
        if f"{option} ✅" in result_text or f"✅ {option}" in result_text:
            return option
    return None

def format_quiz_to_text(quiz_data):
    """Format quiz data into a nice text file format."""
    if "error" in quiz_data:
        return f"Error: {quiz_data['error']}"
    
    text = []
    text.append(f"📝 QUIZ: {quiz_data['title']}")
    text.append(f"🔢 Total Questions: {quiz_data.get('question_count', len(quiz_data['questions']))}")
    text.append("=" * 50)
    text.append("")
    
    for i, question in enumerate(quiz_data['questions'], 1):
        # Add question
        text.append(f"Question {i}: {question['question']}")
        
        # Add options
        for j, option in enumerate(question['options'], 1):
            if option == question['correct_option']:
                text.append(f"  {j}. {option} ✅")
            else:
                text.append(f"  {j}. {option}")
        
        text.append("")
    
    text.append("=" * 50)
    text.append("Generated by Telegram Quiz Extractor Bot")
    
    return "\n".join(text)

@client.on(events.NewMessage(pattern=quiz_url_pattern))
async def handle_quiz_url(event):
    """Handle messages containing quiz URLs."""
    match = re.search(quiz_url_pattern, event.text)
    if match:
        quiz_param = match.group(1)
        await event.respond(f"📝 Processing quiz with ID: {quiz_param}...")
        
        # Extract the quiz data
        quiz_data = await extract_quiz_data(quiz_param)
        
        if "error" in quiz_data:
            await event.respond(f"❌ Error: {quiz_data['error']}")
            return
        
        # Format the quiz data to text
        formatted_text = format_quiz_to_text(quiz_data)
        
        # Generate a file name
        file_name = f"quiz_{int(time.time())}_{quiz_param}.txt"
        
        # Save to file
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(formatted_text)
        
        # Send the file
        await event.respond(f"📋 Here's your extracted quiz:", file=file_name)
        
        # Clean up
        os.remove(file_name)

@client.on(events.NewMessage(pattern=direct_quiz_pattern))
async def handle_direct_quiz(event):
    """Handle direct /quiz commands."""
    match = re.search(direct_quiz_pattern, event.text)
    if match:
        quiz_param = match.group(1)
        await event.respond(f"📝 Processing quiz with ID: {quiz_param}...")
        
        # Extract the quiz data
        quiz_data = await extract_quiz_data(quiz_param)
        
        if "error" in quiz_data:
            await event.respond(f"❌ Error: {quiz_data['error']}")
            return
        
        # Format the quiz data to text
        formatted_text = format_quiz_to_text(quiz_data)
        
        # Generate a file name
        file_name = f"quiz_{int(time.time())}_{quiz_param}.txt"
        
        # Save to file
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(formatted_text)
        
        # Send the file
        await event.respond(f"📋 Here's your extracted quiz:", file=file_name)
        
        # Clean up
        os.remove(file_name)

@client.on(events.NewMessage(pattern=r'^/start$'))
async def handle_start_command(event):
    """Handle /start command."""
    await event.respond(
        "👋 Welcome to Quiz Extractor Bot!\n\n"
        "I can extract questions and answers from Telegram QuizBot quizzes.\n\n"
        "To use me, send:\n"
        "- A QuizBot URL like: https://t.me/QuizBot?start=abcDEF123\n"
        "- Or use the command: /quiz abcDEF123\n\n"
        "I'll extract all questions and answers and send you a formatted text file."
    )

@client.on(events.NewMessage(pattern=r'^/help$'))
async def handle_help_command(event):
    """Handle /help command."""
    await event.respond(
        "📚 Quiz Extractor Bot Help\n\n"
        "I can extract questions and answers from Telegram QuizBot quizzes.\n\n"
        "Commands:\n"
        "- /start: Show welcome message\n"
        "- /help: Show this help message\n"
        "- /quiz [ID]: Extract quiz with given ID\n\n"
        "Or simply send a QuizBot URL like:\n"
        "https://t.me/QuizBot?start=abcDEF123"
    )

async def main():
    """Start the client and run until disconnected."""
    if API_ID == 0 or not API_HASH:
        logger.error("API credentials not provided. Please set TELEGRAM_API_ID and TELEGRAM_API_HASH.")
        return
    
    logger.info("Starting Telegram client...")
    
    try:
        await client.start(phone=PHONE)
        logger.info("Client started successfully!")
        
        # Run the client until disconnected
        await client.run_until_disconnected()
    except SessionPasswordNeededError:
        logger.error("Two-factor authentication required but not supported")
    except Exception as e:
        logger.exception(f"Error starting client: {e}")
    finally:
        await client.disconnect()
        logger.info("Client disconnected.")

if __name__ == "__main__":
    asyncio.run(main())