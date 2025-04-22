import os
import logging
import asyncio
from telethon import TelegramClient, events
from telethon.tl.functions.messages import StartBotRequest
from telethon.tl.functions.channels import JoinChannelRequest

logger = logging.getLogger(__name__)

# Telegram API credentials
API_ID = os.environ.get('TELEGRAM_API_ID')
API_HASH = os.environ.get('TELEGRAM_API_HASH')
PHONE_NUMBER = os.environ.get('TELEGRAM_PHONE')
SESSION_FILE = 'quiz_extractor'

def setup_telegram_client():
    """
    Set up and connect to Telegram client.
    
    Returns:
        TelegramClient: Connected Telegram client or None if connection fails
    """
    if not all([API_ID, API_HASH, PHONE_NUMBER]):
        logger.warning("Telegram credentials not found in environment variables")
        return None
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        client = TelegramClient(SESSION_FILE, API_ID, API_HASH, loop=loop)
        
        # Start the client
        loop.run_until_complete(client.connect())
        
        # Ensure we're authorized
        if not loop.run_until_complete(client.is_user_authorized()):
            logger.info("Not authorized, sending code request...")
            loop.run_until_complete(client.send_code_request(PHONE_NUMBER))
            logger.info("Authorize in the Telegram app and restart this application")
            return None
        
        logger.info("Successfully connected to Telegram")
        return client
    except Exception as e:
        logger.error(f"Error setting up Telegram client: {str(e)}")
        return None

async def _get_quiz_data_async(client, start_param):
    """
    Asynchronous function to get quiz data from Telegram.
    
    Args:
        client (TelegramClient): Connected Telegram client
        start_param (str): Start parameter from QuizBot URL
    
    Returns:
        dict: Quiz data or None if retrieval fails
    """
    try:
        # Start conversation with QuizBot
        logger.debug(f"Starting conversation with QuizBot using parameter: {start_param}")
        
        # Get the QuizBot entity
        quiz_bot = await client.get_entity("QuizBot")
        
        # Start the bot with the parameter
        await client(StartBotRequest(
            bot=quiz_bot,
            peer=quiz_bot,
            start_param=start_param
        ))
        
        # Wait for the bot's response (this is a simplified approach)
        # In a real implementation, you'd want to use more sophisticated message handling
        await asyncio.sleep(2)
        
        # Get messages from the bot
        messages = await client.get_messages(quiz_bot, limit=5)
        
        # Process the messages to extract quiz data
        quiz_data = {
            'title': 'Quiz from Telegram',
            'questions': []
        }
        
        for msg in messages:
            if msg.message and 'question' in msg.message.lower():
                # Extract question text
                question_text = msg.message.split('\n')[0]
                
                # Extract options
                options = []
                for line in msg.message.split('\n')[1:]:
                    if line.strip().startswith(('A.', 'B.', 'C.', 'D.')):
                        options.append(line.strip()[2:].strip())
                
                quiz_data['questions'].append({
                    'text': question_text,
                    'options': options,
                    'correct_option': 0  # Default to first option as we can't determine the correct one
                })
        
        if quiz_data['questions']:
            return quiz_data
        else:
            logger.warning("No quiz questions found in bot response")
            return None
    
    except Exception as e:
        logger.error(f"Error getting quiz data from Telegram: {str(e)}")
        return None

def get_quiz_data(client, start_param):
    """
    Get quiz data from Telegram.
    
    Args:
        client (TelegramClient): Connected Telegram client
        start_param (str): Start parameter from QuizBot URL
    
    Returns:
        dict: Quiz data or None if retrieval fails
    """
    if not client:
        logger.warning("Telegram client not available")
        return None
    
    try:
        # Create a new event loop for this request
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the async function to get quiz data
        quiz_data = loop.run_until_complete(_get_quiz_data_async(client, start_param))
        
        # Close the loop
        loop.close()
        
        return quiz_data
    except Exception as e:
        logger.error(f"Error in get_quiz_data: {str(e)}")
        return None
